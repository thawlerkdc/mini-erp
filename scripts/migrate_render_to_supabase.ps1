# =============================================================================
# MIGRACAO: PostgreSQL Render -> Supabase
# Sistema: Mini ERP
# OS: Windows (PowerShell)
# =============================================================================

$DATABASE_URL_RENDER    = $env:DATABASE_URL_RENDER
$DATABASE_URL_SUPABASE  = $env:DATABASE_URL_SUPABASE

if ([string]::IsNullOrWhiteSpace($DATABASE_URL_RENDER)) {
    Write-Host "ERRO: defina a variavel DATABASE_URL_RENDER antes de executar." -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($DATABASE_URL_SUPABASE)) {
    Write-Host "ERRO: defina a variavel DATABASE_URL_SUPABASE antes de executar." -ForegroundColor Red
    exit 1
}

# Adicionar PostgreSQL 18 ao PATH desta sessao
$env:PATH = "C:\Program Files\PostgreSQL\18\bin;" + $env:PATH

$TIMESTAMP     = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_DIR    = ".\backups\migration_$TIMESTAMP"
$BACKUP_FULL   = "$BACKUP_DIR\render_backup_full.sql"
$BACKUP_SCHEMA = "$BACKUP_DIR\render_backup_schema_only.sql"
$LOG_FILE      = "$BACKUP_DIR\migration_log.txt"

function Write-Step($n, $msg) { Write-Host ""; Write-Host "[$n] $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  OK: $msg"    -ForegroundColor Green  }
function Write-ERR($msg)  { Write-Host "  ERRO: $msg"  -ForegroundColor Red    }
function Write-WARN($msg) { Write-Host "  AVISO: $msg" -ForegroundColor Yellow }

# 1. Pre-requisitos
Write-Step "1/8" "Verificando pre-requisitos..."
if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) { Write-ERR "pg_dump nao encontrado."; exit 1 }
if (-not (Get-Command psql   -ErrorAction SilentlyContinue)) { Write-ERR "psql nao encontrado.";    exit 1 }
Write-OK "pg_dump e psql encontrados"

# 2. Criar diretorio
Write-Step "2/8" "Criando diretorio de backup..."
New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null
Write-OK "Diretorio: $BACKUP_DIR"
"=== LOG MIGRACAO ===" | Out-File -FilePath $LOG_FILE -Encoding UTF8

# 3. Backup completo
Write-Step "3/8" "Gerando backup COMPLETO do Render (schema + dados)..."
& pg_dump --no-owner --no-acl --format=plain --encoding=UTF8 --verbose "--file=$BACKUP_FULL" $DATABASE_URL_RENDER 2>&1 | Tee-Object -FilePath $LOG_FILE -Append
if ($LASTEXITCODE -ne 0) { Write-ERR "Falha no backup. Verifique conectividade e a URL do Render."; exit 1 }
Write-OK "Backup completo: $([math]::Round((Get-Item $BACKUP_FULL).Length/1KB,1)) KB"

# 4. Backup schema-only
Write-Step "4/8" "Gerando backup SCHEMA-ONLY..."
& pg_dump --no-owner --no-acl --schema-only --format=plain --encoding=UTF8 "--file=$BACKUP_SCHEMA" $DATABASE_URL_RENDER 2>&1 | Tee-Object -FilePath $LOG_FILE -Append
if ($LASTEXITCODE -eq 0) { Write-OK "Schema-only gerado" } else { Write-WARN "Falha no schema-only (nao critico)" }

# 5. Extensoes no Supabase
Write-Step "5/8" "Habilitando extensoes no Supabase..."
$ext = 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; CREATE EXTENSION IF NOT EXISTS "pgcrypto";'
$ext | & psql $DATABASE_URL_SUPABASE 2>&1 | Tee-Object -FilePath $LOG_FILE -Append
Write-OK "Extensoes OK"

# 6. Importar no Supabase
Write-Step "6/8" "Importando no Supabase (aguarde)..."
& psql --single-transaction "--set=ON_ERROR_STOP=on" --echo-errors "--file=$BACKUP_FULL" $DATABASE_URL_SUPABASE 2>&1 | Tee-Object -FilePath $LOG_FILE -Append
if ($LASTEXITCODE -ne 0) {
    Write-WARN "Erros na importacao. Verifique: $LOG_FILE"
} else {
    Write-OK "Importacao concluida sem erros"
}

# 7. Validar tabelas
Write-Step "7/8" "Verificando tabelas criticas..."
$tables = @("accounts","users","products","categories","units","suppliers","clients","sales",
            "sale_items","expenses","stock_movements","financial_entries","financial_categories",
            "financial_payment_history","account_settings","saas_plans","saas_subscriptions",
            "saas_billing_events","user_permissions","logs","password_reset_tokens",
            "quick_access_tokens","purchase_orders","sale_fiscal_documents","fiscal_emission_logs",
            "nfe_imports","global_settings","saas_usage_daily","saas_insights")
foreach ($t in $tables) {
    $c = "SELECT COUNT(*) FROM $t;" | & psql $DATABASE_URL_SUPABASE -t -A 2>&1
    if ($LASTEXITCODE -eq 0) { Write-OK "$t ($c registros)" } else { Write-ERR "$t NAO ENCONTRADA" }
}

# 8. Instrucoes finais
Write-Step "8/8" "Concluido!"
Write-Host ""
Write-Host "PROXIMOS PASSOS:" -ForegroundColor Yellow
Write-Host "  1. Atualize DATABASE_URL no Render Web Service:"
Write-Host "     <URL do Supabase definida em DATABASE_URL_SUPABASE>"
Write-Host "  2. Valide no dashboard do Supabase"
Write-Host "  3. Log completo: $LOG_FILE"
