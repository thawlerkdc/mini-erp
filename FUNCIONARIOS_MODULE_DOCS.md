# Módulo de Gestão de Funcionários - Documentação Técnica

## Visão geral
O módulo de Funcionários foi implementado com arquitetura multiempresa baseada em `account_id` (equivalente ao conceito `empresa_id` no projeto). Todas as tabelas novas incluem ambos os campos (`account_id` e `empresa_id`) para facilitar evolução SaaS.

## Componentes implementados
- Backend: `employees_module.py` (Blueprint Flask `employees_bp`)
- Menu lateral: seção Funcionários em `templates/base.html`
- Permissões: módulo `funcionarios` em `access_control.py`
- Banco e migrações: novas tabelas e índices em `models.py`
- Job de automação mensal: `scripts/run_employee_monthly_job.py`
- UI: templates dedicados
  - `_funcionarios_nav.html`
  - `funcionarios_dashboard.html`
  - `funcionarios_list.html`
  - `funcionario_form.html`
  - `funcionarios_dimension.html`
  - `funcionarios_despesas.html`
  - `funcionarios_relatorios.html`
  - `funcionarios_documentos.html`

## Tabelas novas
- `employee_positions`
- `employee_departments`
- `employee_cost_centers`
- `employees`
- `employee_documents`
- `employee_salary_history`
- `employee_expenses`

## Integração com Financeiro
A integração é feita por geração automática de lançamentos em `financial_entries` com:
- `source = 'employee_expense'`
- `source_ref = 'employee:{employee_id}:{expense_type}:{YYYY-MM}'`

Cada componente financeiro do funcionário gera registro individual por mês:
- salário
- comissão
- bonificação
- vale transporte
- vale alimentação
- plano de saúde
- outros benefícios
- descontos fixos (compensação em tipo `receivable`)

Também há rastreio no módulo via `employee_expenses`, vinculando `financial_entry_id`.

## Upload de foto
- Compressão e redimensionamento com Pillow (WebP, qualidade otimizada)
- Prioridade de armazenamento: Supabase Storage
  - variáveis esperadas:
    - `SUPABASE_URL`
    - `SUPABASE_SERVICE_ROLE_KEY`
    - `SUPABASE_STORAGE_EMPLOYEE_BUCKET` (opcional, padrão `employee-photos`)
- Fallback local automático: `static/img/employees`

## Rotas
- `GET /funcionarios/dashboard`
- `GET /funcionarios`
- `GET|POST /funcionarios/novo`
- `GET|POST /funcionarios/<id>/editar`
- `GET|POST /funcionarios/cargos`
- `GET|POST /funcionarios/departamentos`
- `GET|POST /funcionarios/centros-custo`
- `GET|POST /funcionarios/despesas`
- `GET /funcionarios/relatorios`
- `GET /funcionarios/relatorios/export?format=excel|pdf&month=YYYY-MM`
- `GET|POST /funcionarios/<id>/documentos`

## Automação mensal (recorrência)
- Geração automática de despesas fixas mensais por colaborador implementada no job:
  - `python scripts/run_employee_monthly_job.py`
- O job processa todas as contas ativas (`accounts.is_active = 1`) e sincroniza:
  - `employee_expenses`
  - `financial_entries` com `is_recurring = 1` e `recurrence_days = 30`

## Segurança e performance
- Filtro por `account_id` em todas as consultas
- Paginação na listagem principal
- Índices para consultas por conta/status/departamento/centro
- Índices para alertas de reajuste e documentos por colaborador
- Evita duplicação de despesas mensais por chave única (`employee_id + reference_month + expense_type`)

## Dashboard executivo
- KPIs de custo, média salarial, ativos, maior custo individual
- Indicadores avançados:
  - variação mensal da folha (percentual e valor)
  - departamento mais caro
  - centro de custo mais caro
- Gráficos:
  - pizza por cargo
  - pizza por departamento
  - pizza por centro de custo
  - barras por funcionário
  - linha de evolução mensal da folha
- Alertas:
  - aniversários
  - férias
  - vencimento de contrato
  - reajuste salarial

## Evolução futura prevista
- RLS nativo quando houver API externa por tenant
- Módulo RH ampliado (documentos, férias detalhadas, admissões/desligamentos)

## Atualização recente
- Exportação de relatórios de funcionários implementada (Excel e PDF) em `employees.funcionarios_relatorios_export`
