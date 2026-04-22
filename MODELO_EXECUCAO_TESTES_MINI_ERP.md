# Modelo de Execucao de Testes - Mini ERP

## 1. Cabecalho da rodada

| Campo | Preenchimento |
| --- | --- |
| Rodada | Ex.: Homologacao 2026-04-21 R1 |
| Ambiente | Local / Homolog / Pre-producao |
| Responsavel | Nome do executor |
| Build/Commit | Hash ou descricao da versao testada |
| Base de dados | Limpa / restaurada / compartilhada |
| Data e hora de inicio |  |
| Data e hora de fim |  |
| Status geral | Aprovado / Aprovado com ressalvas / Reprovado |

## 2. Registro resumido por cenario

| ID | Modulo | Cenario | Resultado esperado | Resultado obtido | Status | Evidencia | Defeito |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AUT-01 | Login | Login valido | Dashboard abre apos autenticacao |  | Nao iniciado |  |  |
| PRO-06 | Produtos | Conversao compra/venda | Estoque sobe na unidade correta |  | Nao iniciado |  |  |
| COM-05 | Compras | Pedido com contas a pagar | Parcelas geradas no financeiro |  | Nao iniciado |  |  |
| VEN-01 | Vendas | Venda simples em dinheiro | Venda salva e estoque reduz |  | Nao iniciado |  |  |
| FIN-05 | Financeiro | Pagamento parcial | Saldo remanescente fica aberto |  | Nao iniciado |  |  |
| REL-10 | Relatorios | Exportar Excel/PDF | Arquivos gerados com sucesso |  | Nao iniciado |  |  |

Status sugerido:

- Nao iniciado
- Em execucao
- Aprovado
- Aprovado com ressalva
- Reprovado
- Bloqueado

## 3. Registro detalhado por caso

Copie esta tabela para cada caso executado.

| Campo | Conteudo |
| --- | --- |
| ID do teste | Ex.: VEN-07 |
| Modulo | Ex.: Vendas |
| Nome do caso | Ex.: Venda com multiplas formas de pagamento |
| Objetivo | O que este teste quer validar |
| Pre-condicoes | Dados e configuracoes necessarias |
| Massa de dados usada | Cliente, produto, pedido, XML, etc. |
| Passos executados | Lista objetiva dos passos realizados |
| Resultado esperado | Comportamento correto |
| Resultado obtido | O que realmente aconteceu |
| Status | Aprovado / Reprovado / Bloqueado |
| Evidencia | Print, ID da venda, ID do pedido, horario, arquivo exportado |
| Defeito vinculado | Ex.: BUG-014 |
| Observacoes | Impacto, risco, comportamento intermitente |

## 4. Modelo de caso preenchivel

### Caso de teste

- ID: 
- Modulo: 
- Nome do caso: 
- Objetivo: 
- Pre-condicoes: 
- Massa de dados usada: 

### Passos

1. 
2. 
3. 
4. 

### Resultado esperado

- 

### Resultado obtido

- 

### Fechamento

- Status: 
- Evidencia: 
- Defeito vinculado: 
- Observacoes: 

## 5. Controle de defeitos encontrados

| ID do defeito | Modulo | Resumo | Severidade | Reproduzivel | Status | Responsavel |
| --- | --- | --- | --- | --- | --- | --- |
| BUG-001 |  |  | Critica / Alta / Media / Baixa | Sim / Nao | Aberto / Corrigido / Validado |  |

## 6. Resumo final da rodada

| Indicador | Valor |
| --- | --- |
| Total planejado |  |
| Total executado |  |
| Aprovados |  |
| Aprovados com ressalva |  |
| Reprovados |  |
| Bloqueados |  |
| Defeitos criticos |  |
| Defeitos altos |  |
| Defeitos medios |  |
| Defeitos baixos |  |

## 7. Decisao da rodada

Marque uma decisao objetiva:

- Liberado para producao
- Liberado com ressalvas
- Nao liberado para producao

## 8. Recomendacao pratica de uso

Sempre que uma correcao for feita:

1. reexecute o caso que falhou
2. execute novamente o fluxo ponta a ponta relacionado
3. registre a validacao no mesmo documento