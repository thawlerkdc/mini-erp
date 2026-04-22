# Rodada de Testes - Homologacao 2026-04-21 R1

## Cabecalho

| Campo | Preenchimento |
| --- | --- |
| Rodada | Homologacao 2026-04-21 R1 |
| Ambiente | Homolog |
| Responsavel |  |
| Build/Commit | ccfbea1 |
| Base de dados |  |
| Data e hora de inicio |  |
| Data e hora de fim |  |
| Status geral | Nao iniciado |

## Ordem de execucao recomendada

1. Smoke test inicial
2. Fluxo ponta a ponta (compra -> estoque -> venda -> financeiro -> relatorios)
3. Permissoes e auditoria
4. Importacoes (Excel e XML)
5. Regressao final curta

## Controle rapido por bloco

| Bloco | Objetivo | Status |
| --- | --- | --- |
| B1 | Smoke test inicial | Nao iniciado |
| B2 | Cadastro base e parametros | Nao iniciado |
| B3 | Compras e estoque | Nao iniciado |
| B4 | Vendas e caixa | Nao iniciado |
| B5 | Financeiro | Nao iniciado |
| B6 | Relatorios | Nao iniciado |
| B7 | Permissoes e auditoria | Nao iniciado |
| B8 | Importacoes Excel/XML | Nao iniciado |

## Casos prioritarios desta rodada

| ID | Modulo | Cenario | Resultado esperado | Resultado obtido | Status | Evidencia | Defeito |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SMK-01 | Login | Abrir tela inicial e autenticar | Dashboard abre sem erro |  | Nao iniciado |  |  |
| PAR-01 | Parametros | Salvar parametros basicos | Dados persistem |  | Nao iniciado |  |  |
| CAD-EST-01 | Cadastros | Criar categoria e unidade | Itens disponiveis em produtos |  | Nao iniciado |  |  |
| PRO-01 | Produtos | Cadastrar produto base | Produto salvo e ativo |  | Nao iniciado |  |  |
| COM-01 | Compras | Entrada manual de estoque | Estoque aumenta e gera movimento |  | Nao iniciado |  |  |
| COM-05 | Compras | Pedido com contas a pagar | Parcelas criadas no financeiro |  | Nao iniciado |  |  |
| COM-06 | Compras | Receber pedido de compra | Estoque atualiza e pedido fica recebido |  | Nao iniciado |  |  |
| VEN-01 | Vendas | Venda simples dinheiro | Estoque baixa e venda salva |  | Nao iniciado |  |  |
| VEN-07 | Vendas | Multipagamento | Soma das formas bate com total |  | Nao iniciado |  |  |
| FIN-09 | Financeiro | Venda gera contas a receber | Titulo de origem sale criado |  | Nao iniciado |  |  |
| FIN-05 | Financeiro | Pagamento parcial | Saldo remanescente permanece aberto |  | Nao iniciado |  |  |
| FIN-07 | Financeiro | Estorno de pagamento | Titulo volta para pendente |  | Nao iniciado |  |  |
| REL-04 | Relatorios | Estoque por produto com filtro | Lista respeita filtro e ordenacao |  | Nao iniciado |  |  |
| REL-10 | Relatorios | Exportar Excel/PDF | Arquivos baixam sem erro |  | Nao iniciado |  |  |
| ACL-03 | Permissoes | Acesso via URL sem permissao | Bloqueio efetivo e auditavel |  | Nao iniciado |  |  |
| AUD-02 | Auditoria | Filtro por usuario | Logs filtram corretamente |  | Nao iniciado |  |  |
| IMP-03 | Importacao Excel | Planilha com coluna faltante | Retorno com erros |  | Nao iniciado |  |  |
| COM-10 | XML | Reimportar XML igual | Sistema bloqueia duplicidade |  | Nao iniciado |  |  |

## Defeitos encontrados

| ID do defeito | Modulo | Resumo | Severidade | Reproduzivel | Status | Responsavel |
| --- | --- | --- | --- | --- | --- | --- |

## Decisao da rodada

- Liberado para producao
- Liberado com ressalvas
- Nao liberado para producao
