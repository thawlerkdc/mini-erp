"""
Script para automação de backups do banco de dados.
Pode ser executado como serviço ou agendado via cron/task scheduler.
"""

import schedule
import time
import logging
from pathlib import Path
from models import backup_database, check_database_integrity

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = str(Path(__file__).resolve().parent / "kdc_systems.db")

def scheduled_backup():
    """Executa backup programado e verifica integridade."""
    try:
        logger.info("Iniciando backup agendado...")
        check_database_integrity(DB_PATH)
        backup_database(DB_PATH)
        logger.info("Backup agendado concluído com sucesso")
    except Exception as e:
        logger.error(f"Erro no backup agendado: {e}")

def schedule_backups():
    """Agenda backups para serem executados automaticamente."""
    # Backup a cada 6 horas
    schedule.every(6).hours.do(scheduled_backup)
    # Backup diário à meia-noite
    schedule.every().day.at("00:00").do(scheduled_backup)
    
    logger.info("Backups agendados com sucesso")
    logger.info("Diariamente às 00:00 e a cada 6 horas")
    
    # Loop para manter o scheduler rodando
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar a cada minuto

if __name__ == "__main__":
    try:
        schedule_backups()
    except KeyboardInterrupt:
        logger.info("Scheduler de backups interrompido")
