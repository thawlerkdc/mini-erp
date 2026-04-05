import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    name TEXT,
    password TEXT NOT NULL,
    email TEXT,
    is_admin INTEGER DEFAULT 0
);

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

def get_db_connection(db_path: str):
    """Estabelece conexão com o banco de dados com tratamento de erro."""
    try:
        connection = sqlite3.connect(db_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        # Habilitar verificação de integridade
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection
    except sqlite3.DatabaseError as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        raise

def backup_database(db_path: str):
    """Cria backup do banco de dados."""
    try:
        db_path = Path(db_path)
        if not db_path.exists():
            return
        
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"kdc_systems_backup_{timestamp}.db"
        
        shutil.copy2(db_path, backup_file)
        logger.info(f"Backup criado: {backup_file}")
        
        # Manter apenas os últimos 10 backups
        backups = sorted(backup_dir.glob("kdc_systems_backup_*.db"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
                logger.info(f"Backup antigo removido: {old_backup}")
    except Exception as e:
        logger.warning(f"Erro ao criar backup: {e}")

def check_database_integrity(db_path: str) -> bool:
    """Verifica a integridade do banco de dados."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()
        
        if result[0] == "ok":
            logger.info("Integridade do banco de dados verificada: OK")
            return True
        else:
            logger.error(f"Problema detectado na integridade: {result[0]}")
            return False
    except Exception as e:
        logger.error(f"Erro ao verificar integridade: {e}")
        return False

def recover_database(db_path: str) -> bool:
    """Tenta recuperar um banco de dados corrompido."""
    try:
        db_path = Path(db_path)
        logger.info("Tentando recuperar banco de dados...")
        
        # Verificar se existe backup
        backup_dir = db_path.parent / "backups"
        if backup_dir.exists():
            backups = sorted(backup_dir.glob("kdc_systems_backup_*.db"), reverse=True)
            if backups:
                logger.info(f"Restaurando do backup: {backups[0]}")
                shutil.copy2(backups[0], db_path)
                return True
        
        # Se não houver backup, remover arquivo corrompido
        if db_path.exists():
            corrupted_file = db_path.parent / f"{db_path.stem}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            db_path.rename(corrupted_file)
            logger.info(f"Arquivo corrompido movido para: {corrupted_file}")
        
        return False
    except Exception as e:
        logger.error(f"Erro ao recuperar banco de dados: {e}")
        return False

def init_db(db_path: str):
    """Inicializa o banco de dados com tratamento de erro e recuperação."""
    try:
        db_path = Path(db_path)
        
        # Se o banco existe, fazer backup antes de inicializar
        if db_path.exists():
            # Verificar integridade
            if not check_database_integrity(str(db_path)):
                logger.warning("Banco de dados corrompido detectado!")
                if not recover_database(str(db_path)):
                    # Se não conseguir recuperar, continuar criando um novo
                    logger.info("Criando novo banco de dados...")
            else:
                # Fazer backup periódico
                backup_database(str(db_path))
        
        # Conectar e criar tabelas se não existirem
        conn = get_db_connection(str(db_path))
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
        
        # Aplicar migrações
        migrate_database(str(db_path))
        
        logger.info("Banco de dados inicializado com sucesso")
    except sqlite3.DatabaseError as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        # Tentar recuperar
        recover_database(str(db_path))
        # Tentar inicializar novamente
        conn = get_db_connection(str(db_path))
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
        migrate_database(str(db_path))
    except Exception as e:
        logger.error(f"Erro inesperado ao inicializar banco de dados: {e}")
        raise

def seed_admin(db_path: str):
    """Adiciona usuário admin padrão se não existir."""
    try:
        conn = get_db_connection(db_path)
        user = conn.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USER[0],)).fetchone()
        if not user:
            conn.execute("INSERT INTO users (username, name, password, email, is_admin) VALUES (?, ?, ?, ?, ?)", 
                        (ADMIN_USER[0], "Administrador", ADMIN_USER[1], ADMIN_USER[2], ADMIN_USER[3]))
            conn.commit()
            logger.info("Usuário admin criado com sucesso")
        conn.close()
    except sqlite3.IntegrityError:
        logger.warning("Usuário admin já existe")
    except Exception as e:
        logger.error(f"Erro ao criar usuário admin: {e}")
        raise

def migrate_database(db_path: str):
    """Aplica migrações do banco de dados (adiciona novos campos se necessário)."""
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Verificar se a coluna 'name' existe na tabela 'users'
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'name' not in columns:
            logger.info("Adicionando coluna 'name' à tabela 'users'...")
            try:
                conn.execute("ALTER TABLE users ADD COLUMN name TEXT")
                conn.commit()
                logger.info("Coluna 'name' adicionada com sucesso")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise

        # Adicionar colunas de endereço e categoria para fornecedores
        cursor.execute("PRAGMA table_info(suppliers)")
        supplier_columns = [column[1] for column in cursor.fetchall()]
        supplier_migrations = {
            'street': "ALTER TABLE suppliers ADD COLUMN street TEXT",
            'number': "ALTER TABLE suppliers ADD COLUMN number TEXT",
            'complement': "ALTER TABLE suppliers ADD COLUMN complement TEXT",
            'neighborhood': "ALTER TABLE suppliers ADD COLUMN neighborhood TEXT",
            'city': "ALTER TABLE suppliers ADD COLUMN city TEXT",
            'state': "ALTER TABLE suppliers ADD COLUMN state TEXT",
            'country': "ALTER TABLE suppliers ADD COLUMN country TEXT",
            'postal_code': "ALTER TABLE suppliers ADD COLUMN postal_code TEXT",
            'category_id': "ALTER TABLE suppliers ADD COLUMN category_id INTEGER"
        }
        for column_name, sql in supplier_migrations.items():
            if column_name not in supplier_columns:
                logger.info(f"Adicionando coluna '{column_name}' à tabela 'suppliers'...")
                conn.execute(sql)
                conn.commit()

        # Adicionar colunas de endereço para clientes
        cursor.execute("PRAGMA table_info(clients)")
        client_columns = [column[1] for column in cursor.fetchall()]
        client_migrations = {
            'street': "ALTER TABLE clients ADD COLUMN street TEXT",
            'number': "ALTER TABLE clients ADD COLUMN number TEXT",
            'complement': "ALTER TABLE clients ADD COLUMN complement TEXT",
            'neighborhood': "ALTER TABLE clients ADD COLUMN neighborhood TEXT",
            'city': "ALTER TABLE clients ADD COLUMN city TEXT",
            'state': "ALTER TABLE clients ADD COLUMN state TEXT",
            'country': "ALTER TABLE clients ADD COLUMN country TEXT"
        }
        
        cursor.execute("PRAGMA table_info(products)")
        product_columns = [column[1] for column in cursor.fetchall()]
        if 'supplier_id' not in product_columns:
            logger.info("Adicionando coluna 'supplier_id' à tabela 'products'...")
            conn.execute("ALTER TABLE products ADD COLUMN supplier_id INTEGER")
            conn.commit()
        for column_name, sql in client_migrations.items():
            if column_name not in client_columns:
                logger.info(f"Adicionando coluna '{column_name}' à tabela 'clients'...")
                conn.execute(sql)
                conn.commit()
        
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao aplicar migrações: {e}")
        raise
