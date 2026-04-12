import logging
import os

import psycopg
from datetime import datetime
from pathlib import Path


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Estado da conexão
_DB_INITIALIZED = False
_DB_ERROR = None


# ---------------------------------------------------------------------------
# Schemas (PostgreSQL)
# ---------------------------------------------------------------------------

_AUTH_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        username TEXT UNIQUE NOT NULL,
        name TEXT,
        password TEXT NOT NULL,
        email TEXT,
        role TEXT NOT NULL DEFAULT 'operator',
        parent_user_id INTEGER REFERENCES users(id),
        is_admin INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """,
]

_TENANT_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        UNIQUE (account_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS units (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        UNIQUE (account_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS suppliers (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        cnpj TEXT,
        email TEXT,
        phone TEXT,
        whatsapp TEXT,
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
        category_id INTEGER REFERENCES categories(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS clients (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        cpf TEXT,
        email TEXT,
        phone TEXT,
        whatsapp TEXT,
        birth_date TEXT,
        address TEXT,
        street TEXT,
        number TEXT,
        complement TEXT,
        neighborhood TEXT,
        city TEXT,
        state TEXT,
        country TEXT,
        postal_code TEXT,
        gender TEXT DEFAULT 'nao_informar'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        category_id INTEGER REFERENCES categories(id),
        unit_id INTEGER REFERENCES units(id),
        supplier_id INTEGER REFERENCES suppliers(id),
        cost DOUBLE PRECISION DEFAULT 0,
        price DOUBLE PRECISION DEFAULT 0,
        stock INTEGER DEFAULT 0,
        stock_min INTEGER DEFAULT 0,
        expiration_date TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        date TEXT NOT NULL,
        client_id INTEGER REFERENCES clients(id),
        payment_method TEXT,
        discount DOUBLE PRECISION DEFAULT 0,
        surcharge DOUBLE PRECISION DEFAULT 0,
        total DOUBLE PRECISION NOT NULL,
        profit DOUBLE PRECISION DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sale_items (
        id SERIAL PRIMARY KEY,
        sale_id INTEGER REFERENCES sales(id),
        product_id INTEGER REFERENCES products(id),
        quantity DOUBLE PRECISION,
        unit_price DOUBLE PRECISION,
        total_price DOUBLE PRECISION
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS expenses (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        description TEXT,
        amount DOUBLE PRECISION,
        type TEXT,
        date TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_movements (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        product_id INTEGER REFERENCES products(id),
        quantity DOUBLE PRECISION,
        movement_type TEXT,
        date TEXT,
        notes TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS account_settings (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        setting_key TEXT NOT NULL,
        setting_value TEXT,
        updated_at TEXT NOT NULL,
        UNIQUE (account_id, setting_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS financial_categories (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        kind TEXT NOT NULL DEFAULT 'both',
        UNIQUE (account_id, name, kind)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS financial_entries (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        entry_type TEXT NOT NULL,
        description TEXT NOT NULL,
        category_id INTEGER REFERENCES financial_categories(id),
        supplier_id INTEGER REFERENCES suppliers(id),
        client_id INTEGER REFERENCES clients(id),
        amount DOUBLE PRECISION NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pendente',
        is_recurring INTEGER DEFAULT 0,
        recurrence_days INTEGER DEFAULT 30,
        source TEXT DEFAULT 'manual',
        source_ref TEXT,
        created_at TEXT NOT NULL,
        paid_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS nfe_imports (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        invoice_key TEXT,
        invoice_number TEXT,
        issue_date TEXT,
        supplier_cnpj TEXT,
        supplier_name TEXT,
        total_amount DOUBLE PRECISION DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS purchase_orders (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        supplier_id INTEGER REFERENCES suppliers(id),
        product_id INTEGER REFERENCES products(id),
        quantity DOUBLE PRECISION NOT NULL,
        unit_cost DOUBLE PRECISION DEFAULT 0,
        installments INTEGER DEFAULT 1,
        first_due_date TEXT,
        expected_date TEXT,
        status TEXT NOT NULL DEFAULT 'aberto',
        notes TEXT,
        created_at TEXT NOT NULL,
        received_at TEXT
    )
    """,
]

_TENANT_MIGRATIONS = [
    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS gender TEXT DEFAULT 'nao_informar'",
    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS email TEXT",
    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS birth_date TEXT",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS email TEXT",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS phone TEXT",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS whatsapp TEXT",
    "ALTER TABLE financial_entries ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual'",
    "ALTER TABLE financial_entries ADD COLUMN IF NOT EXISTS source_ref TEXT",
    "ALTER TABLE financial_entries ADD COLUMN IF NOT EXISTS is_recurring INTEGER DEFAULT 0",
    "ALTER TABLE financial_entries ADD COLUMN IF NOT EXISTS recurrence_days INTEGER DEFAULT 30",
    "ALTER TABLE nfe_imports ADD COLUMN IF NOT EXISTS invoice_key TEXT",
    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS phone TEXT",
    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS whatsapp TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS margin_percent DOUBLE PRECISION DEFAULT 100",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS unit_buy TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS unit_sell TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS conversion_factor DOUBLE PRECISION DEFAULT 1",
]

ADMIN_USER = ("admin", "admin123", "admin@kdcsystems.local", 1)

DEFAULT_CATEGORIES = [
    "Alimentos e Bebidas",
    "Automotivo",
    "Brinquedos e Jogos",
    "Casa e Decoração",
    "Eletrônicos",
    "Esportes e Lazer",
    "Farmácia",
    "Ferramentas e Construção",
    "Higiene e Beleza",
    "Informática",
    "Limpeza",
    "Papelaria e Escritório",
    "Pet Shop",
    "Serviços",
    "Vestuário e Acessórios",
]

DEFAULT_UNITS = ["CX", "KG", "PC", "PT", "UN"]


def seed_default_data(account_id: int, conn) -> None:
    for cat in DEFAULT_CATEGORIES:
        conn.execute(
            "INSERT INTO categories (account_id, name) VALUES (%s, %s) ON CONFLICT (account_id, name) DO NOTHING",
            (account_id, cat),
        )
    for unit in DEFAULT_UNITS:
        conn.execute(
            "INSERT INTO units (account_id, name) VALUES (%s, %s) ON CONFLICT (account_id, name) DO NOTHING",
            (account_id, unit),
        )


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    # Render provides postgres:// but the driver expects postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _log_db_info():
    """Log informações sobre a configuração do banco de dados."""
    global _DB_INITIALIZED, _DB_ERROR
    
    db_url = _get_db_url()
    
    if db_url:
        logger.info("📦 Usando PostgreSQL (Render/Produção ou Local)")
        logger.info(f"   URL: {db_url[:50]}...")
    else:
        logger.info("📦 DATABASE_URL não configurado")
        logger.info("   Configure no arquivo .env para ativar PostgreSQL")
    
    _DB_INITIALIZED = True


class _Conn:
    """Thin wrapper around psycopg connection that mimics sqlite3's conn.execute() API."""

    def __init__(self, pg_conn):
        self._c = pg_conn

    def execute(self, sql, params=()):
        cur = self._c.cursor()
        cur.execute(sql, params)
        return _Cursor(cur)

    def commit(self):
        self._c.commit()

    def rollback(self):
        self._c.rollback()

    def close(self):
        self._c.close()


class _Row:
    def __init__(self, columns, values):
        self._columns = list(columns)
        self._values = tuple(values)
        self._mapping = dict(zip(self._columns, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._mapping[key]

    def __iter__(self):
        return iter(self._mapping.items())

    def get(self, key, default=None):
        return self._mapping.get(key, default)

    def items(self):
        return self._mapping.items()

    def keys(self):
        return self._mapping.keys()

    def values(self):
        return self._mapping.values()


class _Cursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def _columns(self):
        if not self._cursor.description:
            return []
        return [column.name for column in self._cursor.description]

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return _Row(self._columns(), row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        columns = self._columns()
        return [_Row(columns, row) for row in rows]

    def close(self):
        self._cursor.close()


def get_db_connection() -> _Conn:
    """
    Obtém conexão com o banco de dados.
    
    - Tenta usar DATABASE_URL (Render/PostgreSQL local)
    - Se falhar, registra erro e levanta exceção
    - O app.py trata a exceção graciosamente
    """
    global _DB_INITIALIZED
    
    if not _DB_INITIALIZED:
        _log_db_info()
    
    db_url = _get_db_url()
    
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL não configurado. "
            "Configure a variável de ambiente DATABASE_URL ou adicione ao arquivo .env"
        )
    
    try:
        pg_conn = psycopg.connect(db_url)
        return _Conn(pg_conn)
    except (psycopg.OperationalError, psycopg.DatabaseError) as exc:
        logger.error(f"❌ Erro ao conectar ao banco de dados: {exc}")
        raise


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def _run_statements(statements):
    conn = get_db_connection()
    for stmt in statements:
        conn.execute(stmt)
    conn.commit()
    conn.close()


def init_auth_db(db_path=None):
    """Creates auth tables in PostgreSQL. db_path ignored (kept for API compat)."""
    _run_statements(_AUTH_STATEMENTS)


def init_tenant_db(db_path=None):
    """Creates tenant tables in PostgreSQL. db_path ignored (kept for API compat)."""
    _run_statements(_TENANT_STATEMENTS)
    _run_statements(_TENANT_MIGRATIONS)


# ---------------------------------------------------------------------------
# Slug utility
# ---------------------------------------------------------------------------

def slugify(value: str) -> str:
    normalized = "".join(c.lower() if c.isalnum() else "-" for c in value.strip())
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed or "conta"


def _ensure_unique_slug(conn, base_slug: str) -> str:
    slug = base_slug
    counter = 1
    while conn.execute("SELECT 1 FROM accounts WHERE slug = %s", (slug,)).fetchone():
        counter += 1
        slug = f"{base_slug}-{counter}"
    return slug


# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------

def create_account_with_owner(
    account_name: str,
    owner_name: str,
    username: str,
    password: str,
    email=None,
):
    init_auth_db()
    init_tenant_db()
    conn = get_db_connection()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    slug = _ensure_unique_slug(conn, slugify(account_name))

    account_id = conn.execute(
        "INSERT INTO accounts (name, slug, created_at) VALUES (%s, %s, %s) RETURNING id",
        (account_name.strip(), slug, timestamp),
    ).fetchone()[0]

    conn.execute(
        "INSERT INTO users (account_id, username, name, password, email, role, is_admin, created_at) "
        "VALUES (%s, %s, %s, %s, %s, 'owner', 1, %s)",
        (account_id, username.strip(), owner_name.strip(), password, email, timestamp),
    )
    seed_default_data(account_id, conn)
    conn.commit()
    conn.close()
    return account_id


def seed_all_accounts_default_data() -> None:
    """Ensures all existing accounts have the default categories and units seeded."""
    conn = get_db_connection()
    accounts = conn.execute("SELECT id FROM accounts").fetchall()
    for row in accounts:
        seed_default_data(row[0], conn)
    conn.commit()
    conn.close()


def seed_admin(db_path=None):
    """Creates default account if no owners exist. db_path ignored (kept for API compat)."""
    init_auth_db()
    init_tenant_db()
    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM users WHERE role = 'owner' LIMIT 1").fetchone()
    conn.close()
    if existing:
        return
    create_account_with_owner(
        account_name="Conta Principal",
        owner_name="Administrador",
        username=ADMIN_USER[0],
        password=ADMIN_USER[1],
        email=ADMIN_USER[2],
    )


def authenticate_user(username: str, password: str):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT u.*, a.name AS account_name, a.slug AS account_slug "
        "FROM users u JOIN accounts a ON a.id = u.account_id "
        "WHERE u.username = %s AND u.password = %s AND u.is_active = 1",
        (username, password),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def migrate_legacy_database(legacy_db_path=None):
    """No-op in PostgreSQL mode. Kept for API compatibility."""
    pass


# ---------------------------------------------------------------------------
# Stubs kept for backup_scheduler.py compatibility
# ---------------------------------------------------------------------------

def backup_database(db_path=None):
    """No-op stub — PostgreSQL manages its own backups."""
    logger.info("backup_database: no-op in PostgreSQL mode")


def check_database_integrity(db_path=None) -> bool:
    """No-op stub — always returns True in PostgreSQL mode."""
    return True