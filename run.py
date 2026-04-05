"""
Script de inicialização da aplicação com todas as funcionalidades.
Inicia: Flask/Gunicorn + Scheduler de Backups
"""

import subprocess
import sys
import os
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    project_dir = Path(__file__).resolve().parent
    os.chdir(project_dir)
    
    logger.info("=" * 60)
    logger.info("Iniciando Mini ERP - KDC Systems")
    logger.info("=" * 60)
    
    # Verificar se as dependências estão instaladas
    logger.info("Verificando dependências...")
    try:
        import gunicorn
        import schedule
        logger.info("✓ Dependências instaladas")
    except ImportError:
        logger.error("✗ Dependências não instaladas!")
        logger.info("Execute: pip install -r requirements.txt")
        sys.exit(1)
    
    # Inicializar banco de dados
    logger.info("Inicializando banco de dados...")
    try:
        from models import init_db, seed_admin
        db_path = str(project_dir / "kdc_systems.db")
        init_db(db_path)
        seed_admin(db_path)
        logger.info("✓ Banco de dados pronto")
    except Exception as e:
        logger.error(f"✗ Erro ao inicializar banco de dados: {e}")
        sys.exit(1)
    
    # Iniciar servidor Gunicorn
    logger.info("Iniciando servidor Gunicorn...")
    logger.info("Acesse: http://127.0.0.1:5000")
    
    try:
        # Para Windows, usar flask em desenvolvimento como alternativa
        if sys.platform == "win32":
            logger.info("Sistema em desenvolvimento (Windows)")
            logger.info("Use: python app.py")
            os.system("python app.py")
        else:
            # Para Linux/Mac
            subprocess.run([
                "gunicorn",
                "-c", "gunicorn_config.py",
                "wsgi:app"
            ])
    except KeyboardInterrupt:
        logger.info("Aplicação interrompida pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro ao iniciar servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
