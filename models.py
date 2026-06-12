import logging
import os
import time
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

# Importar psycopg para PostgreSQL (opcional em desenvolvimento)
try:
    import psycopg
except ImportError:
    psycopg = None
    print("⚠️  psycopg não disponível - usando SQLite para desenvolvimento local")

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
    """
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        token TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quick_access_tokens (
        id SERIAL PRIMARY KEY,
        token_hash TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL REFERENCES users(id),
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        user_agent_hash TEXT,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        last_used_at TEXT,
        revoked INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS webauthn_credentials (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        credential_id TEXT UNIQUE NOT NULL,
        public_key TEXT NOT NULL,
        sign_count INTEGER DEFAULT 0,
        transports TEXT,
        created_at TEXT NOT NULL,
        last_used_at TEXT,
        revoked INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS webauthn_challenges (
        id SERIAL PRIMARY KEY,
        account_id INTEGER,
        user_id INTEGER,
        purpose TEXT NOT NULL,
        challenge TEXT UNIQUE NOT NULL,
        metadata_json TEXT,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS global_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT,
        updated_at TEXT NOT NULL
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
        notes TEXT,
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
        notes TEXT,
        gender TEXT DEFAULT 'nao_informar'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        product_code TEXT,
        category_id INTEGER REFERENCES categories(id),
        unit_id INTEGER REFERENCES units(id),
        supplier_id INTEGER REFERENCES suppliers(id),
        cost DOUBLE PRECISION DEFAULT 0,
        price DOUBLE PRECISION DEFAULT 0,
        stock INTEGER DEFAULT 0,
        stock_min INTEGER DEFAULT 0,
        status TEXT DEFAULT 'ativo',
        image_url TEXT,
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
        subtotal_products DOUBLE PRECISION DEFAULT 0,
        nf_requested INTEGER DEFAULT 0,
        fiscal_status TEXT DEFAULT 'nao_solicitada',
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
        notes TEXT,
        created_by_user_id INTEGER,
        created_by_user_name TEXT
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
    CREATE TABLE IF NOT EXISTS financial_payment_history (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        entry_id INTEGER NOT NULL REFERENCES financial_entries(id),
        event_type TEXT NOT NULL,
        payment_date TEXT,
        payment_amount DOUBLE PRECISION,
        payment_method TEXT,
        notes TEXT,
        created_by_user_name TEXT,
        created_at TEXT NOT NULL
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
    CREATE TABLE IF NOT EXISTS sale_fiscal_documents (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        sale_id INTEGER NOT NULL REFERENCES sales(id),
        emit_requested INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'nao_solicitada',
        provider_name TEXT,
        provider_reference TEXT,
        environment TEXT,
        note_type TEXT,
        serie TEXT,
        number INTEGER,
        invoice_key TEXT,
        xml_content TEXT,
        pdf_url TEXT,
        error_message TEXT,
        attempts INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (sale_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fiscal_emission_logs (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        sale_id INTEGER REFERENCES sales(id),
        provider_name TEXT NOT NULL,
        provider_reference TEXT,
        operation TEXT NOT NULL,
        status TEXT NOT NULL,
        http_status INTEGER,
        retries INTEGER DEFAULT 0,
        response_time_ms INTEGER,
        estimated_cost DOUBLE PRECISION DEFAULT 0,
        invoice_key TEXT,
        error_message TEXT,
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
    """
    CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        user_id INTEGER REFERENCES users(id),
        endpoint TEXT,
        method TEXT,
        path TEXT,
        data TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_permissions (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        module TEXT NOT NULL,
        can_view INTEGER DEFAULT 1,
        can_edit INTEGER DEFAULT 0,
        can_delete INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT,
        UNIQUE (account_id, user_id, module)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_positions (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        empresa_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (account_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_departments (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        empresa_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (account_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_cost_centers (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        empresa_id INTEGER NOT NULL REFERENCES accounts(id),
        name TEXT NOT NULL,
        code TEXT,
        description TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (account_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employees (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        empresa_id INTEGER NOT NULL REFERENCES accounts(id),
        full_name TEXT NOT NULL,
        photo_url TEXT,
        cpf TEXT,
        rg TEXT,
        birth_date TEXT,
        sex TEXT,
        marital_status TEXT,
        phone TEXT,
        whatsapp TEXT,
        email TEXT,
        address TEXT,
        street TEXT,
        number TEXT,
        complement TEXT,
        neighborhood TEXT,
        city TEXT,
        state TEXT,
        country TEXT,
        postal_code TEXT,
        position_id INTEGER REFERENCES employee_positions(id),
        department_id INTEGER REFERENCES employee_departments(id),
        cost_center_id INTEGER REFERENCES employee_cost_centers(id),
        admission_date TEXT,
        contract_type TEXT NOT NULL DEFAULT 'clt',
        status TEXT NOT NULL DEFAULT 'ativo',
        salary_base DOUBLE PRECISION DEFAULT 0,
        commission DOUBLE PRECISION DEFAULT 0,
        bonus DOUBLE PRECISION DEFAULT 0,
        transportation_allowance DOUBLE PRECISION DEFAULT 0,
        meal_allowance DOUBLE PRECISION DEFAULT 0,
        health_plan DOUBLE PRECISION DEFAULT 0,
        other_benefits DOUBLE PRECISION DEFAULT 0,
        fixed_discounts DOUBLE PRECISION DEFAULT 0,
        monthly_total_cost DOUBLE PRECISION DEFAULT 0,
        vacation_start_date TEXT,
        vacation_end_date TEXT,
        contract_end_date TEXT,
        salary_review_date TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_documents (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        empresa_id INTEGER NOT NULL REFERENCES accounts(id),
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        document_type TEXT,
        file_url TEXT,
        file_name TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_salary_history (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        empresa_id INTEGER NOT NULL REFERENCES accounts(id),
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        previous_salary DOUBLE PRECISION DEFAULT 0,
        new_salary DOUBLE PRECISION DEFAULT 0,
        reason TEXT,
        changed_by_user_id INTEGER REFERENCES users(id),
        changed_by_user_name TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_expenses (
        id SERIAL PRIMARY KEY,
        account_id INTEGER NOT NULL REFERENCES accounts(id),
        empresa_id INTEGER NOT NULL REFERENCES accounts(id),
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        cost_center_id INTEGER REFERENCES employee_cost_centers(id),
        reference_month TEXT NOT NULL,
        expense_type TEXT NOT NULL,
        description TEXT,
        amount DOUBLE PRECISION NOT NULL DEFAULT 0,
        financial_entry_id INTEGER REFERENCES financial_entries(id),
        status TEXT NOT NULL DEFAULT 'pendente',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
]

_TENANT_MIGRATIONS = [
    "CREATE TABLE IF NOT EXISTS logs (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), user_id INTEGER REFERENCES users(id), endpoint TEXT, method TEXT, path TEXT, data TEXT, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS user_permissions (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), user_id INTEGER NOT NULL REFERENCES users(id), module TEXT NOT NULL, can_view INTEGER DEFAULT 1, can_edit INTEGER DEFAULT 0, can_delete INTEGER DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_permissions_unique ON user_permissions (account_id, user_id, module)",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS trade_name TEXT",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS cnpj TEXT",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS primary_email TEXT",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS phone TEXT",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS whatsapp TEXT",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS responsible_name TEXT",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ativa'",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS last_access_at TEXT",
    "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS updated_at TEXT",
    "UPDATE accounts SET status = 'ativa' WHERE status IS NULL OR BTRIM(status) = ''",
    "CREATE TABLE IF NOT EXISTS saas_plans (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, price_monthly DOUBLE PRECISION DEFAULT 0, price_yearly DOUBLE PRECISION DEFAULT 0, setup_fee DOUBLE PRECISION DEFAULT 0, features_json TEXT, limits_json TEXT, is_active INTEGER DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS saas_plan_price_history (id SERIAL PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES saas_plans(id), old_monthly DOUBLE PRECISION DEFAULT 0, old_yearly DOUBLE PRECISION DEFAULT 0, new_monthly DOUBLE PRECISION DEFAULT 0, new_yearly DOUBLE PRECISION DEFAULT 0, apply_scope TEXT DEFAULT 'novos', changed_by_user_id INTEGER, changed_by_user_name TEXT, changed_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS saas_subscriptions (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), plan_id INTEGER NOT NULL REFERENCES saas_plans(id), billing_cycle TEXT NOT NULL DEFAULT 'mensal', amount DOUBLE PRECISION DEFAULT 0, setup_fee_amount DOUBLE PRECISION DEFAULT 0, starts_at TEXT, next_due_date TEXT, status TEXT DEFAULT 'ativa', suspension_days INTEGER DEFAULT 10, auto_block_enabled INTEGER DEFAULT 1, apply_new_prices_to_existing INTEGER DEFAULT 0, updated_at TEXT NOT NULL)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_saas_subscriptions_account_unique ON saas_subscriptions (account_id)",
    "CREATE TABLE IF NOT EXISTS saas_billing_events (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), subscription_id INTEGER REFERENCES saas_subscriptions(id), charge_type TEXT NOT NULL DEFAULT 'mensalidade', reference_period TEXT, due_date TEXT NOT NULL, amount DOUBLE PRECISION NOT NULL, status TEXT NOT NULL DEFAULT 'pendente', paid_at TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS idx_saas_billing_account_status ON saas_billing_events (account_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_saas_billing_due_date ON saas_billing_events (due_date)",
    "CREATE TABLE IF NOT EXISTS saas_usage_daily (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), usage_date TEXT NOT NULL, active_users INTEGER DEFAULT 0, total_sessions INTEGER DEFAULT 0, avg_session_minutes DOUBLE PRECISION DEFAULT 0, top_screen TEXT, top_feature TEXT, created_at TEXT NOT NULL)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_saas_usage_account_date_unique ON saas_usage_daily (account_id, usage_date)",
    "CREATE TABLE IF NOT EXISTS saas_insights (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), insight_type TEXT NOT NULL, severity TEXT DEFAULT 'media', title TEXT NOT NULL, message TEXT NOT NULL, generated_on TEXT NOT NULL, resolved INTEGER DEFAULT 0)",
    "CREATE INDEX IF NOT EXISTS idx_saas_insights_account ON saas_insights (account_id, generated_on)",
    "CREATE TABLE IF NOT EXISTS saas_automation_settings (id SERIAL PRIMARY KEY, setting_key TEXT UNIQUE NOT NULL, setting_value TEXT, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS saas_panel_access_logs (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id), account_id INTEGER REFERENCES accounts(id), username TEXT, action TEXT NOT NULL, method TEXT, path TEXT, payload TEXT, created_at TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS idx_saas_panel_access_logs_created_at ON saas_panel_access_logs (created_at)",
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
    "UPDATE financial_entries SET source = 'manual' WHERE source IS NULL OR BTRIM(source) = ''",
    "CREATE TABLE IF NOT EXISTS financial_payment_history (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), entry_id INTEGER NOT NULL REFERENCES financial_entries(id), event_type TEXT NOT NULL, payment_date TEXT, payment_amount DOUBLE PRECISION, payment_method TEXT, notes TEXT, created_by_user_name TEXT, created_at TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS idx_financial_payment_history_entry ON financial_payment_history (entry_id)",
    "CREATE INDEX IF NOT EXISTS idx_financial_entries_source_ref ON financial_entries (account_id, source, source_ref)",
    "ALTER TABLE nfe_imports ADD COLUMN IF NOT EXISTS invoice_key TEXT",
    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS phone TEXT",
    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS whatsapp TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS margin_percent DOUBLE PRECISION DEFAULT 100",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS unit_buy TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS unit_sell TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS conversion_factor DOUBLE PRECISION DEFAULT 1",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS product_code TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ativo'",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url TEXT",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS created_at TEXT",
    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS created_at TEXT",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS created_at TEXT",
    "ALTER TABLE categories ADD COLUMN IF NOT EXISTS created_at TEXT",
    "ALTER TABLE units ADD COLUMN IF NOT EXISTS created_at TEXT",
    "ALTER TABLE clients ADD COLUMN IF NOT EXISTS notes TEXT",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS notes TEXT",
    "ALTER TABLE stock_movements ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER",
    "ALTER TABLE stock_movements ADD COLUMN IF NOT EXISTS created_by_user_name TEXT",
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS subtotal_products DOUBLE PRECISION DEFAULT 0",
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS nf_requested INTEGER DEFAULT 0",
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS fiscal_status TEXT DEFAULT 'nao_solicitada'",
    "CREATE TABLE IF NOT EXISTS sale_fiscal_documents (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), sale_id INTEGER NOT NULL REFERENCES sales(id), emit_requested INTEGER DEFAULT 0, status TEXT NOT NULL DEFAULT 'nao_solicitada', environment TEXT, note_type TEXT, serie TEXT, number INTEGER, invoice_key TEXT, xml_content TEXT, pdf_url TEXT, error_message TEXT, attempts INTEGER DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "ALTER TABLE sale_fiscal_documents ADD COLUMN IF NOT EXISTS provider_name TEXT",
    "ALTER TABLE sale_fiscal_documents ADD COLUMN IF NOT EXISTS provider_reference TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_sale_fiscal_documents_sale_unique ON sale_fiscal_documents (sale_id)",
    "CREATE TABLE IF NOT EXISTS fiscal_emission_logs (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), sale_id INTEGER REFERENCES sales(id), provider_name TEXT NOT NULL, provider_reference TEXT, operation TEXT NOT NULL, status TEXT NOT NULL, http_status INTEGER, retries INTEGER DEFAULT 0, response_time_ms INTEGER, estimated_cost DOUBLE PRECISION DEFAULT 0, invoice_key TEXT, error_message TEXT, created_at TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS idx_fiscal_emission_logs_account_created ON fiscal_emission_logs (account_id, created_at)",
    "UPDATE products SET conversion_factor = GREATEST(1, ROUND(COALESCE(conversion_factor, 1))) WHERE conversion_factor IS NULL OR conversion_factor <> ROUND(conversion_factor)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_products_account_product_code_unique ON products (account_id, product_code) WHERE product_code IS NOT NULL AND BTRIM(product_code) <> ''",
    "CREATE TABLE IF NOT EXISTS employee_positions (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), empresa_id INTEGER NOT NULL REFERENCES accounts(id), name TEXT NOT NULL, description TEXT, is_active INTEGER DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS employee_departments (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), empresa_id INTEGER NOT NULL REFERENCES accounts(id), name TEXT NOT NULL, description TEXT, is_active INTEGER DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS employee_cost_centers (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), empresa_id INTEGER NOT NULL REFERENCES accounts(id), name TEXT NOT NULL, code TEXT, description TEXT, is_active INTEGER DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS employees (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), empresa_id INTEGER NOT NULL REFERENCES accounts(id), full_name TEXT NOT NULL, photo_url TEXT, cpf TEXT, rg TEXT, birth_date TEXT, sex TEXT, marital_status TEXT, phone TEXT, whatsapp TEXT, email TEXT, address TEXT, street TEXT, number TEXT, complement TEXT, neighborhood TEXT, city TEXT, state TEXT, country TEXT, postal_code TEXT, position_id INTEGER REFERENCES employee_positions(id), department_id INTEGER REFERENCES employee_departments(id), cost_center_id INTEGER REFERENCES employee_cost_centers(id), admission_date TEXT, contract_type TEXT NOT NULL DEFAULT 'clt', status TEXT NOT NULL DEFAULT 'ativo', salary_base DOUBLE PRECISION DEFAULT 0, commission DOUBLE PRECISION DEFAULT 0, bonus DOUBLE PRECISION DEFAULT 0, transportation_allowance DOUBLE PRECISION DEFAULT 0, meal_allowance DOUBLE PRECISION DEFAULT 0, health_plan DOUBLE PRECISION DEFAULT 0, other_benefits DOUBLE PRECISION DEFAULT 0, fixed_discounts DOUBLE PRECISION DEFAULT 0, monthly_total_cost DOUBLE PRECISION DEFAULT 0, vacation_start_date TEXT, vacation_end_date TEXT, contract_end_date TEXT, salary_review_date TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS employee_documents (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), empresa_id INTEGER NOT NULL REFERENCES accounts(id), employee_id INTEGER NOT NULL REFERENCES employees(id), document_type TEXT, file_url TEXT, file_name TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS employee_salary_history (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), empresa_id INTEGER NOT NULL REFERENCES accounts(id), employee_id INTEGER NOT NULL REFERENCES employees(id), previous_salary DOUBLE PRECISION DEFAULT 0, new_salary DOUBLE PRECISION DEFAULT 0, reason TEXT, changed_by_user_id INTEGER REFERENCES users(id), changed_by_user_name TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS employee_expenses (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), empresa_id INTEGER NOT NULL REFERENCES accounts(id), employee_id INTEGER NOT NULL REFERENCES employees(id), cost_center_id INTEGER REFERENCES employee_cost_centers(id), reference_month TEXT NOT NULL, expense_type TEXT NOT NULL, description TEXT, amount DOUBLE PRECISION NOT NULL DEFAULT 0, financial_entry_id INTEGER REFERENCES financial_entries(id), status TEXT NOT NULL DEFAULT 'pendente', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "ALTER TABLE employee_positions ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
    "ALTER TABLE employee_departments ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
    "ALTER TABLE employee_cost_centers ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
    "ALTER TABLE employee_documents ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
    "ALTER TABLE employee_salary_history ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
    "ALTER TABLE employee_expenses ADD COLUMN IF NOT EXISTS empresa_id INTEGER",
    "UPDATE employee_positions SET empresa_id = account_id WHERE empresa_id IS NULL",
    "UPDATE employee_departments SET empresa_id = account_id WHERE empresa_id IS NULL",
    "UPDATE employee_cost_centers SET empresa_id = account_id WHERE empresa_id IS NULL",
    "UPDATE employees SET empresa_id = account_id WHERE empresa_id IS NULL",
    "UPDATE employee_documents SET empresa_id = account_id WHERE empresa_id IS NULL",
    "UPDATE employee_salary_history SET empresa_id = account_id WHERE empresa_id IS NULL",
    "UPDATE employee_expenses SET empresa_id = account_id WHERE empresa_id IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_employee_positions_name_unique ON employee_positions (account_id, name)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_employee_departments_name_unique ON employee_departments (account_id, name)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_employee_cost_centers_name_unique ON employee_cost_centers (account_id, name)",
    "CREATE INDEX IF NOT EXISTS idx_employees_account_status ON employees (account_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_employees_account_department ON employees (account_id, department_id)",
    "CREATE INDEX IF NOT EXISTS idx_employees_account_cost_center ON employees (account_id, cost_center_id)",
    "CREATE INDEX IF NOT EXISTS idx_employee_expenses_account_month ON employee_expenses (account_id, reference_month)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_employee_expenses_month_type_unique ON employee_expenses (account_id, employee_id, reference_month, expense_type)",
    "CREATE INDEX IF NOT EXISTS idx_employee_salary_history_account ON employee_salary_history (account_id, employee_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_employee_documents_account_employee ON employee_documents (account_id, employee_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_employees_salary_review ON employees (account_id, salary_review_date)",
    # Cancellation support for sales
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ativa'",
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS cancel_reason TEXT",
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS cancelled_at TEXT",
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS cancelled_by TEXT",
    "CREATE INDEX IF NOT EXISTS idx_sales_account_status ON sales (account_id, status)",
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


def _normalize_db_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if not url:
        return ""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    parsed = urlparse(url)
    query_pairs = dict(parse_qsl(parsed.query, keep_blank_values=True))

    host = (parsed.hostname or "").strip().lower()
    is_local_host = host in {"localhost", "127.0.0.1", "::1", ""}
    if not is_local_host and "sslmode" not in query_pairs:
        query_pairs["sslmode"] = "require"

    if "connect_timeout" not in query_pairs:
        query_pairs["connect_timeout"] = "10"

    if "keepalives" not in query_pairs:
        query_pairs["keepalives"] = "1"
    if "keepalives_idle" not in query_pairs:
        query_pairs["keepalives_idle"] = "30"
    if "keepalives_interval" not in query_pairs:
        query_pairs["keepalives_interval"] = "10"
    if "keepalives_count" not in query_pairs:
        query_pairs["keepalives_count"] = "5"

    updated_query = urlencode(query_pairs)
    return urlunparse(parsed._replace(query=updated_query))


def _resolve_db_url_and_source():
    database_url = (os.environ.get("DATABASE_URL") or "").strip()
    if database_url:
        return _normalize_db_url(database_url), "DATABASE_URL"

    supabase_db_url = (os.environ.get("SUPABASE_DB_URL") or "").strip()
    if supabase_db_url:
        return _normalize_db_url(supabase_db_url), "SUPABASE_DB_URL"

    pg_host = (os.environ.get("PGHOST") or "").strip()
    pg_port = (os.environ.get("PGPORT") or "5432").strip() or "5432"
    pg_database = (os.environ.get("PGDATABASE") or "").strip()
    pg_user = (os.environ.get("PGUSER") or "").strip()
    pg_password = (os.environ.get("PGPASSWORD") or "").strip()

    if pg_host and pg_database and pg_user and pg_password:
        encoded_user = quote(pg_user, safe="")
        encoded_password = quote(pg_password, safe="")
        pooler_url = f"postgresql://{encoded_user}:{encoded_password}@{pg_host}:{pg_port}/{pg_database}"
        return _normalize_db_url(pooler_url), "PG*"

    return "", "none"


def get_db_connection_diagnostics() -> dict:
    db_url, source = _resolve_db_url_and_source()
    parsed = urlparse(db_url) if db_url else None
    host = (parsed.hostname or "") if parsed else ""
    query_pairs = dict(parse_qsl(parsed.query, keep_blank_values=True)) if parsed else {}
    return {
        "url_configured": bool(db_url),
        "url_source": source,
        "db_host": host,
        "db_port": parsed.port if parsed else None,
        "db_name": (parsed.path or "").lstrip("/") if parsed else "",
        "is_supabase_host": host.endswith("supabase.co") if host else False,
        "is_pooler_host": host.endswith("pooler.supabase.com") if host else False,
        "sslmode": query_pairs.get("sslmode"),
    }


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
    url, _source = _resolve_db_url_and_source()
    return url


def _log_db_info():
    """Log informações sobre a configuração do banco de dados."""
    global _DB_INITIALIZED, _DB_ERROR
    
    diagnostics = get_db_connection_diagnostics()

    if diagnostics["url_configured"]:
        logger.info("📦 Usando PostgreSQL (Render/Produção ou Local)")
        logger.info(
            "   Fonte: %s | Host: %s | DB: %s | SSL: %s",
            diagnostics["url_source"],
            diagnostics["db_host"] or "n/a",
            diagnostics["db_name"] or "n/a",
            diagnostics["sslmode"] or "n/a",
        )
    else:
        logger.info("📦 URL de banco não configurada")
        logger.info("   Configure DATABASE_URL, SUPABASE_DB_URL ou PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD")
    
    _DB_INITIALIZED = True


class _Conn:
    """Wrapper que funciona com psycopg (PostgreSQL) ou sqlite3."""

    def __init__(self, conn):
        self._conn = conn

        # Detectar driver de forma explícita para evitar falso positivo em psycopg.
        module_name = type(conn).__module__
        self._is_sqlite = module_name.startswith("sqlite3")
        self._is_psycopg = module_name.startswith("psycopg")

    def _convert_sql_for_sqlite(self, sql):
        """Converte SQL PostgreSQL para SQLite: %s -> ?, SERIAL -> INTEGER, etc."""
        if not self._is_sqlite:
            return sql

        # Converter placeholders de parâmetros.
        if "%s" in sql:
            sql = sql.replace("%s", "?")

        # Converter tipos PostgreSQL para SQLite.
        sql = sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
        sql = sql.replace("SERIAL", "INTEGER")

        return sql

    def execute(self, sql, params=()):
        if self._is_sqlite:
            sql = self._convert_sql_for_sqlite(sql)
            cur = self._conn.execute(sql, params)
            return _Cursor(cur)
        else:
            # PostgreSQL
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return _Cursor(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


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
        # sqlite3 e psycopg retorna diferentes tipos de description
        columns = []
        for col_desc in self._cursor.description:
            if hasattr(col_desc, 'name'):
                # psycopg: psycopg.extensions.Column object com .name
                columns.append(col_desc.name)
            else:
                # sqlite3: tuple onde primeiro elemento é o nome
                columns.append(col_desc[0])
        return columns

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
    
    if psycopg is None:
        # Fallback para desenvolvimento local com SQLite
        import sqlite3
        logger.info("📦 Conectando ao SQLite (desenvolvimento local)")
        return _Conn(sqlite3.connect("kdc_systems.db"))

    last_exc = None
    for attempt in range(1, 4):
        try:
            pg_conn = psycopg.connect(db_url)
            return _Conn(pg_conn)
        except Exception as exc:
            last_exc = exc
            is_operational = psycopg and hasattr(psycopg, "OperationalError") and isinstance(
                exc, (psycopg.OperationalError, psycopg.DatabaseError)
            )
            if is_operational and attempt < 3:
                logger.warning(
                    "⚠️ Falha ao conectar no banco (tentativa %s/3). Retentando... Erro: %s",
                    attempt,
                    exc,
                )
                time.sleep(0.25 * attempt)
                continue
            logger.error(f"❌ Erro ao conectar ao banco de dados: {exc}")
            raise

    raise last_exc


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
    if not username or not password:
        return None

    conn = None
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT u.*, a.name AS account_name, a.slug AS account_slug, COALESCE(a.status, 'ativa') AS account_status "
            "FROM users u JOIN accounts a ON a.id = u.account_id "
            "WHERE LOWER(u.username) = LOWER(%s) AND u.password = %s AND u.is_active = 1",
            (username, password),
        ).fetchone()
        if not row:
            return None

        try:
            return dict(row)
        except Exception:
            # Fallback defensivo para ambientes onde dict(row) pode falhar.
            data = {
                "id": row["id"],
                "username": row["username"],
                "name": row.get("name"),
                "email": row.get("email"),
                "role": row.get("role"),
                "is_admin": row.get("is_admin", 0),
                "is_active": row.get("is_active", 1),
                "account_id": row["account_id"],
                "account_name": row.get("account_name"),
                "account_slug": row.get("account_slug"),
                "account_status": row.get("account_status", "ativa"),
            }
            return data
    finally:
        if conn:
            conn.close()


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