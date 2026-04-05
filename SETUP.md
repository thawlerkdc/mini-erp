# Setup e Execução - Mini ERP KDC Systems

## ✅ Melhorias Implementadas

### 1. **Persistência de Dados Garantida**
- Banco de dados SQLite com backup automático
- Modo WAL (Write-Ahead Logging) para maior segurança
- Verificação de integridade automática

### 2. **Backup Automático**
- Backups a cada 6 horas
- Backup diário à meia-noite
- Mantém os últimos 10 backups
- Pasta de backups: `/backups/`

### 3. **Recuperação de Falhas**
- Detecção automática de corrupção
- Recuperação via restauração de backup
- Recriação do banco se necessário

### 4. **Servidor WSGI (Gunicorn)**
- Melhor performance em produção
- Múltiplos workers
- Logging detalhado
- Reload de código em dev

---

## 🚀 Instalação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Verificar instalação
pip list | findstr gunicorn schedule
```

---

## ▶️ Como Executar

### **Opção 1: Desenvolvimento (Recomendado para começar)**
```bash
python app.py
```
- Acesso: `http://127.0.0.1:5000`
- Login: `admin` / `admin123`
- Auto-recarrega ao alterar código

### **Opção 2: Script Automatizado**
```bash
python run.py
```
- Inicializa banco de dados
- Verifica dependências
- Inicia servidor

### **Opção 3: Produção com Gunicorn (Linux/Mac)**
```bash
gunicorn -c gunicorn_config.py wsgi:app
```

### **Opção 4: Backup Automático em Background**
```bash
# Terminal 1: Iniciar servidor
python app.py

# Terminal 2: Iniciar scheduler de backups
python backup_scheduler.py
```

---

## 📊 Banco de Dados

### Localização
- Banco de autenticação: `DATA_DIR/auth.db`
- Bancos operacionais por conta: `DATA_DIR/tenants/tenant_<id>.db`
- Backups: `DATA_DIR/backups/` e `DATA_DIR/tenants/backups/`

### Dados Persistem?
✅ **SIM, desde que em produção o Render use disco persistente e a variável `DATA_DIR` aponte para ele.**

O problema anterior era:
- ❌ Banco SQLite salvo dentro do filesystem efêmero do deploy
- ❌ Sem separação entre clientes/contas principais

Agora tudo está resolvido! ✅

### Configuração no Render
1. Crie um Persistent Disk no serviço web.
2. Monte esse disco, por exemplo, em `/var/data`.
3. Configure a variável de ambiente `DATA_DIR=/var/data`.
4. Faça novo deploy.

### Modelo Multiempresa
1. Conta principal: dono da empresa/cliente.
2. Usuários dependentes: operadores da mesma conta principal.
3. Cada conta principal possui banco operacional próprio.
4. Os dados de uma conta não ficam visíveis para outra.

---

## 🛡️ Segurança

### Modo WAL (Write-Ahead Logging)
- Escreve alterações em arquivo de log antes de aplicar
- Recuperação automática em caso de interrupção
- Múltiplas conexões simultâneas

### Verificação de Integridade
```python
from models import check_database_integrity
status = check_database_integrity("kdc_systems.db")
# Retorna True se OK, False se corrompido
```

### Recuperação Manual
```python
from models import recover_database
recover_database("kdc_systems.db")
```

---

## 📝 Logs

### Aplicação
```
access.log   - Requisições HTTP
error.log    - Erros do servidor
```

### Backups
```
backup.log   - Histórico de backups
```

---

## ⚙️ Configuração

### Modificar Horários de Backup
Editar `backup_scheduler.py`:
```python
schedule.every(6).hours.do(scheduled_backup)  # Alterar intervalo
schedule.every().day.at("00:00").do(scheduled_backup)  # Alterar horário
```

### Modificar Workers do Gunicorn
Editar `gunicorn_config.py`:
```python
workers = 4  # Número de processos
```

---

## 🆘 Troubleshooting

### Porta 5000 em uso
```bash
# Windows - Matar processo
taskkill /PID <PID> /F

# Linux/Mac - Encontrar processo
lsof -i :5000
kill -9 <PID>
```

### Banco de dados corrompido
```bash
# Remover arquivos corrompidos
rm kdc_systems.db
rm kdc_systems.db-wal
rm kdc_systems.db-shm

# Reiniciar aplicação (recria automaticamente)
python app.py
```

### Dependências ausentes
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📊 Informações Importantes

### Estrutura de Backup
```
Mini ERP/
├── auth.db
├── backups/
├── tenants/
│   ├── tenant_1.db
│   ├── tenant_2.db
│   ├── backups/
│   └── ...
└── backup.log
```

### Ciclo de Vida
1. **Aplicativo inicia** → Verifica integridade
2. **Encontra problema?** → Restaura do backup
3. **Sem problema?** → Faz novo backup
4. **Cada 6h** → Backup automático
5. **Meia-noite** → Backup diário

---

✅ **Seu sistema agora está robusto e seus dados estão seguros!**
