# Módulo de Gestão de Funcionários - Documentação Técnica

## Visão geral
O módulo de Funcionários foi implementado com arquitetura multiempresa baseada em `account_id` (equivalente ao conceito `empresa_id` no projeto). Todas as tabelas novas incluem ambos os campos (`account_id` e `empresa_id`) para facilitar evolução SaaS.

## Componentes implementados
- Backend: `employees_module.py` (Blueprint Flask `employees_bp`)
- Menu lateral: seção Funcionários em `templates/base.html`
- Permissões: módulo `funcionarios` em `access_control.py`
- Banco e migrações: novas tabelas e índices em `models.py`
- UI: templates dedicados
  - `_funcionarios_nav.html`
  - `funcionarios_dashboard.html`
  - `funcionarios_list.html`
  - `funcionario_form.html`
  - `funcionarios_dimension.html`
  - `funcionarios_despesas.html`
  - `funcionarios_relatorios.html`

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

## Segurança e performance
- Filtro por `account_id` em todas as consultas
- Paginação na listagem principal
- Índices para consultas por conta/status/departamento/centro
- Evita duplicação de despesas mensais por chave única (`employee_id + reference_month + expense_type`)

## Evolução futura prevista
- RLS nativo quando houver API externa por tenant
- Alertas assíncronos por scheduler (aniversário, férias, contrato, reajuste)
- Módulo RH ampliado (documentos, férias detalhadas, admissões/desligamentos)

## Atualização recente
- Exportação de relatórios de funcionários implementada (Excel e PDF) em `employees.funcionarios_relatorios_export`
