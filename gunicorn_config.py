"""
Configuração de Gunicorn para produção.
"""

import os
import multiprocessing

# Porta dinâmica injetada pelo Render (default 10000 em produção, 5000 local).
_port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{_port}"

# Número de workers (processos de trabalho)
# Em serviços pequenos (ex.: Render free), muitos workers podem derrubar a instância.
# Prioriza WEB_CONCURRENCY quando definido e usa um valor conservador como fallback.
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))

# Tipo de worker
worker_class = "sync"

# Timeout
timeout = 120

# Máximo de requisições por worker antes de restart
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Modo daemon
daemon = False

# Reload de código em desenvolvimento
_flask_env = os.environ.get("FLASK_ENV", "production").lower()
reload = _flask_env == "development"

# Diretório de trabalho
chdir = os.path.dirname(os.path.abspath(__file__))

# Configurações de performance
keepalive = 5

# Pool de conexões
worker_connections = 1000
