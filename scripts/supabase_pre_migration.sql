-- =============================================================================
-- PRÉ-MIGRAÇÃO: Script para preparar o Supabase antes de importar o dump
-- Executar ANTES de importar o backup do Render
-- Comando: psql "postgresql://postgres:<SENHA>@<HOST_SUPABASE>:5432/postgres" -f scripts\supabase_pre_migration.sql
-- =============================================================================

-- Extensões necessárias (Supabase geralmente já tem, mas garantindo)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- Confirmar extensões ativas
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('uuid-ossp', 'pgcrypto', 'citext')
ORDER BY extname;

-- =============================================================================
-- NOTA SOBRE O SCHEMA "public" NO SUPABASE
-- =============================================================================
-- O Supabase usa Row Level Security (RLS). As tabelas importadas NÃO terão
-- RLS ativo automaticamente. O sistema usa autenticação própria (session Flask),
-- então isso é SEGURO — não é necessário ativar RLS para este sistema.
--
-- Caso queira garantir que o schema público está acessível:
GRANT USAGE ON SCHEMA public TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres;
