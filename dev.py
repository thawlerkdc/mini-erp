#!/usr/bin/env python
"""
Script simples para rodar Flask localmente para testes
Sem Gunicorn, sem dependências pesadas
Este arquivo NÃO afeta o Render, que usa run.py
"""

import os
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Garantir que estamos usando SQLite em desenvolvimento local
if not os.getenv('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'sqlite:///kdc_systems.db'
    print("✓ Usando SQLite local: kdc_systems.db")

# Importar a aplicação Flask
try:
    from app import app
    print("✓ Aplicação carregada com sucesso")
except ImportError as e:
    print(f"✗ Erro ao carregar aplicação: {e}")
    sys.exit(1)

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 Mini ERP - Servidor de Desenvolvimento Local")
    print("=" * 60)
    print("📡 Iniciando em http://localhost:5000")
    print("🛑 Pressione Ctrl+C para parar")
    print("=" * 60 + "\n")
    
    # Rodar com reload automático em desenvolvimento
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=True
    )
