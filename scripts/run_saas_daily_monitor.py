from datetime import datetime

from saas_management import run_saas_daily_monitor_job


if __name__ == "__main__":
    run_saas_daily_monitor_job()
    print(f"[OK] Monitor SaaS executado em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
