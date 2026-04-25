import time
from datetime import datetime

from models import get_db_connection
from saas_management import run_saas_daily_monitor_job


def _get_monitor_hour_setting(default_value="07:30"):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT setting_value FROM saas_automation_settings WHERE setting_key = 'daily_monitor_hour' LIMIT 1"
        ).fetchone()
        value = (row["setting_value"] if row else default_value) or default_value
        value = value.strip()
        if len(value) == 5 and value[2] == ":":
            return value
        return default_value
    finally:
        conn.close()


def main():
    print("[SaaS Monitor] Servico iniciado.")
    last_run_date = ""

    while True:
        now = datetime.now()
        run_hour = _get_monitor_hour_setting()
        current_hhmm = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")

        if current_hhmm == run_hour and current_date != last_run_date:
            try:
                run_saas_daily_monitor_job(reference_date=current_date)
                print(f"[SaaS Monitor] Execucao concluida em {now.strftime('%Y-%m-%d %H:%M:%S')}")
                last_run_date = current_date
            except Exception as exc:
                print(f"[SaaS Monitor] Erro na execucao: {exc}")

        time.sleep(20)


if __name__ == "__main__":
    main()
