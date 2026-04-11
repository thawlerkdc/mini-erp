# 🚀 Instruções para Executar a Aplicação Localmente

## ✅ Problema Resolvido
- ✓ Configurado host e porta explícitos no Flask (127.0.0.1:5000)
- ✓ Dependências instaladas
- ✓ Arquivo `.env` criado para configurações de desenvolvimento
- ✓ Carregamento de variáveis de ambiente adicionado

## 📋 Opções de Execução

### Opção 1: Com PostgreSQL Local (Recomendado para produção)

1. **Instale PostgreSQL** em sua máquina
   - Download: https://www.postgresql.org/download/
   - Durante instalação, anote a senha do usuário `postgres`

2. **Crie um banco de dados**
   ```bash
   # No PowerShell/CMD:
   psql -U postgres -c "CREATE DATABASE mini_erp;"
   ```

3. **Configure o `.env`**
   Edite o arquivo `.env` na raiz do projeto:
   ```
   DATABASE_URL=postgresql://postgres:sua_senha@localhost:5432/mini_erp
   ```

4. **Execute a aplicação**
   ```bash
   python app.py
   ```
   A aplicação estará disponível em: **http://127.0.0.1:5000**

### Opção 2: Com SQLite (Desenvolvimento rápido)

Se você prefere testar rápido sem instalar PostgreSQL:

1. **Modifique `models.py`** (opcional - use SQLite como fallback)
   - A aplicação já está preparada para usar PostgreSQL
   - Para usar SQLite, consulte o padrão comentado em models.py

2. **Execute**
   ```bash
   # Ative o ambiente virtual (já deve estar)
   # Se não: .\venv\Scripts\Activate.ps1
   
   python app.py
   ```

## 🔧 Solução de Problemas

### "Conexão recusada"
- Verifique se PostgreSQL está rodando (se usar essa opção)
- Verifique a DATABASE_URL no `.env`
- Verifique a porta 5000 não está em uso: `Get-NetTcpConnection -LocalPort 5000`

### "Connection refused"
```bash
# Para liberar a porta:
Get-Process -Id (Get-NetTcpConnection -LocalPort 5000).OwningProcess | Stop-Process
```

### "ModuleNotFoundError"
```bash
# Reinstale dependências:
pip install -r requirements.txt
```

## ✨ Confirmação de Sucesso

Quando a aplicação iniciar corretamente, você verá:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

Então acesse no navegador: **http://127.0.0.1:5000**

---

## 📝 Atualização do `requirements.txt`

O `requirements.txt` foi atualizado para incluir:
- `python-dotenv` - para carregar variáveis de ambiente

Se quiser instalar tudo novamente:
```bash
pip install -r requirements.txt python-dotenv
```
