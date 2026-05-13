from datetime import datetime

from employees_module import run_employee_monthly_automation_job


if __name__ == "__main__":
    result = run_employee_monthly_automation_job()
    print(
        "[OK] Automacao mensal de funcionarios executada em "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"mes={result['month']} | contas={result['processed_accounts']}"
    )
