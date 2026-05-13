-- =============================================================================
-- PÓS-MIGRAÇÃO: Validação de integridade — Mini ERP
-- Execute após importar o backup no Supabase
-- Comando: psql "postgresql://postgres:<SENHA>@<HOST_SUPABASE>:5432/postgres" -f scripts\supabase_post_migration_validation.sql
-- =============================================================================

\echo '============================================================'
\echo 'VALIDAÇÃO PÓS-MIGRAÇÃO — Mini ERP'
\echo '============================================================'

-- -------------------------------------------------------------------
-- 1. CONTAGEM DE REGISTROS POR TABELA
-- -------------------------------------------------------------------
\echo ''
\echo '[1] Contagem de registros por tabela:'

SELECT
    relname        AS tabela,
    n_live_tup     AS registros
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY relname;

-- -------------------------------------------------------------------
-- 2. VERIFICAR TABELAS CRÍTICAS EXISTEM
-- -------------------------------------------------------------------
\echo ''
\echo '[2] Verificação de tabelas críticas:'

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
  AND table_name IN (
    'accounts', 'users', 'products', 'categories', 'units',
    'suppliers', 'clients', 'sales', 'sale_items', 'expenses',
    'stock_movements', 'financial_entries', 'financial_categories',
    'financial_payment_history', 'account_settings',
    'saas_plans', 'saas_subscriptions', 'saas_billing_events',
    'user_permissions', 'logs', 'password_reset_tokens',
    'quick_access_tokens', 'webauthn_credentials', 'webauthn_challenges',
    'global_settings', 'purchase_orders', 'sale_fiscal_documents',
    'fiscal_emission_logs', 'nfe_imports', 'saas_usage_daily',
    'saas_insights', 'saas_automation_settings', 'saas_panel_access_logs',
    'saas_plan_price_history'
  )
ORDER BY table_name;

-- -------------------------------------------------------------------
-- 3. VERIFICAR FOREIGN KEYS INTACTAS
-- -------------------------------------------------------------------
\echo ''
\echo '[3] Foreign Keys registradas:'

SELECT
    tc.table_name           AS tabela,
    kcu.column_name         AS coluna,
    ccu.table_name          AS tabela_referenciada,
    ccu.column_name         AS coluna_referenciada,
    tc.constraint_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;

-- -------------------------------------------------------------------
-- 4. VERIFICAR SEQUENCES (auto increment)
-- -------------------------------------------------------------------
\echo ''
\echo '[4] Sequences (verificar se estão sincronizadas com os dados):'

SELECT
    s.sequence_name,
    s.last_value
FROM (
    SELECT sequence_name,
           (xpath('/row/last_value/text()',
               query_to_xml('SELECT last_value FROM ' || quote_ident(sequence_name), false, true, ''))
           )[1]::text::bigint AS last_value
    FROM information_schema.sequences
    WHERE sequence_schema = 'public'
) s
ORDER BY sequence_name;

-- -------------------------------------------------------------------
-- 5. VERIFICAR ÍNDICES
-- -------------------------------------------------------------------
\echo ''
\echo '[5] Índices criados:'

SELECT
    indexname,
    tablename,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- -------------------------------------------------------------------
-- 6. VERIFICAR ACCOUNTS E USUÁRIOS
-- -------------------------------------------------------------------
\echo ''
\echo '[6] Accounts e usuários cadastrados:'

SELECT
    a.id    AS account_id,
    a.name  AS empresa,
    a.slug,
    a.status,
    COUNT(u.id) AS total_usuarios
FROM accounts a
LEFT JOIN users u ON u.account_id = a.id
GROUP BY a.id, a.name, a.slug, a.status
ORDER BY a.id;

-- -------------------------------------------------------------------
-- 7. VERIFICAR PRODUTOS E ESTOQUE
-- -------------------------------------------------------------------
\echo ''
\echo '[7] Produtos por account (amostra):'

SELECT
    account_id,
    COUNT(*) AS total_produtos,
    SUM(stock) AS estoque_total
FROM products
GROUP BY account_id
ORDER BY account_id;

-- -------------------------------------------------------------------
-- 8. VERIFICAR ENTRADAS FINANCEIRAS
-- -------------------------------------------------------------------
\echo ''
\echo '[8] Entradas financeiras por status:'

SELECT
    account_id,
    status,
    COUNT(*)                     AS quantidade,
    ROUND(SUM(amount)::numeric, 2) AS valor_total
FROM financial_entries
GROUP BY account_id, status
ORDER BY account_id, status;

-- -------------------------------------------------------------------
-- 9. TESTE DE ESCRITA (inserção e remoção de registro de teste)
-- -------------------------------------------------------------------
\echo ''
\echo '[9] Teste de escrita (inserção temporária em global_settings):'

INSERT INTO global_settings (setting_key, setting_value, updated_at)
VALUES ('__migration_test__', 'ok', NOW()::text)
ON CONFLICT (setting_key) DO UPDATE SET setting_value = 'ok', updated_at = NOW()::text;

SELECT setting_key, setting_value FROM global_settings WHERE setting_key = '__migration_test__';

DELETE FROM global_settings WHERE setting_key = '__migration_test__';

\echo '✅ Teste de escrita concluído com sucesso'

-- -------------------------------------------------------------------
-- 10. VERIFICAR PLANOS SAAS
-- -------------------------------------------------------------------
\echo ''
\echo '[10] Planos SaaS cadastrados:'

SELECT id, name, price_monthly, is_active FROM saas_plans ORDER BY id;

\echo ''
\echo '============================================================'
\echo 'VALIDAÇÃO CONCLUÍDA — Revise os resultados acima'
\echo '============================================================'
