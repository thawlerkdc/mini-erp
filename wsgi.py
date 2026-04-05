"""
Arquivo WSGI para executar a aplicação com Gunicorn.
"""

from app import app

if __name__ == "__main__":
    app.run()
