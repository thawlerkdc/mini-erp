# ✅ Configuração Local + Render - Mini ERP

## 🌍 Estado Atual

✅ **Aplicação rodando em**: http://127.0.0.1:5000  
✅ **Host**: 127.0.0.1  
✅ **Porta**: 5000  
✅ **Modo**: Desenvolvimento (localhost)  

## 🎯 Cenários de Uso

### Cenário 1: Produção no Render (Atual - Funcionando ✅)

Sem fazer nada extra:
- O Render injeta automaticamente `DATABASE_URL` durante deploy
- Seu arquivo `.env` local fica com `DATABASE_URL=` vazio
- A aplicação detecta que está em produção via Render e usa o PostgreSQL

**Status**: ✅ Já está funcionando!

---

### Cenário 2: Testes Locais com PostgreSQL Local (Recomendado)

Se você quer testar a aplicação **completa** localmente:

#### Passo 1: Instale PostgreSQL
- Download: https://www.postgresql.org/download/windows/
- Durante instalação, anote a senha do usuário `postgres` (padrão: postgres)

#### Passo 2: Crie o banco de dados

```bash
# No PowerShell/CMD:
psql -U postgres -c "CREATE DATABASE mini_erp;"
```

#### Passo 3: Configure o `.env`

Edite o arquivo `.env` na raiz do projeto e descomente:

```env
DATABASE_URL=postgresql://postgres:senha_do_postgres@localhost:5432/mini_erp
```

#### Passo 4: Ride a aplicação

```bash
python app.py
```

Agora acesse: **http://127.0.0.1:5000**

**Credenciais padrão**:
- Usuário: `admin`
- Senha: `admin123`

---

### Cenário 3: Testes Rápidos (Sem PostgreSQL)

Se você quer apenas verificar a interface sem banco de dados:

```bash
python app.py
```

A aplicação:
- ✅ Carrega a página de login
- ❌ Falha ao tentar fazer login (esperado - sem BD)
- ✅ Útil para testar CSS, layout, tradução

---

## 🔧 Solução de Problemas

### "Connection refused em localhost:5000"

1. Verifique se porta 5000 está livre:
```bash
Get-NetTcpConnection -LocalPort 5000
```

2. Se estiver ocupada, libere:
```bash
Get-Process -Id (Get-NetTcpConnection -LocalPort 5000).OwningProcess | Stop-Process
```

### "DATABASE_URL não configurado" (ao fazer login local)

**Solução**: Configure PostgreSQL local conforme Cenário 2 acima.

Ou para testes sem banco:
- Use modo offline (interface apenas)
- Configure PostgreSQL local

### "Erro de conexão ao Render após deploy"

Verifique no painel do Render:
1. Environment variables
2. DATABASE_URL está configurado?
3. PostgreSQL está ativo?

---

## 📋 Resumo Rápido

| Ambiente | Database | Arquivo .env | Status |
|----------|----------|--------------|--------|
| **Render (Produção)** | PostgreSQL Cloud | `DATABASE_URL=` (vazio) | ✅ Automático |
| **Local com PostgreSQL** | PostgreSQL Local | `DATABASE_URL=postgresql://...` | ✅ Configure |
| **Local Demo** | Nenhum | `DATABASE_URL=` (vazio) | ⚠️ Interface only |

---

## 🚀 Próximos Passos

1. **Para testar localmente** → Siga Cenário 2 acima
2. **Para manter Render funcionando** → Não mude nada, deixe `.env` vazio
3. **Para ambos simultaneamente** → Use PostgreSQL local para dev, Render para prod

---

## ℹ️ Arquivos Relevantes

- [.env](.env) - Configu ração de ambiente
- [app.py](app.py#L775-L805) - Status do banco de dados (linhas 775-805)
- [models.py](models.py#L253-L288) - Função get_db_connection
- [requirements.txt](requirements.txt) - Dependências

---

**Dúvidas?** A aplicação agora informa claramente qual ambiente está usando no console:
- `🌍 Ambiente: development (Local)`
- `🌍 Ambiente: production (Render)`
