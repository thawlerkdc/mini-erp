# GUIA DE MIGRAÇÃO: Render PostgreSQL → Supabase

**Sistema:** Mini ERP  
**Data:** 04/05/2026  
**Destino:** instância Supabase definida pela equipe

---

## ⚠️ ANTES DE COMEÇAR

### Obter credenciais do Render
1. Acesse o Render Dashboard → seu banco PostgreSQL
2. Clique em **"Info"** ou **"Connect"**
3. Copie a **"External Database URL"** (formato: `postgresql://USER:PASS@HOST:PORT/DBNAME`)

---

## PASSO A PASSO

### 1. Preencher credenciais no script
Edite o arquivo `scripts\migrate_render_to_supabase.ps1` e substitua:
```
$DATABASE_URL_RENDER = "postgresql://USER:PASSWORD@HOST:PORT/DATABASE"
```
pela URL real copiada do Render.

---

### 2. Executar o script de migração (recomendado)
```powershell
# No terminal PowerShell, na raiz do projeto:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\scripts\migrate_render_to_supabase.ps1
```
O script executa automaticamente todas as etapas abaixo.

---

### 3. Executar manualmente (alternativo)

#### 3a. Backup completo (schema + dados)
```powershell
$RENDER = "postgresql://USER:PASSWORD@HOST:PORT/DATABASE"
$SUPABASE = "postgresql://postgres:<SENHA>@<HOST_SUPABASE>:5432/postgres"

pg_dump `
  --no-owner `
  --no-acl `
  --format=plain `
  --encoding=UTF8 `
  --file="backups\render_backup_full.sql" `
  $RENDER
```

#### 3b. Backup somente schema (sem dados)
```powershell
pg_dump `
  --no-owner `
  --no-acl `
  --schema-only `
  --format=plain `
  --encoding=UTF8 `
  --file="backups\render_backup_schema.sql" `
  $RENDER
```

#### 3c. Preparar Supabase
```powershell
psql $SUPABASE -f scripts\supabase_pre_migration.sql
```

#### 3d. Importar no Supabase
```powershell
psql `
  --single-transaction `
  --set=ON_ERROR_STOP=on `
  --echo-errors `
  --file="backups\render_backup_full.sql" `
  $SUPABASE
```

#### 3e. Validar integridade
```powershell
psql $SUPABASE -f scripts\supabase_post_migration_validation.sql
```

---

## POSSÍVEIS PROBLEMAS E SOLUÇÕES

| Problema | Causa | Solução |
|----------|-------|---------|
| `role "xyz" does not exist` | O Render cria roles internos | Use `--no-owner --no-acl` no pg_dump (já incluído) |
| `extension "xyz" not found` | Extensão não habilitada | Execute `supabase_pre_migration.sql` antes |
| `duplicate key value` | Objeto já existe | Execute em banco limpo ou use `--if-not-exists` |
| `permission denied for schema public` | Permissão no Supabase | O `supabase_pre_migration.sql` já resolve |
| Timeout de conexão | IP bloqueado no Render | Render gratuito libera acesso externo por padrão |

---

## PÓS-MIGRAÇÃO: ATUALIZAR VARIÁVEL DE AMBIENTE

### No Render (serviço web):
1. Dashboard → seu Web Service → **Environment**
2. Edite `DATABASE_URL`:
   ```
  postgresql://postgres:<SENHA>@<HOST_SUPABASE>:5432/postgres
   ```
3. Clique **Save Changes** → o serviço será redeploy automaticamente

### Local (desenvolvimento):
Crie ou edite `.env`:
```
DATABASE_URL=postgresql://postgres:<SENHA>@<HOST_SUPABASE>:5432/postgres
```

---

## CHECKLIST DE VALIDAÇÃO FINAL

### Banco de dados
- [ ] Todas as 33+ tabelas foram criadas
- [ ] Foreign keys estão intactas (verificadas pelo script SQL)
- [ ] Sequences sincronizadas com os dados (IDs corretos)
- [ ] Índices únicos recriados
- [ ] Registros de accounts e users presentes

### Sistema
- [ ] Login funcionando normalmente
- [ ] Dashboard carrega sem erros
- [ ] Vendas — listar e criar nova venda
- [ ] Estoque — listar produtos e ajustar estoque
- [ ] Financeiro — listar lançamentos
- [ ] Clientes — listar e cadastrar
- [ ] Relatórios — gerar pelo menos um relatório
- [ ] Painel SaaS — acessível (se admin)

### Infraestrutura
- [ ] Variável `DATABASE_URL` atualizada no Render
- [ ] Redeploy do serviço web concluído
- [ ] Nenhum erro 500 no sistema
- [ ] Logs do servidor sem erros de conexão DB

### Segurança
- [ ] Backup do Render salvo em local seguro (`backups/migration_*/`)
- [ ] Banco do Render mantido temporariamente (não excluir ainda)
- [ ] Testar o sistema por 48h antes de encerrar o banco Render

---

## SCRIPTS DISPONÍVEIS

| Arquivo | Descrição |
|---------|-----------|
| `scripts\migrate_render_to_supabase.ps1` | Script completo automatizado |
| `scripts\supabase_pre_migration.sql` | Extensões e permissões no Supabase |
| `scripts\supabase_post_migration_validation.sql` | Validação de integridade pós-migração |

---

## TABELAS MIGRADAS (33 tabelas)

**Auth/Sistema:** `accounts`, `users`, `password_reset_tokens`, `quick_access_tokens`, `webauthn_credentials`, `webauthn_challenges`, `global_settings`

**Negócio:** `categories`, `units`, `suppliers`, `clients`, `products`, `sales`, `sale_items`, `expenses`, `stock_movements`, `purchase_orders`, `account_settings`

**Financeiro:** `financial_categories`, `financial_entries`, `financial_payment_history`

**Fiscal:** `nfe_imports`, `sale_fiscal_documents`, `fiscal_emission_logs`

**SaaS:** `saas_plans`, `saas_plan_price_history`, `saas_subscriptions`, `saas_billing_events`, `saas_usage_daily`, `saas_insights`, `saas_automation_settings`, `saas_panel_access_logs`

**Auditoria:** `logs`, `user_permissions`
