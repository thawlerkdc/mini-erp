# Plano Completo de Testes - Mini ERP

## 1. Objetivo

Validar o Mini ERP de forma pratica antes da producao, cobrindo:

- funcionamento ponta a ponta dos fluxos principais
- consistencia entre modulos
- regras de permissao e multiusuario
- integridade de estoque, financeiro e relatorios
- regressao basica das telas existentes

Este plano foi montado com base nos modulos reais do sistema:

- autenticacao e recuperacao de senha
- dashboard
- parametros
- cadastro de usuarios
- controle de acesso
- cadastro de clientes
- cadastro de fornecedores
- cadastro de categorias
- cadastro de unidades
- cadastro de produtos
- importacao de dados por Excel
- compras e entrada de estoque
- controle e ajustes de estoque
- vendas e fechamento de caixa
- financeiro
- relatorios
- auditoria
- manual
- troca de idioma e tema

## 2. Melhor Estrategia de Testes para Este Cenário

Para este ERP, a melhor abordagem antes de producao e combinar 5 camadas:

### 2.1. Smoke test inicial

Objetivo: confirmar rapidamente se o sistema sobe e se os menus principais carregam sem erro.

Cobrir:

- login
- dashboard
- cadastros
- compras
- estoque
- vendas
- financeiro
- relatorios
- parametros
- auditoria

Quando usar:

- depois de deploy local ou em homolog
- depois de correcoes urgentes
- antes de iniciar a bateria completa

### 2.2. Teste funcional por fluxo

Objetivo: validar o uso real do ERP, na sequencia em que o negocio opera.

Fluxo principal:

1. configurar conta e parametros
2. cadastrar estruturas basicas
3. cadastrar produto
4. registrar compra/entrada
5. conferir estoque
6. vender
7. validar contas a receber geradas
8. registrar contas a pagar/receber
9. validar relatorios
10. validar auditoria e permissoes

Esse e o teste mais importante para liberar producao.

### 2.3. Teste de regressao por modulo

Objetivo: depois do fluxo principal, testar cada tela com foco em inclusao, edicao, exclusao, filtro, mensagens e consistencia visual.

### 2.4. Teste orientado a risco

Objetivo: testar o que mais quebra em ERP pequeno:

- estoque ficando divergente
- financeiro duplicando ou perdendo vinculos
- permissoes falhando
- relatorios com totais diferentes do operacional
- importacoes com dados incompletos

### 2.5. Teste manual estruturado com evidencias

Objetivo: registrar o resultado de cada cenário com status, observacao e evidencia.

Recomendacao pratica:

- usar este plano como roteiro mestre
- usar o modelo de documentacao para registrar execucao
- salvar print das telas criticas e IDs gerados

## 3. Ambiente e Preparacao

## 3.1. Ambiente recomendado

- executar em homologacao ou local com base de testes
- evitar testar diretamente em dados produtivos
- se possivel, iniciar com base limpa ou snapshot restauravel

## 3.2. Massa de dados minima para teste

Criar ou garantir:

- 1 conta principal
- 1 usuario operador
- 1 usuario com acesso restrito
- 2 categorias de produto
- 2 unidades de medida
- 2 fornecedores
- 3 clientes
- 4 produtos ativos
- 1 produto com estoque baixo
- 1 produto com fator de conversao maior que 1
- 1 categoria financeira de receita
- 1 categoria financeira de despesa

## 3.3. Regras de execucao

- registrar data e responsavel por cada rodada
- usar sempre periodo conhecido nos relatorios
- anotar IDs de venda, pedido de compra e lancamento financeiro
- ao encontrar erro, registrar modulo, passo, impacto e evidencia

## 4. Fluxograma Textual Ideal de Testes Ponta a Ponta

Sequencia recomendada:

1. Acesso ao sistema
2. Login com conta principal
3. Validacao do dashboard
4. Configuracao de parametros basicos da empresa
5. Cadastro de unidades e categorias
6. Cadastro de fornecedores e clientes
7. Cadastro de produtos
8. Cadastro de usuario operador
9. Configuracao de permissoes desse usuario
10. Registro de compra manual
11. Criacao de pedido de compra
12. Recebimento do pedido de compra
13. Validacao do historico e da posicao de estoque
14. Ajuste de estoque de entrada e saida
15. Registro de venda simples
16. Registro de venda com cliente
17. Registro de venda com Pix ou cartao
18. Fechamento de caixa
19. Validacao do financeiro gerado automaticamente pelas vendas
20. Registro manual de conta a pagar
21. Registro de pagamento parcial
22. Registro de pagamento total
23. Estorno de pagamento
24. Validacao dos relatorios operacionais e financeiros
25. Validacao dos logs de auditoria
26. Login com usuario restrito
27. Validacao de bloqueios por permissao
28. Teste de importacao por Excel
29. Teste de XML no financeiro/compras
30. Revisao final de regressao basica em todas as telas

## 5. Checklist Mestre de Execucao

Use esta checklist na ordem abaixo.

### 5.1. Smoke test inicial

| ID | Tela/Modulo | Passos | Validacao esperada |
| --- | --- | --- | --- |
| SMK-01 | Login | Abrir a tela inicial | Tela carrega sem erro visual ou erro 500 |
| SMK-02 | Login | Entrar com usuario valido | Redireciona para dashboard |
| SMK-03 | Dashboard | Abrir painel principal | KPIs, cards e atalhos carregam |
| SMK-04 | Cadastros | Abrir clientes, fornecedores, produtos, categorias, unidades, usuarios | Todas as telas carregam e listam dados |
| SMK-05 | Compras | Abrir Compras | Tela de entrada, pedidos e XML abre corretamente |
| SMK-06 | Estoque | Abrir Historico/Controle de Estoque | Posicao, alertas e kardex aparecem |
| SMK-07 | Vendas | Abrir Vendas | Produtos e clientes carregam |
| SMK-08 | Financeiro | Abrir Financeiro | Resumo, lancamentos e categorias carregam |
| SMK-09 | Relatorios | Abrir Relatorios | Cards de secoes aparecem |
| SMK-10 | Parametros | Abrir Parametros | Formulario carrega e aceita consulta |
| SMK-11 | Auditoria | Abrir Auditoria | Lista e filtros carregam |
| SMK-12 | Manual | Abrir Manual | Conteudo abre sem quebrar layout |

### 5.2. Checklist por modulo

#### A. Autenticacao e sessao

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| AUT-01 | Login valido | Informar usuario e senha corretos | Acesso liberado e sessao iniciada |
| AUT-02 | Login invalido | Informar senha incorreta | Mensagem de usuario/senha invalidos |
| AUT-03 | Logout | Clicar em Sair | Sessao encerrada e retorno ao login |
| AUT-04 | Recuperacao de senha | Abrir Esqueci minha senha e enviar solicitacao | Tela responde corretamente sem travar fluxo |
| AUT-05 | Protecao de rota | Tentar abrir URL interna sem sessao | Redireciona para login ou bloqueia acesso |

#### B. Dashboard

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| DSH-01 | Carregamento inicial | Abrir dashboard apos login | Indicadores aparecem sem falha |
| DSH-02 | Troca de periodo | Alternar Hoje, 7 dias, 30 dias e Mes | KPIs e grafico atualizam |
| DSH-03 | Links rapidos | Abrir atalhos do dashboard | Cada link leva ao modulo correto |
| DSH-04 | Alertas | Validar alertas de estoque e financeiro | Quantidades e links coerentes |
| DSH-05 | Favoritos | Marcar e desmarcar favoritos | Cards e menu lateral refletem a mudanca |

#### C. Parametros

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| PAR-01 | Salvar configuracoes | Alterar parametros e salvar | Mensagem de sucesso e persistencia dos dados |
| PAR-02 | Teste SMTP | Informar email de teste e disparar teste | Sucesso claro ou erro explicito |
| PAR-03 | Pix e pagamentos | Configurar chave Pix, receptor e opcoes de cartao | Vendas passam a usar os parametros |
| PAR-04 | Modo somente leitura | Entrar com usuario sem editar parametros | Tela abre, mas bloqueia gravacao |

#### D. Cadastros estruturais

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| CAD-EST-01 | Categoria nova | Cadastrar categoria | Registro aparece na lista |
| CAD-EST-02 | Categoria duplicada | Repetir o mesmo nome | Mensagem de duplicidade |
| CAD-EST-03 | Unidade nova | Cadastrar unidade | Registro aparece na lista |
| CAD-EST-04 | Exclusao protegida | Tentar excluir categoria/unidade em uso | Sistema bloqueia exclusao |

#### E. Clientes

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| CLI-01 | Cadastro simples | Criar cliente com nome e dados basicos | Cliente salvo e listado |
| CLI-02 | Edicao | Alterar telefone, email e endereco | Dados atualizados corretamente |
| CLI-03 | Campos tratados | Informar CPF, telefone e CEP com mascara | Sistema salva dados normalizados |
| CLI-04 | Genero | Cadastrar cliente com genero | Campo fica disponivel nos relatorios |
| CLI-05 | Exclusao | Excluir cliente sem vinculo critico | Registro removido da lista |

#### F. Fornecedores

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| FOR-01 | Cadastro completo | Criar fornecedor com categoria e contatos | Registro salvo |
| FOR-02 | Categoria criada no fluxo | Criar categoria pela tela de fornecedor | Categoria nova disponivel no formulario |
| FOR-03 | Edicao | Atualizar CNPJ e contato | Dados persistem |

#### G. Produtos

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| PRO-01 | Cadastro basico | Criar produto com categoria, unidade, custo e preco | Produto salvo |
| PRO-02 | Codigo unico | Repetir codigo de produto | Sistema bloqueia duplicidade |
| PRO-03 | Margem automatica | Informar custo sem preco ou com preco | Preco/margem calculados coerentemente |
| PRO-04 | Estoque minimo automatico | Informar estoque e deixar minimo zerado | Minimo e calculado conforme parametro |
| PRO-05 | Produto inativo | Marcar produto inativo | Produto deixa de aparecer em vendas |
| PRO-06 | Conversao compra/venda | Produto com fator de conversao > 1 | Entradas respeitam a conversao |

#### H. Usuarios e permissoes

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| USR-01 | Novo usuario | Criar usuario operador | Usuario aparece na lista |
| USR-02 | Reset de senha | Executar reset de senha | Novo acesso funciona |
| USR-03 | Login sem espaco | Tentar salvar login com espacos | Sistema bloqueia |
| ACL-01 | Permissao de visualizacao | Remover acesso a um modulo | Usuario nao enxerga ou nao acessa o modulo |
| ACL-02 | Permissao de edicao | Permitir ver e bloquear editar | Tela abre, mas gravacao e bloqueada |
| ACL-03 | Bloqueio direto por URL | Abrir rota manualmente sem permissao | Acesso negado com mensagem adequada |

#### I. Compras e entrada de estoque

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| COM-01 | Entrada manual | Registrar compra manual de produto | Estoque aumenta e movimento e criado |
| COM-02 | Atualizacao de custo | Informar custo na entrada | Custo do produto e atualizado |
| COM-03 | Conversao de unidade | Entrada em produto com fator > 1 | Estoque sobe na unidade de venda correta |
| COM-04 | Pedido de compra | Criar pedido de compra | Pedido aparece na lista |
| COM-05 | Pedido com contas a pagar | Gerar pedido parcelado com financeiro | Lancamentos a pagar sao criados |
| COM-06 | Recebimento do pedido | Marcar pedido como recebido | Estoque atualiza e pedido muda status |
| COM-07 | Recebimento duplicado | Tentar receber pedido ja recebido | Sistema impede duplicacao |
| COM-08 | Importacao XML preview | Enviar XML valido para pre-visualizacao | Itens e dados do fornecedor aparecem |
| COM-09 | Confirmacao de XML | Confirmar importacao XML | Estoque, historico e financeiro atualizam |
| COM-10 | XML duplicado | Importar mesmo XML novamente | Sistema bloqueia |

#### J. Controle e ajuste de estoque

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| EST-01 | Posicao de estoque | Abrir controle de estoque | Quantidades batem com operacoes feitas |
| EST-02 | Ajuste de acrescimo | Registrar ajuste de entrada | Estoque aumenta e log e salvo |
| EST-03 | Ajuste de reducao | Registrar perda/quebra/vencimento | Estoque reduz e motivo aparece no historico |
| EST-04 | Kardex | Conferir historico de movimentos | Venda, entrada, ajuste e XML aparecem |
| EST-05 | Alertas | Validar abaixo do minimo, sem giro e divergencia | Produtos corretos aparecem em cada alerta |
| EST-06 | Valor de estoque | Validar total de estoque x custo | Valor total coerente |

#### K. Vendas

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| VEN-01 | Venda simples em dinheiro | Vender 1 produto com estoque suficiente | Venda salva e estoque reduz |
| VEN-02 | Venda com cliente | Selecionar cliente na venda | Venda fica vinculada ao cliente |
| VEN-03 | Estoque insuficiente | Tentar vender acima do estoque | Sistema bloqueia |
| VEN-04 | Venda sem item | Tentar confirmar sem itens | Sistema bloqueia |
| VEN-05 | Desconto e acrescimo | Aplicar desconto e acrescimo | Total final fica correto |
| VEN-06 | Credito com parcelas | Vender no credito com parcelamento | Forma de pagamento salva corretamente |
| VEN-07 | Multiplas formas | Habilitar multipagamento e dividir valores | Soma deve bater com total |
| VEN-08 | Pix | Selecionar Pix e confirmar recebimento | Venda so conclui com confirmacao |
| VEN-09 | Email pos-venda | Cliente com email e parametro ativo | Sistema tenta enviar mensagem ao cliente |
| VEN-10 | Alerta de estoque minimo | Vender ate atingir o minimo | Alerta e disparado conforme configuracao |

#### L. Fechamento de caixa

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| CAI-01 | Fechamento diario | Executar fechamento de caixa | Resumo do dia e exibido |
| CAI-02 | Total por meio de pagamento | Conferir total geral e total em dinheiro | Valores coerentes com vendas do dia |
| CAI-03 | Email de fechamento | Parametro de email configurado | Sistema envia ou reporta erro de envio |

#### M. Financeiro

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| FIN-01 | Categoria financeira | Criar categoria de receita e despesa | Categorias disponiveis nos lancamentos |
| FIN-02 | Lancamento manual a pagar | Cadastrar titulo a pagar | Entra como pendente |
| FIN-03 | Lancamento manual a receber | Cadastrar titulo a receber | Entra como pendente |
| FIN-04 | Validacao de categoria x tipo | Escolher categoria incompatível | Sistema bloqueia |
| FIN-05 | Pagamento parcial | Registrar valor menor que o titulo | Saldo remanescente continua aberto |
| FIN-06 | Pagamento total | Quitar titulo integralmente | Status muda para pago |
| FIN-07 | Estorno | Estornar um pago | Volta para pendente e grava historico |
| FIN-08 | Recorrencia | Criar lancamento recorrente | Titulo e marcado corretamente |
| FIN-09 | Venda gera financeiro | Concluir venda | Conta a receber correspondente e criada |
| FIN-10 | Filtro por origem | Filtrar por manual, venda, compra, XML | Lista respeita origem |
| FIN-11 | Grafico e resumo | Validar cards e fluxo de caixa | Totais coerentes |
| FIN-12 | DRE | Validar receitas, CMV, despesas e lucro | Numeros consistentes com operacao |

#### N. Relatorios

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| REL-01 | Filtro por periodo | Alterar datas | Relatorios refletem apenas o periodo |
| REL-02 | Clientes que mais compram | Abrir ranking e drill-down | Totais e compras detalhadas batem |
| REL-03 | Produtos mais lucrativos | Abrir relatorio correspondente | Lucro condiz com custo e venda |
| REL-04 | Estoque por produto | Filtrar categoria e ordenacao | Lista respeita filtro |
| REL-05 | Estoque minimo | Ordenar maior/menor urgencia | Ordenacao correta |
| REL-06 | Kardex | Conferir movimentos do periodo | Entradas, vendas e ajustes aparecem |
| REL-07 | Valorizacao de estoque | Validar estoque x custo | Total coerente |
| REL-08 | Pagamentos | Conferir vendas por forma de pagamento | Soma bate com vendas |
| REL-09 | Fluxo de caixa | Conferir entradas e saidas pagas | Saldo final coerente |
| REL-10 | Exportar Excel e PDF | Exportar um relatorio | Arquivos sao gerados sem erro |

#### O. Importacao Excel

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| IMP-01 | Download de template | Baixar modelo de importacao | Arquivo contem abas esperadas |
| IMP-02 | Arquivo valido | Enviar planilha com colunas corretas | Sistema confirma importacao |
| IMP-03 | Arquivo invalido | Enviar planilha com colunas faltantes | Sistema retorna arquivo com erros |
| IMP-04 | Modulo nao reconhecido | Alterar nome de aba | Sistema sinaliza modulo nao reconhecido |

#### P. Auditoria

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| AUD-01 | Registro de navegacao | Navegar por modulos e salvar registros | Logs sao gerados |
| AUD-02 | Filtro por usuario | Aplicar filtro por usuario | Resultado reduz corretamente |
| AUD-03 | Filtro por metodo/endpoint/path | Aplicar filtros | Lista respeita criterios |
| AUD-04 | Evento de permissao negada | Forcar acesso indevido | Evento fica registrado |
| AUD-05 | Retencao | Validar configuracao de retencao | Logs antigos sao tratados conforme parametro |

#### Q. Manual, idioma e tema

| ID | Cenario | Passo a passo | Validacao esperada |
| --- | --- | --- | --- |
| UI-01 | Manual | Abrir manual pelo menu do usuario | Conteudo carrega |
| UI-02 | Idioma | Trocar idioma e navegar | Textos mudam sem quebrar telas |
| UI-03 | Tema | Alternar claro/escuro | Layout permanece usavel |
| UI-04 | Responsividade basica | Abrir em janela menor | Menus e formularios seguem operaveis |

## 6. Cenarios de Teste Reais de Uso

### Cenario 1. Onboarding basico da conta

Passos:

1. Fazer login com conta principal.
2. Abrir Parametros e configurar dados da empresa.
3. Cadastrar unidade, categoria, fornecedor e cliente.
4. Cadastrar dois produtos.

Resultado esperado:

- estruturas basicas disponiveis para operacao
- listas atualizadas sem duplicidade indevida
- dados persistidos apos sair e entrar novamente

### Cenario 2. Abastecimento de estoque via compra manual

Passos:

1. Abrir Compras.
2. Registrar entrada manual de produto.
3. Validar custo atualizado.
4. Abrir Controle de Estoque.

Resultado esperado:

- estoque aumenta corretamente
- movimento entra no historico
- custo do produto e refletido no cadastro e relatorios

### Cenario 3. Pedido de compra com impacto financeiro

Passos:

1. Criar pedido de compra parcelado.
2. Verificar titulos no Financeiro.
3. Receber o pedido.
4. Conferir estoque e pedido marcado como recebido.

Resultado esperado:

- pedido salvo com parcelas esperadas
- contas a pagar geradas corretamente
- recebimento nao duplica pedidos nem parcelas

### Cenario 4. Venda completa com cliente e baixa de estoque

Passos:

1. Abrir Vendas.
2. Selecionar cliente.
3. Adicionar dois produtos.
4. Aplicar desconto ou acrescimo.
5. Confirmar venda.

Resultado esperado:

- venda salva
- estoque reduzido
- conta a receber automatica criada
- relatorios passam a refletir a nova venda

### Cenario 5. Venda com Pix

Passos:

1. Configurar Pix em Parametros.
2. Criar venda com forma Pix.
3. Tentar concluir sem confirmar Pix.
4. Confirmar Pix e concluir.

Resultado esperado:

- sistema bloqueia conclusao sem confirmacao
- apos confirmacao, venda e salva normalmente

### Cenario 6. Pagamento parcial de conta

Passos:

1. Criar conta a pagar ou a receber.
2. Registrar pagamento parcial.
3. Abrir a lista novamente.
4. Validar historico do pagamento.

Resultado esperado:

- saldo remanescente continua pendente
- parcela quitada fica registrada no historico
- total nao se perde nem duplica

### Cenario 7. Estorno financeiro

Passos:

1. Quitar um titulo.
2. Executar estorno.
3. Revalidar status e historico.

Resultado esperado:

- titulo volta para pendente
- historico guarda o estorno
- relatorios ajustam o impacto financeiro

### Cenario 8. Validacao de permissoes

Passos:

1. Criar usuario restrito.
2. Remover acesso a Financeiro e Parametros.
3. Fazer login com esse usuario.
4. Tentar acessar por menu e por URL direta.

Resultado esperado:

- usuario nao consegue editar ou acessar o que foi bloqueado
- tentativas ficam auditaveis

### Cenario 9. Importacao Excel

Passos:

1. Baixar template.
2. Preencher abas validas.
3. Importar arquivo.
4. Repetir com erro proposital em coluna.

Resultado esperado:

- arquivo valido conclui fluxo
- arquivo invalido retorna relatorio de erro utilizavel

### Cenario 10. Importacao de XML de NF-e

Passos:

1. Abrir Compras ou Financeiro.
2. Fazer preview de XML.
3. Confirmar importacao com criacao de fornecedor/produtos quando necessario.
4. Conferir estoque, historico e contas a pagar.

Resultado esperado:

- pre-visualizacao mostra os itens certos
- importacao atualiza todos os modulos vinculados
- XML duplicado e bloqueado

### Cenario 11. Fechamento gerencial

Passos:

1. Executar operacoes de compra, venda e financeiro.
2. Abrir relatorios de estoque, vendas, pagamentos e financeiro.
3. Executar fechamento de caixa.

Resultado esperado:

- totais entre modulos ficam coerentes
- resumo do caixa corresponde ao dia testado
- relatorios nao mostram lacunas obvias de integridade

## 7. Validacoes Criticas que Devem Ser Feitas em Cada Rodada

Estas validacoes devem ser repetidas ao fim de cada rodada de homologacao:

1. Toda venda reduziu estoque corretamente.
2. Toda venda gerou conta a receber quando aplicavel.
3. Nenhum pedido de compra recebido foi recebido duas vezes.
4. Nenhum titulo financeiro mudou de status sem historico correspondente.
5. Relatorios batem com os dados operacionais do periodo.
6. Usuario sem permissao nao consegue salvar alteracoes nem acessar por URL.
7. Datas, filtros e ordenacoes nao quebram os resultados.
8. Exportacoes PDF/Excel funcionam.
9. Logs de auditoria registram as principais acoes.
10. Navegacao, idioma e tema nao quebram a usabilidade.

## 8. Principais Erros que Normalmente Passam Despercebidos em ERPs Pequenos

1. Venda baixa estoque, mas relatorio ainda mostra valor antigo por causa de filtro ou data inconsistente.
2. Compra atualiza estoque, mas nao atualiza custo medio ou custo unitario usado nos relatorios.
3. Venda gera contas a receber duplicadas em fluxos repetidos ou refresh de pagina.
4. Exclusao de cadastro deixa registro orfao em vendas, financeiro ou relatorios.
5. Permissao bloqueia o menu, mas nao bloqueia a URL direta.
6. Pagamento parcial vira pagamento total por erro de arredondamento.
7. Relatorios somam vendas pelo total bruto enquanto o financeiro considera liquido.
8. Produto inativo continua aparecendo em vendas ou relatorios.
9. Fator de conversao funciona na compra manual, mas falha no pedido de compra ou XML.
10. XML cria fornecedor ou produto duplicado por comparacao imperfeita de codigo ou nome.
11. Exportacao PDF/Excel quebra quando ha acento, coluna vazia ou tabela sem linhas.
12. Datas com periodo invertido retornam dados incorretos em vez de erro claro.
13. Tema ou idioma altera layout e esconde botoes importantes.
14. Fechamento de caixa considera apenas dinheiro e o usuario interpreta como total geral.
15. Auditoria grava navegacao, mas nao registra claramente a acao negada ou a alteracao critica.

## 9. Modelo de Rodada de Teste Recomendado

Use a seguinte rotina operacional sempre que quiser homologar:

1. Rodar smoke test completo.
2. Executar os 11 cenarios reais de uso.
3. Rodar checklist por modulo apenas nos modulos alterados e nos modulos impactados.
4. Validar relatorios e integridade cruzada.
5. Registrar defeitos encontrados.
6. Corrigir.
7. Reexecutar o cenario que falhou.
8. Fazer regressao curta nas areas vizinhas.

## 10. Evolucao Futura para Testes Automatizados

Comece simples. A melhor evolucao para esse projeto e em 3 etapas.

### Etapa 1. Automatizar o essencial primeiro

Prioridade:

- login
- cadastro de cliente
- cadastro de produto
- compra/entrada de estoque
- venda com baixa de estoque
- geracao automatica de contas a receber
- abertura das principais telas sem erro

Ferramentas sugeridas:

- pytest para testes Python
- Flask test client para rotas e regras de negocio
- Playwright para testes de interface ponta a ponta

### Etapa 2. Automatizar regras de negocio criticas

Criar testes automatizados para:

- estoque insuficiente
- calculo de desconto/acrescimo
- pagamento parcial e estorno
- fator de conversao
- bloqueio por permissao
- filtros de periodo

### Etapa 3. Criar suite de regressao de homologacao

Separar uma suite curta para rodar sempre antes de producao:

- smoke de rotas principais
- venda ponta a ponta
- compra ponta a ponta
- financeiro basico
- exportacao de relatorio

### Estrutura simples recomendada para iniciar

- tests/test_auth.py
- tests/test_cadastros.py
- tests/test_vendas.py
- tests/test_estoque.py
- tests/test_financeiro.py
- tests/test_relatorios.py
- tests/e2e/test_fluxo_principal.spec.ts

### Regra pratica

Automatize primeiro o que:

- gera dinheiro
- mexe em estoque
- altera financeiro
- muda permissao
- costuma quebrar em deploy

## 11. Criterio de Liberacao para Producao

Liberar somente quando:

- nenhum erro critico estiver aberto
- fluxo ponta a ponta estiver aprovado
- vendas, estoque e financeiro estiverem coerentes
- permissoes principais estiverem validadas
- relatorios essenciais estiverem conferidos
- smoke test final estiver 100% aprovado

## 12. Como Usar Este Documento

1. Use a secao 5 como checklist oficial.
2. Use a secao 6 para testar os fluxos reais do negocio.
3. Use o arquivo MODELO_EXECUCAO_TESTES_MINI_ERP.md para registrar a rodada.
4. Ao corrigir um bug, repita o cenario correspondente e os modulos vizinhos impactados.