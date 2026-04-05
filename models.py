import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    username TEXT UNIQUE NOT NULL,
    name TEXT,
    password TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL DEFAULT 'operator',
    parent_user_id INTEGER,
    is_admin INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (parent_user_id) REFERENCES users(id)
);
"""


TENANT_SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cnpj TEXT,
    address TEXT,
    street TEXT,
    number TEXT,
    complement TEXT,
    neighborhood TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    postal_code TEXT,
    category TEXT,
    category_id INTEGER,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cpf TEXT,
    address TEXT,
    street TEXT,
    number TEXT,
    complement TEXT,
    neighborhood TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    postal_code TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER,
    unit_id INTEGER,
    supplier_id INTEGER,
    cost REAL DEFAULT 0,
    price REAL DEFAULT 0,
    stock INTEGER DEFAULT 0,
    stock_min INTEGER DEFAULT 0,
    expiration_date TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (unit_id) REFERENCES units(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    client_id INTEGER,
    payment_method TEXT,
    discount REAL DEFAULT 0,
    surcharge REAL DEFAULT 0,
    total REAL NOT NULL,
    profit REAL DEFAULT 0,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER,
    product_id INTEGER,
    quantity REAL,
    unit_price REAL,
    total_price REAL,
    FOREIGN KEY (sale_id) REFERENCES sales(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    amount REAL,
    type TEXT,
    date TEXT
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    quantity REAL,
    movement_type TEXT,
    date TEXT,
    notes TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""


ADMIN_USER = ("admin", "admin123", "admin@kdcsystems.local", 1)


def slugify(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed or "conta"


def get_data_root() -> Path:
    configured_path = os.environ.get("DATA_DIR") or os.environ.get("RENDER_DISK_PATH")
    data_root = Path(configured_path) if configured_path else Path(__file__).resolve().parent / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "tenants").mkdir(parents=True, exist_ok=True)
    return data_root


def get_auth_db_path() -> Path:
    return get_data_root() / "auth.db"


def get_tenant_db_path(account_id: int) -> Path:
    return get_data_root() / "tenants" / f"tenant_{account_id}.db"


def get_db_connection(db_path: str | Path):
    try:
        connection = sqlite3.connect(str(db_path), timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection
    except sqlite3.DatabaseError as error:
        logger.error(f"Erro ao conectar ao banco de dados: {error}")
        raise


def backup_database(db_path: str | Path):
    try:
        db_path = Path(db_path)
        if not db_path.exists():
            return

        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{db_path.stem}_backup_{timestamp}.db"
        shutil.copy2(db_path, backup_file)

        backups = sorted(backup_dir.glob(f"{db_path.stem}_backup_*.db"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink(missing_ok=True)
    except Exception as error:
        logger.warning(f"Erro ao criar backup: {error}")


def check_database_integrity(db_path: str | Path) -> bool:
    try:
        connection = sqlite3.connect(str(db_path))
        cursor = connection.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        connection.close()
        return bool(result and result[0] == "ok")
    except Exception as error:
        logger.error(f"Erro ao verificar integridade: {error}")
        return False


def recover_database(db_path: str | Path) -> bool:
    try:
        db_path = Path(db_path)
        backup_dir = db_path.parent / "backups"
        if backup_dir.exists():
            backups = sorted(backup_dir.glob(f"{db_path.stem}_backup_*.db"), reverse=True)
            if backups:
                shutil.copy2(backups[0], db_path)
                return True

        if db_path.exists():
            corrupted_name = f"{db_path.stem}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            db_path.rename(db_path.parent / corrupted_name)
        return False
    except Exception as error:
        logger.error(f"Erro ao recuperar banco: {error}")
        return False


def init_db(db_path: str | Path, schema: str = TENANT_SCHEMA):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if db_path.exists() and not check_database_integrity(db_path):
            recover_database(db_path)
        elif db_path.exists():
            backup_database(db_path)

        connection = get_db_connection(db_path)
        connection.executescript(schema)
        connection.commit()
        connection.close()

        if schema == AUTH_SCHEMA:
            migrate_auth_database(db_path)
        else:
            migrate_tenant_database(db_path)
    except sqlite3.DatabaseError as error:
        logger.error(f"Erro ao inicializar banco de dados: {error}")
        recover_database(db_path)
        connection = get_db_connection(db_path)
        connection.executescript(schema)
        connection.commit()
        connection.close()
        if schema == AUTH_SCHEMA:
            migrate_auth_database(db_path)
        else:
            migrate_tenant_database(db_path)


def init_auth_db(db_path: str | Path | None = None):
    init_db(db_path or get_auth_db_path(), AUTH_SCHEMA)


def init_tenant_db(db_path: str | Path):
    init_db(db_path, TENANT_SCHEMA)


def migrate_auth_database(db_path: str | Path):
    connection = get_db_connection(db_path)
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = {column[1] for column in cursor.fetchall()}
    migrations = {
        "account_id": "ALTER TABLE users ADD COLUMN account_id INTEGER DEFAULT 1",
        "role": "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'operator'",
        "parent_user_id": "ALTER TABLE users ADD COLUMN parent_user_id INTEGER",
        "is_active": "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1",
        "created_at": "ALTER TABLE users ADD COLUMN created_at TEXT",
    }
    for column_name, sql in migrations.items():
        if column_name not in columns:
            connection.execute(sql)
            connection.commit()

    connection.execute(
        "UPDATE users SET role = CASE WHEN is_admin = 1 THEN 'owner' ELSE 'operator' END WHERE role IS NULL OR role = ''"
    )
    connection.execute(
        "UPDATE users SET created_at = ? WHERE created_at IS NULL OR created_at = ''",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
    )
    connection.commit()
    connection.close()


def migrate_tenant_database(db_path: str | Path):
    connection = get_db_connection(db_path)
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(suppliers)")
    supplier_columns = {column[1] for column in cursor.fetchall()}
    supplier_migrations = {
        "street": "ALTER TABLE suppliers ADD COLUMN street TEXT",
        "number": "ALTER TABLE suppliers ADD COLUMN number TEXT",
        "complement": "ALTER TABLE suppliers ADD COLUMN complement TEXT",
        "neighborhood": "ALTER TABLE suppliers ADD COLUMN neighborhood TEXT",
        "city": "ALTER TABLE suppliers ADD COLUMN city TEXT",
        "state": "ALTER TABLE suppliers ADD COLUMN state TEXT",
        "country": "ALTER TABLE suppliers ADD COLUMN country TEXT",
        "postal_code": "ALTER TABLE suppliers ADD COLUMN postal_code TEXT",
        "category_id": "ALTER TABLE suppliers ADD COLUMN category_id INTEGER",
    }
    for column_name, sql in supplier_migrations.items():
        if column_name not in supplier_columns:
            connection.execute(sql)
            connection.commit()

    cursor.execute("PRAGMA table_info(clients)")
    client_columns = {column[1] for column in cursor.fetchall()}
    client_migrations = {
        "street": "ALTER TABLE clients ADD COLUMN street TEXT",
        "number": "ALTER TABLE clients ADD COLUMN number TEXT",
        "complement": "ALTER TABLE clients ADD COLUMN complement TEXT",
        "neighborhood": "ALTER TABLE clients ADD COLUMN neighborhood TEXT",
        "city": "ALTER TABLE clients ADD COLUMN city TEXT",
        "state": "ALTER TABLE clients ADD COLUMN state TEXT",
        "country": "ALTER TABLE clients ADD COLUMN country TEXT",
        "postal_code": "ALTER TABLE clients ADD COLUMN postal_code TEXT",
    }
    for column_name, sql in client_migrations.items():
        if column_name not in client_columns:
            connection.execute(sql)
            connection.commit()

    cursor.execute("PRAGMA table_info(products)")
    product_columns = {column[1] for column in cursor.fetchall()}
    if "supplier_id" not in product_columns:
        connection.execute("ALTER TABLE products ADD COLUMN supplier_id INTEGER")
        connection.commit()

    connection.close()


def ensure_unique_slug(connection, base_slug: str) -> str:
    slug = base_slug
    counter = 1
    while connection.execute("SELECT 1 FROM accounts WHERE slug = ?", (slug,)).fetchone():
        counter += 1
        slug = f"{base_slug}-{counter}"
    return slug


def create_account_with_owner(account_name: str, owner_name: str, username: str, password: str, email: str | None = None):
    auth_db_path = get_auth_db_path()
    init_auth_db(auth_db_path)
    connection = get_db_connection(auth_db_path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slug = ensure_unique_slug(connection, slugify(account_name))

    connection.execute(
        "INSERT INTO accounts (name, slug, created_at) VALUES (?, ?, ?)",
        (account_name.strip(), slug, timestamp),
    )
    account_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    connection.execute(
        "INSERT INTO users (account_id, username, name, password, email, role, is_admin, created_at) VALUES (?, ?, ?, ?, ?, 'owner', 1, ?)",
        (account_id, username.strip(), owner_name.strip(), password, email, timestamp),
    )
    connection.commit()
    connection.close()

    init_tenant_db(get_tenant_db_path(account_id))
    return account_id


def seed_admin(db_path: str | Path | None = None):
    auth_db_path = Path(db_path) if db_path else get_auth_db_path()
    init_auth_db(auth_db_path)
    connection = get_db_connection(auth_db_path)
    existing_owner = connection.execute("SELECT id FROM users WHERE role = 'owner' LIMIT 1").fetchone()
    connection.close()
    if existing_owner:
        return
    create_account_with_owner(
        account_name="Conta Principal",
        owner_name="Administrador",
        username=ADMIN_USER[0],
        password=ADMIN_USER[1],
        email=ADMIN_USER[2],
    )


def authenticate_user(username: str, password: str):
    connection = get_db_connection(get_auth_db_path())
    user = connection.execute(
        "SELECT u.*, a.name AS account_name, a.slug AS account_slug "
        "FROM users u JOIN accounts a ON a.id = u.account_id "
        "WHERE u.username = ? AND u.password = ? AND u.is_active = 1",
        (username, password),
    ).fetchone()
    connection.close()
    return user


def migrate_legacy_database(legacy_db_path: str | Path | None):
    if not legacy_db_path:
        return

    legacy_db_path = Path(legacy_db_path)
    auth_db_path = get_auth_db_path()
    if not legacy_db_path.exists() or legacy_db_path.resolve() == auth_db_path.resolve():
        return

    init_auth_db(auth_db_path)
    connection = get_db_connection(auth_db_path)
    has_accounts = connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] > 0
    connection.close()
    if has_accounts:
        return

    legacy_connection = get_db_connection(legacy_db_path)
    legacy_users = legacy_connection.execute(
        "SELECT id, username, name, password, email, is_admin FROM users ORDER BY is_admin DESC, id ASC"
    ).fetchall()
    legacy_connection.close()

    default_account_id = create_account_with_owner(
        account_name="Conta Migrada",
        owner_name=(legacy_users[0]["name"] if legacy_users else "Administrador"),
        username=(legacy_users[0]["username"] if legacy_users else ADMIN_USER[0]),
        password=(legacy_users[0]["password"] if legacy_users else ADMIN_USER[1]),
        email=(legacy_users[0]["email"] if legacy_users else ADMIN_USER[2]),
    )

    auth_connection = get_db_connection(auth_db_path)
    owner_row = auth_connection.execute(
        "SELECT id FROM users WHERE account_id = ? AND role = 'owner' LIMIT 1",
        (default_account_id,),
    ).fetchone()
    owner_id = owner_row[0]
    for legacy_user in legacy_users[1:]:
        auth_connection.execute(
            "INSERT OR IGNORE INTO users (account_id, username, name, password, email, role, parent_user_id, is_admin, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'operator', ?, 0, ?)",
            (
                default_account_id,
                legacy_user["username"],
                legacy_user["name"],
                legacy_user["password"],
                legacy_user["email"],
                owner_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
    auth_connection.commit()
    auth_connection.close()

    tenant_db_path = get_tenant_db_path(default_account_id)
    if not tenant_db_path.exists():
        shutil.copy2(legacy_db_path, tenant_db_path)
    init_tenant_db(tenant_db_path)
