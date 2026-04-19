# Fluxo Homologacao -> Producao

Este projeto agora suporta dois ambientes isolados de trabalho:

- Homologacao: para validar mudancas sem risco para o ambiente estavel.
- Producao: ambiente oficial para usuarios finais.

## 1. Estrutura criada

- `.env.homolog.example`: exemplo de variaveis para homologacao.
- `.env.production.example`: exemplo de variaveis para producao.
- `render.homolog.yaml`: blueprint Render para criar servico de homologacao separado.
- `render.yaml`: mantido para producao, agora com `APP_ENV=production`.
- `scripts/start_env.ps1`: sobe localmente em development/homolog/production.
- `scripts/promote_homolog_to_production.ps1`: promove branch homolog para producao com merge controlado.

## 2. Isolamento recomendado

1. Crie dois bancos separados:
- Producao: `mini_erp_prod`
- Homologacao: `mini_erp_homolog`

2. Crie os arquivos locais reais (nao versionados):
- `.env.homolog`
- `.env.production`

3. Configure `SECRET_KEY` diferente para cada ambiente.

4. No Render, use dois servicos distintos:
- `mini-erp` (producao) usando `render.yaml`
- `mini-erp-homolog` (homolog) usando `render.homolog.yaml`

## 3. Estrategia de branches

- `main`: producao
- `homolog`: validacao previa

Fluxo:

1. Desenvolver em `homolog`
2. Validar em ambiente de homologacao
3. Promover para `main` quando aprovado

## 4. Execucao local por ambiente

```powershell
# Development
.\scripts\start_env.ps1 -Environment development

# Homologacao
.\scripts\start_env.ps1 -Environment homolog

# Producao local
.\scripts\start_env.ps1 -Environment production
```

## 5. Promocao rapida homolog -> producao

```powershell
.\scripts\promote_homolog_to_production.ps1
```

Comportamento do script:

- Falha se houver alteracoes locais nao commitadas.
- Atualiza branches remotos (`fetch/pull`).
- Faz merge `homolog` -> `main` com commit de promocao.
- Faz push para `main` (disparando deploy de producao).

## 6. Boas praticas de seguranca

- Nunca reutilizar o mesmo `DATABASE_URL` entre homolog e producao.
- Nunca reutilizar o mesmo `SECRET_KEY` entre homolog e producao.
- Sempre validar migracoes e processos financeiros em homolog antes da promocao.
