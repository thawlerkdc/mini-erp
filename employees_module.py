from __future__ import annotations

import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import pandas as pd
from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename

from logs_auditoria import log_audit_event
from models import get_db_connection

try:
    from PIL import Image
except ImportError:
    Image = None


employees_bp = Blueprint("employees", __name__)


EMPLOYEE_STATUS = {"ativo", "ferias", "afastado", "desligado"}
CONTRACT_TYPES = {"clt", "pj", "freelancer", "temporario"}
SEX_TYPES = {"masculino", "feminino", "outro", "nao_informado"}
MARITAL_TYPES = {"solteiro", "casado", "divorciado", "viuvo", "nao_informado"}


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def _clean_digits(raw: str, max_len: int) -> str:
    return re.sub(r"\D", "", str(raw or ""))[:max_len]


def _current_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def _account_id() -> int:
    return int(session.get("account_id") or 0)


def _parse_month_key(raw: str | None) -> str:
    text = (raw or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text
    return _current_month_key()


def _month_due_date(month_key: str) -> str:
    return f"{month_key}-05"


def _normalize_status(value: str) -> str:
    normalized = (value or "ativo").strip().lower()
    return normalized if normalized in EMPLOYEE_STATUS else "ativo"


def _normalize_contract(value: str) -> str:
    normalized = (value or "clt").strip().lower()
    return normalized if normalized in CONTRACT_TYPES else "clt"


def _normalize_sex(value: str) -> str:
    normalized = (value or "nao_informado").strip().lower()
    return normalized if normalized in SEX_TYPES else "nao_informado"


def _normalize_marital(value: str) -> str:
    normalized = (value or "nao_informado").strip().lower()
    return normalized if normalized in MARITAL_TYPES else "nao_informado"


def _employee_monthly_total(payload: dict) -> float:
    gross = (
        _safe_float(payload.get("salary_base"))
        + _safe_float(payload.get("commission"))
        + _safe_float(payload.get("bonus"))
        + _safe_float(payload.get("transportation_allowance"))
        + _safe_float(payload.get("meal_allowance"))
        + _safe_float(payload.get("health_plan"))
        + _safe_float(payload.get("other_benefits"))
    )
    total = gross - _safe_float(payload.get("fixed_discounts"))
    return round(max(total, 0.0), 2)


def _date_br(value: str | None) -> str:
    text = (value or "").strip()
    if len(text) >= 10 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10]):
        return f"{text[8:10]}/{text[5:7]}/{text[0:4]}"
    return text


def _month_label(month_key: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}", month_key):
        return f"{month_key[5:7]}/{month_key[0:4]}"
    return month_key


def _money_br(value) -> str:
    return f"R$ {float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _ensure_hr_defaults(conn, account_id: int):
    now = _now_text()
    defaults_positions = ["Assistente", "Analista", "Coordenador", "Gerente"]
    defaults_departments = ["Administrativo", "Comercial", "Financeiro", "Estoque", "Logística"]
    defaults_centers = [
        ("Administrativo", "ADM"),
        ("Comercial", "COM"),
        ("Financeiro", "FIN"),
        ("Estoque", "EST"),
        ("Logística", "LOG"),
    ]

    for name in defaults_positions:
        conn.execute(
            "INSERT INTO employee_positions (account_id, empresa_id, name, description, is_active, created_at, updated_at) "
            "VALUES (%s, %s, %s, '', 1, %s, %s) ON CONFLICT (account_id, name) DO NOTHING",
            (account_id, account_id, name, now, now),
        )

    for name in defaults_departments:
        conn.execute(
            "INSERT INTO employee_departments (account_id, empresa_id, name, description, is_active, created_at, updated_at) "
            "VALUES (%s, %s, %s, '', 1, %s, %s) ON CONFLICT (account_id, name) DO NOTHING",
            (account_id, account_id, name, now, now),
        )

    for name, code in defaults_centers:
        conn.execute(
            "INSERT INTO employee_cost_centers (account_id, empresa_id, name, code, description, is_active, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, '', 1, %s, %s) ON CONFLICT (account_id, name) DO NOTHING",
            (account_id, account_id, name, code, now, now),
        )


def _ensure_financial_category(conn, account_id: int, name: str, kind: str):
    row = conn.execute(
        "SELECT id FROM financial_categories WHERE account_id = %s AND name = %s AND kind IN (%s, 'both') ORDER BY id LIMIT 1",
        (account_id, name, kind),
    ).fetchone()
    if row:
        return int(row["id"])

    conn.execute(
        "INSERT INTO financial_categories (account_id, name, kind) VALUES (%s, %s, %s)",
        (account_id, name, kind),
    )
    row = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('financial_categories', 'id')) AS id").fetchone()
    return int(row["id"])


def _compress_employee_image(file_storage):
    raw = file_storage.read()
    file_storage.stream.seek(0)
    if not raw:
        return None

    if Image is None:
        return raw

    with Image.open(io.BytesIO(raw)) as img:
        img = img.convert("RGB")
        img.thumbnail((640, 640), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="WEBP", quality=82, method=6)
        return out.getvalue()


def _upload_employee_photo(file_storage, account_id: int, employee_id: int | None):
    filename = secure_filename(file_storage.filename or "foto")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Use PNG, JPG, JPEG ou WEBP para a foto do funcionário.")

    binary = _compress_employee_image(file_storage)
    if not binary:
        return ""

    supabase_url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    service_key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    bucket = (os.environ.get("SUPABASE_STORAGE_EMPLOYEE_BUCKET") or "employee-photos").strip()

    object_name = f"account-{account_id}/employee-{employee_id or int(datetime.now().timestamp())}.webp"

    if supabase_url and service_key:
        encoded_path = urllib.parse.quote(object_name, safe="/-_.")
        endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{encoded_path}"
        req = urllib.request.Request(
            endpoint,
            data=binary,
            method="POST",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "x-upsert": "true",
                "Content-Type": "image/webp",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20):
                return f"{supabase_url}/storage/v1/object/public/{bucket}/{object_name}"
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Falha ao enviar foto para Supabase Storage: {detail[:300]}")
        except Exception as exc:
            raise RuntimeError(f"Falha ao enviar foto para Supabase Storage: {exc}")

    local_dir = os.path.join(os.getcwd(), "static", "img", "employees")
    os.makedirs(local_dir, exist_ok=True)
    local_name = f"account_{account_id}_employee_{employee_id or int(datetime.now().timestamp())}.webp"
    local_path = os.path.join(local_dir, local_name)
    with open(local_path, "wb") as out:
        out.write(binary)
    return f"/static/img/employees/{local_name}"


def _load_dimensions(conn, account_id: int):
    positions = conn.execute(
        "SELECT id, name FROM employee_positions WHERE account_id = %s AND is_active = 1 ORDER BY name",
        (account_id,),
    ).fetchall()
    departments = conn.execute(
        "SELECT id, name FROM employee_departments WHERE account_id = %s AND is_active = 1 ORDER BY name",
        (account_id,),
    ).fetchall()
    centers = conn.execute(
        "SELECT id, name, code FROM employee_cost_centers WHERE account_id = %s AND is_active = 1 ORDER BY name",
        (account_id,),
    ).fetchall()
    return positions, departments, centers


def _sync_employee_expenses(conn, account_id: int, employee_row: dict, reference_month: str):
    if (employee_row.get("status") or "").strip().lower() == "desligado":
        return

    category_payable = _ensure_financial_category(conn, account_id, "Folha de pagamento", "payable")
    category_receivable = _ensure_financial_category(conn, account_id, "Recebimentos diversos", "receivable")
    due_date = _month_due_date(reference_month)
    now = _now_text()

    components = [
        ("salary", "Salário base", _safe_float(employee_row.get("salary_base")), "payable"),
        ("commission", "Comissão", _safe_float(employee_row.get("commission")), "payable"),
        ("bonus", "Bonificação", _safe_float(employee_row.get("bonus")), "payable"),
        ("transport", "Vale transporte", _safe_float(employee_row.get("transportation_allowance")), "payable"),
        ("meal", "Vale alimentação", _safe_float(employee_row.get("meal_allowance")), "payable"),
        ("health", "Plano de saúde", _safe_float(employee_row.get("health_plan")), "payable"),
        ("benefits", "Outros benefícios", _safe_float(employee_row.get("other_benefits")), "payable"),
        ("discounts", "Descontos fixos", _safe_float(employee_row.get("fixed_discounts")), "receivable"),
    ]

    employee_id = int(employee_row["id"])
    for expense_type, label, amount, entry_type in components:
        source_ref = f"employee:{employee_id}:{expense_type}:{reference_month}"
        expense_desc = f"Funcionário {employee_row.get('full_name')}: {label} ({reference_month})"

        existing_entry = conn.execute(
            "SELECT id FROM financial_entries WHERE account_id = %s AND source = 'employee_expense' AND source_ref = %s LIMIT 1",
            (account_id, source_ref),
        ).fetchone()

        if amount <= 0:
            if existing_entry:
                conn.execute(
                    "DELETE FROM financial_entries WHERE id = %s AND account_id = %s",
                    (existing_entry["id"], account_id),
                )
            conn.execute(
                "DELETE FROM employee_expenses WHERE account_id = %s AND employee_id = %s AND reference_month = %s AND expense_type = %s",
                (account_id, employee_id, reference_month, expense_type),
            )
            continue

        category_id = category_payable if entry_type == "payable" else category_receivable

        if existing_entry:
            financial_entry_id = int(existing_entry["id"])
            conn.execute(
                "UPDATE financial_entries SET entry_type = %s, description = %s, category_id = %s, amount = %s, due_date = %s, status = 'pendente', updated_at = NULL "
                "WHERE id = %s AND account_id = %s",
                (entry_type, expense_desc, category_id, amount, due_date, financial_entry_id, account_id),
            )
        else:
            conn.execute(
                "INSERT INTO financial_entries (account_id, entry_type, description, category_id, amount, due_date, status, is_recurring, recurrence_days, source, source_ref, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'pendente', 0, 30, 'employee_expense', %s, %s)",
                (account_id, entry_type, expense_desc, category_id, amount, due_date, source_ref, now),
            )
            financial_entry_id = int(
                conn.execute("SELECT CURRVAL(pg_get_serial_sequence('financial_entries', 'id')) AS id").fetchone()["id"]
            )

        existing_expense = conn.execute(
            "SELECT id FROM employee_expenses WHERE account_id = %s AND employee_id = %s AND reference_month = %s AND expense_type = %s LIMIT 1",
            (account_id, employee_id, reference_month, expense_type),
        ).fetchone()

        if existing_expense:
            conn.execute(
                "UPDATE employee_expenses SET amount = %s, description = %s, financial_entry_id = %s, status = 'pendente', updated_at = %s "
                "WHERE id = %s AND account_id = %s",
                (amount, expense_desc, financial_entry_id, now, existing_expense["id"], account_id),
            )
        else:
            conn.execute(
                "INSERT INTO employee_expenses (account_id, empresa_id, employee_id, cost_center_id, reference_month, expense_type, description, amount, financial_entry_id, status, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pendente', %s, %s)",
                (
                    account_id,
                    account_id,
                    employee_id,
                    employee_row.get("cost_center_id"),
                    reference_month,
                    expense_type,
                    expense_desc,
                    amount,
                    financial_entry_id,
                    now,
                    now,
                ),
            )


def _run_employee_month_generation(conn, account_id: int, reference_month: str):
    rows = conn.execute(
        "SELECT * FROM employees WHERE account_id = %s AND status IN ('ativo', 'ferias', 'afastado')",
        (account_id,),
    ).fetchall()
    for row in rows:
        _sync_employee_expenses(conn, account_id, dict(row), reference_month)


def _load_employee_reports(conn, account_id: int, month_key: str):
    active_rows = conn.execute(
        "SELECT full_name, status, contract_type, salary_base, monthly_total_cost FROM employees WHERE account_id = %s ORDER BY full_name",
        (account_id,),
    ).fetchall()
    by_department = conn.execute(
        "SELECT COALESCE(d.name, 'Sem departamento') AS name, COALESCE(SUM(e.monthly_total_cost), 0) AS total "
        "FROM employees e LEFT JOIN employee_departments d ON d.id = e.department_id "
        "WHERE e.account_id = %s GROUP BY d.name ORDER BY total DESC",
        (account_id,),
    ).fetchall()
    by_position = conn.execute(
        "SELECT COALESCE(p.name, 'Sem cargo') AS name, COALESCE(SUM(e.monthly_total_cost), 0) AS total "
        "FROM employees e LEFT JOIN employee_positions p ON p.id = e.position_id "
        "WHERE e.account_id = %s GROUP BY p.name ORDER BY total DESC",
        (account_id,),
    ).fetchall()
    by_center = conn.execute(
        "SELECT COALESCE(c.name, 'Sem centro') AS name, COALESCE(SUM(e.monthly_total_cost), 0) AS total "
        "FROM employees e LEFT JOIN employee_cost_centers c ON c.id = e.cost_center_id "
        "WHERE e.account_id = %s GROUP BY c.name ORDER BY total DESC",
        (account_id,),
    ).fetchall()
    month_expenses = conn.execute(
        "SELECT e.full_name, ex.expense_type, ex.amount, ex.reference_month "
        "FROM employee_expenses ex JOIN employees e ON e.id = ex.employee_id "
        "WHERE ex.account_id = %s AND ex.reference_month = %s ORDER BY e.full_name",
        (account_id, month_key),
    ).fetchall()
    return active_rows, by_department, by_position, by_center, month_expenses


def _export_employee_reports_excel(month_key: str, active_rows, by_department, by_position, by_center, month_expenses):
    output = io.BytesIO()
    month_text = _month_label(month_key)

    df_active = pd.DataFrame(
        [
            {
                "Nome": row["full_name"],
                "Status": str(row["status"] or "").capitalize(),
                "Contrato": str(row["contract_type"] or "").upper(),
                "Salario": float(row["salary_base"] or 0),
                "Custo mensal": float(row["monthly_total_cost"] or 0),
            }
            for row in active_rows
        ]
    )

    df_summary = pd.DataFrame(
        [
            {"Tipo": "Departamento", "Nome": row["name"], "Total": float(row["total"] or 0)}
            for row in by_department
        ]
        + [{"Tipo": "Cargo", "Nome": row["name"], "Total": float(row["total"] or 0)} for row in by_position]
        + [{"Tipo": "Centro de custo", "Nome": row["name"], "Total": float(row["total"] or 0)} for row in by_center]
    )

    df_expenses = pd.DataFrame(
        [
            {
                "Funcionario": row["full_name"],
                "Tipo": row["expense_type"],
                "Valor": float(row["amount"] or 0),
                "Mes": _month_label(row["reference_month"]),
            }
            for row in month_expenses
        ]
    )

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        pd.DataFrame(
            [
                {
                    "Relatorio": "Funcionarios",
                    "Mes de referencia": month_text,
                    "Gerado em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }
            ]
        ).to_excel(writer, index=False, sheet_name="Capa")
        df_active.to_excel(writer, index=False, sheet_name="Funcionarios")
        df_summary.to_excel(writer, index=False, sheet_name="Resumo")
        df_expenses.to_excel(writer, index=False, sheet_name="Despesas")

    output.seek(0)
    filename = f"funcionarios_relatorio_{month_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _pdf_write_table(c: canvas.Canvas, title: str, headers: list[str], rows: list[list[str]], y_start: int, width: int, height: int):
    x = 32
    y = y_start
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, title)
    y -= 18
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, " | ".join(headers))
    y -= 14
    c.setFont("Helvetica", 9)

    for row in rows:
        if y < 36:
            c.showPage()
            y = height - 36
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x, y, title)
            y -= 18
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x, y, " | ".join(headers))
            y -= 14
            c.setFont("Helvetica", 9)

        text = " | ".join(str(cell) for cell in row)
        if len(text) > 180:
            text = text[:177] + "..."
        c.drawString(x, y, text)
        y -= 12

    return y


def _export_employee_reports_pdf(month_key: str, active_rows, by_department, by_position, by_center, month_expenses):
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=landscape(A4))
    width, height = landscape(A4)

    c.setFont("Helvetica-Bold", 15)
    c.drawString(32, height - 30, "Relatorio de Funcionarios")
    c.setFont("Helvetica", 10)
    c.drawString(32, height - 46, f"Mes de referencia: {_month_label(month_key)}")
    c.drawString(32, height - 60, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    y = height - 84
    y = _pdf_write_table(
        c,
        "Funcionarios",
        ["Nome", "Status", "Contrato", "Salario", "Custo mensal"],
        [
            [
                row["full_name"],
                str(row["status"] or "").capitalize(),
                str(row["contract_type"] or "").upper(),
                _money_br(row["salary_base"]),
                _money_br(row["monthly_total_cost"]),
            ]
            for row in active_rows
        ],
        y,
        width,
        height,
    )

    y -= 8
    y = _pdf_write_table(
        c,
        "Resumo por departamento/cargo/centro de custo",
        ["Tipo", "Nome", "Total"],
        [["Departamento", row["name"], _money_br(row["total"])] for row in by_department]
        + [["Cargo", row["name"], _money_br(row["total"])] for row in by_position]
        + [["Centro de custo", row["name"], _money_br(row["total"])] for row in by_center],
        y,
        width,
        height,
    )

    y -= 8
    _pdf_write_table(
        c,
        f"Despesas do mes {_month_label(month_key)}",
        ["Funcionario", "Tipo", "Valor", "Mes"],
        [
            [row["full_name"], row["expense_type"], _money_br(row["amount"]), _month_label(row["reference_month"])]
            for row in month_expenses
        ],
        y,
        width,
        height,
    )

    c.showPage()
    c.save()
    output.seek(0)
    filename = f"funcionarios_relatorio_{month_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(output, as_attachment=True, download_name=filename, mimetype="application/pdf")


def _employee_from_form(form_data: dict):
    payload = {
        "full_name": (form_data.get("full_name") or "").strip(),
        "cpf": _clean_digits(form_data.get("cpf"), 14),
        "rg": (form_data.get("rg") or "").strip(),
        "birth_date": (form_data.get("birth_date") or "").strip(),
        "sex": _normalize_sex(form_data.get("sex")),
        "marital_status": _normalize_marital(form_data.get("marital_status")),
        "phone": _clean_digits(form_data.get("phone"), 15),
        "whatsapp": _clean_digits(form_data.get("whatsapp"), 15),
        "email": (form_data.get("email") or "").strip(),
        "address": (form_data.get("address") or "").strip(),
        "street": (form_data.get("street") or "").strip(),
        "number": (form_data.get("number") or "").strip(),
        "complement": (form_data.get("complement") or "").strip(),
        "neighborhood": (form_data.get("neighborhood") or "").strip(),
        "city": (form_data.get("city") or "").strip(),
        "state": (form_data.get("state") or "").strip(),
        "country": (form_data.get("country") or "").strip(),
        "postal_code": _clean_digits(form_data.get("postal_code"), 9),
        "position_id": form_data.get("position_id") or None,
        "department_id": form_data.get("department_id") or None,
        "cost_center_id": form_data.get("cost_center_id") or None,
        "admission_date": (form_data.get("admission_date") or "").strip(),
        "contract_type": _normalize_contract(form_data.get("contract_type")),
        "status": _normalize_status(form_data.get("status")),
        "salary_base": _safe_float(form_data.get("salary_base"), 0),
        "commission": _safe_float(form_data.get("commission"), 0),
        "bonus": _safe_float(form_data.get("bonus"), 0),
        "transportation_allowance": _safe_float(form_data.get("transportation_allowance"), 0),
        "meal_allowance": _safe_float(form_data.get("meal_allowance"), 0),
        "health_plan": _safe_float(form_data.get("health_plan"), 0),
        "other_benefits": _safe_float(form_data.get("other_benefits"), 0),
        "fixed_discounts": _safe_float(form_data.get("fixed_discounts"), 0),
        "vacation_start_date": (form_data.get("vacation_start_date") or "").strip(),
        "vacation_end_date": (form_data.get("vacation_end_date") or "").strip(),
        "contract_end_date": (form_data.get("contract_end_date") or "").strip(),
        "salary_review_date": (form_data.get("salary_review_date") or "").strip(),
        "notes": (form_data.get("notes") or "").strip(),
    }
    payload["monthly_total_cost"] = _employee_monthly_total(payload)
    return payload


def _save_employee(conn, account_id: int, payload: dict, employee_id: int | None = None):
    now = _now_text()

    if not payload.get("full_name"):
        raise ValueError("Nome completo é obrigatório.")

    if payload.get("cpf"):
        duplicate = conn.execute(
            "SELECT id FROM employees WHERE account_id = %s AND cpf = %s AND (%s IS NULL OR id <> %s) LIMIT 1",
            (account_id, payload["cpf"], employee_id, employee_id),
        ).fetchone()
        if duplicate:
            raise ValueError("Já existe funcionário cadastrado com este CPF.")

    if employee_id:
        previous = conn.execute(
            "SELECT salary_base, full_name FROM employees WHERE id = %s AND account_id = %s LIMIT 1",
            (employee_id, account_id),
        ).fetchone()
        if not previous:
            raise ValueError("Funcionário não encontrado para edição.")

        conn.execute(
            "UPDATE employees SET full_name = %s, cpf = %s, rg = %s, birth_date = %s, sex = %s, marital_status = %s, phone = %s, whatsapp = %s, email = %s, "
            "address = %s, street = %s, number = %s, complement = %s, neighborhood = %s, city = %s, state = %s, country = %s, postal_code = %s, "
            "position_id = %s, department_id = %s, cost_center_id = %s, admission_date = %s, contract_type = %s, status = %s, salary_base = %s, commission = %s, bonus = %s, "
            "transportation_allowance = %s, meal_allowance = %s, health_plan = %s, other_benefits = %s, fixed_discounts = %s, monthly_total_cost = %s, "
            "vacation_start_date = %s, vacation_end_date = %s, contract_end_date = %s, salary_review_date = %s, notes = %s, updated_at = %s WHERE id = %s AND account_id = %s",
            (
                payload["full_name"], payload["cpf"], payload["rg"], payload["birth_date"], payload["sex"], payload["marital_status"], payload["phone"],
                payload["whatsapp"], payload["email"], payload["address"], payload["street"], payload["number"], payload["complement"], payload["neighborhood"],
                payload["city"], payload["state"], payload["country"], payload["postal_code"], payload["position_id"], payload["department_id"], payload["cost_center_id"],
                payload["admission_date"], payload["contract_type"], payload["status"], payload["salary_base"], payload["commission"], payload["bonus"],
                payload["transportation_allowance"], payload["meal_allowance"], payload["health_plan"], payload["other_benefits"], payload["fixed_discounts"],
                payload["monthly_total_cost"], payload["vacation_start_date"], payload["vacation_end_date"], payload["contract_end_date"], payload["salary_review_date"],
                payload["notes"], now, employee_id, account_id,
            ),
        )

        previous_salary = _safe_float(previous["salary_base"], 0)
        current_salary = _safe_float(payload["salary_base"], 0)
        if previous_salary != current_salary:
            conn.execute(
                "INSERT INTO employee_salary_history (account_id, empresa_id, employee_id, previous_salary, new_salary, reason, changed_by_user_id, changed_by_user_name, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    account_id,
                    account_id,
                    employee_id,
                    previous_salary,
                    current_salary,
                    (request.form.get("salary_change_reason") or "Ajuste cadastral").strip(),
                    session.get("user_id"),
                    session.get("user_name") or session.get("user"),
                    now,
                    now,
                ),
            )
        return employee_id

    conn.execute(
        "INSERT INTO employees (account_id, empresa_id, full_name, cpf, rg, birth_date, sex, marital_status, phone, whatsapp, email, address, street, number, complement, neighborhood, city, state, country, postal_code, "
        "position_id, department_id, cost_center_id, admission_date, contract_type, status, salary_base, commission, bonus, transportation_allowance, meal_allowance, health_plan, other_benefits, fixed_discounts, monthly_total_cost, "
        "vacation_start_date, vacation_end_date, contract_end_date, salary_review_date, notes, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            account_id,
            account_id,
            payload["full_name"],
            payload["cpf"],
            payload["rg"],
            payload["birth_date"],
            payload["sex"],
            payload["marital_status"],
            payload["phone"],
            payload["whatsapp"],
            payload["email"],
            payload["address"],
            payload["street"],
            payload["number"],
            payload["complement"],
            payload["neighborhood"],
            payload["city"],
            payload["state"],
            payload["country"],
            payload["postal_code"],
            payload["position_id"],
            payload["department_id"],
            payload["cost_center_id"],
            payload["admission_date"],
            payload["contract_type"],
            payload["status"],
            payload["salary_base"],
            payload["commission"],
            payload["bonus"],
            payload["transportation_allowance"],
            payload["meal_allowance"],
            payload["health_plan"],
            payload["other_benefits"],
            payload["fixed_discounts"],
            payload["monthly_total_cost"],
            payload["vacation_start_date"],
            payload["vacation_end_date"],
            payload["contract_end_date"],
            payload["salary_review_date"],
            payload["notes"],
            now,
            now,
        ),
    )
    row = conn.execute("SELECT CURRVAL(pg_get_serial_sequence('employees', 'id')) AS id").fetchone()
    return int(row["id"])


@employees_bp.before_request
def _require_login():
    if request.endpoint == "static":
        return None
    if not session.get("user"):
        return redirect(url_for("login"))
    return None


@employees_bp.route("/funcionarios/dashboard", endpoint="funcionarios_dashboard")
def funcionarios_dashboard():
    account_id = _account_id()
    conn = get_db_connection()
    month_key = _parse_month_key(request.args.get("month"))
    try:
        _ensure_hr_defaults(conn, account_id)
        _run_employee_month_generation(conn, account_id, month_key)
        conn.commit()

        totals = conn.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(CASE WHEN status = 'ativo' THEN 1 ELSE 0 END), 0) AS active_count, "
            "COALESCE(SUM(monthly_total_cost), 0) AS total_cost, "
            "COALESCE(AVG(NULLIF(salary_base, 0)), 0) AS avg_salary "
            "FROM employees WHERE account_id = %s",
            (account_id,),
        ).fetchone()

        by_position = conn.execute(
            "SELECT COALESCE(p.name, 'Sem cargo') AS name, COALESCE(SUM(e.monthly_total_cost), 0) AS total "
            "FROM employees e LEFT JOIN employee_positions p ON p.id = e.position_id "
            "WHERE e.account_id = %s GROUP BY p.name ORDER BY total DESC",
            (account_id,),
        ).fetchall()
        by_department = conn.execute(
            "SELECT COALESCE(d.name, 'Sem departamento') AS name, COALESCE(SUM(e.monthly_total_cost), 0) AS total "
            "FROM employees e LEFT JOIN employee_departments d ON d.id = e.department_id "
            "WHERE e.account_id = %s GROUP BY d.name ORDER BY total DESC",
            (account_id,),
        ).fetchall()
        by_cost_center = conn.execute(
            "SELECT COALESCE(c.name, 'Sem centro') AS name, COALESCE(SUM(e.monthly_total_cost), 0) AS total "
            "FROM employees e LEFT JOIN employee_cost_centers c ON c.id = e.cost_center_id "
            "WHERE e.account_id = %s GROUP BY c.name ORDER BY total DESC",
            (account_id,),
        ).fetchall()

        expensive_employee = conn.execute(
            "SELECT full_name, monthly_total_cost FROM employees WHERE account_id = %s ORDER BY monthly_total_cost DESC LIMIT 1",
            (account_id,),
        ).fetchone()

        monthly_evolution = conn.execute(
            "SELECT reference_month, COALESCE(SUM(amount), 0) AS total "
            "FROM employee_expenses WHERE account_id = %s GROUP BY reference_month ORDER BY reference_month DESC LIMIT 12",
            (account_id,),
        ).fetchall()

        alerts_birthdays = conn.execute(
            "SELECT full_name, birth_date FROM employees "
            "WHERE account_id = %s AND status <> 'desligado' AND birth_date IS NOT NULL AND birth_date <> '' "
            "AND TO_CHAR(TO_DATE(SUBSTRING(birth_date, 1, 10), 'YYYY-MM-DD'), 'MM-DD') BETWEEN TO_CHAR(CURRENT_DATE, 'MM-DD') "
            "AND TO_CHAR(CURRENT_DATE + INTERVAL '30 day', 'MM-DD') ORDER BY birth_date LIMIT 5",
            (account_id,),
        ).fetchall()

        alerts_vacation = conn.execute(
            "SELECT full_name, vacation_start_date FROM employees "
            "WHERE account_id = %s AND status <> 'desligado' AND vacation_start_date IS NOT NULL AND vacation_start_date <> '' "
            "AND vacation_start_date BETWEEN %s AND %s ORDER BY vacation_start_date LIMIT 5",
            (account_id, datetime.now().strftime("%Y-%m-%d"), (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")),
        ).fetchall()

        alerts_contract = conn.execute(
            "SELECT full_name, contract_end_date FROM employees "
            "WHERE account_id = %s AND status <> 'desligado' AND contract_end_date IS NOT NULL AND contract_end_date <> '' "
            "AND contract_end_date BETWEEN %s AND %s ORDER BY contract_end_date LIMIT 5",
            (account_id, datetime.now().strftime("%Y-%m-%d"), (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")),
        ).fetchall()
    finally:
        conn.close()

    return render_template(
        "funcionarios_dashboard.html",
        title="Funcionários - Dashboard",
        month_key=month_key,
        totals=totals,
        expensive_employee=expensive_employee,
        by_position=by_position,
        by_department=by_department,
        by_cost_center=by_cost_center,
        monthly_evolution=list(reversed(monthly_evolution)),
        alerts_birthdays=alerts_birthdays,
        alerts_vacation=alerts_vacation,
        alerts_contract=alerts_contract,
    )


@employees_bp.route("/funcionarios", endpoint="funcionarios")
def funcionarios():
    account_id = _account_id()
    conn = get_db_connection()
    page = max(int(request.args.get("page", 1)), 1)
    per_page = max(min(int(request.args.get("per_page", 20)), 100), 10)
    offset = (page - 1) * per_page

    filters = {
        "q": (request.args.get("q") or "").strip().lower(),
        "position_id": (request.args.get("position_id") or "").strip(),
        "department_id": (request.args.get("department_id") or "").strip(),
        "cost_center_id": (request.args.get("cost_center_id") or "").strip(),
        "status": (request.args.get("status") or "").strip().lower(),
        "salary_min": _safe_float(request.args.get("salary_min"), 0),
        "salary_max": _safe_float(request.args.get("salary_max"), 0),
    }

    where = ["e.account_id = %s"]
    params = [account_id]

    if filters["q"]:
        where.append("(LOWER(e.full_name) LIKE %s OR LOWER(COALESCE(e.email, '')) LIKE %s)")
        params.extend([f"%{filters['q']}%", f"%{filters['q']}%"])
    if filters["position_id"]:
        where.append("CAST(e.position_id AS TEXT) = %s")
        params.append(filters["position_id"])
    if filters["department_id"]:
        where.append("CAST(e.department_id AS TEXT) = %s")
        params.append(filters["department_id"])
    if filters["cost_center_id"]:
        where.append("CAST(e.cost_center_id AS TEXT) = %s")
        params.append(filters["cost_center_id"])
    if filters["status"] in EMPLOYEE_STATUS:
        where.append("e.status = %s")
        params.append(filters["status"])
    if filters["salary_min"] > 0:
        where.append("e.salary_base >= %s")
        params.append(filters["salary_min"])
    if filters["salary_max"] > 0:
        where.append("e.salary_base <= %s")
        params.append(filters["salary_max"])

    where_sql = " AND ".join(where)

    try:
        positions, departments, centers = _load_dimensions(conn, account_id)

        total_row = conn.execute(
            f"SELECT COUNT(*) AS total FROM employees e WHERE {where_sql}",
            tuple(params),
        ).fetchone()

        rows = conn.execute(
            f"SELECT e.*, COALESCE(p.name, '-') AS position_name, COALESCE(d.name, '-') AS department_name, "
            f"COALESCE(c.name, '-') AS cost_center_name "
            f"FROM employees e "
            f"LEFT JOIN employee_positions p ON p.id = e.position_id "
            f"LEFT JOIN employee_departments d ON d.id = e.department_id "
            f"LEFT JOIN employee_cost_centers c ON c.id = e.cost_center_id "
            f"WHERE {where_sql} ORDER BY e.full_name LIMIT %s OFFSET %s",
            tuple(params + [per_page, offset]),
        ).fetchall()
    finally:
        conn.close()

    total = int(total_row["total"] or 0)
    total_pages = max((total + per_page - 1) // per_page, 1)

    return render_template(
        "funcionarios_list.html",
        title="Funcionários",
        rows=rows,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        filters=filters,
        positions=positions,
        departments=departments,
        centers=centers,
    )


@employees_bp.route("/funcionarios/novo", methods=["GET", "POST"], endpoint="novo_funcionario")
def novo_funcionario():
    account_id = _account_id()
    conn = get_db_connection()
    try:
        _ensure_hr_defaults(conn, account_id)
        positions, departments, centers = _load_dimensions(conn, account_id)

        if request.method == "POST":
            payload = _employee_from_form(request.form)
            employee_id = _save_employee(conn, account_id, payload)

            photo = request.files.get("employee_photo")
            if photo and photo.filename:
                photo_url = _upload_employee_photo(photo, account_id, employee_id)
                conn.execute(
                    "UPDATE employees SET photo_url = %s, updated_at = %s WHERE id = %s AND account_id = %s",
                    (photo_url, _now_text(), employee_id, account_id),
                )

            employee_row = conn.execute(
                "SELECT * FROM employees WHERE id = %s AND account_id = %s LIMIT 1",
                (employee_id, account_id),
            ).fetchone()
            _sync_employee_expenses(conn, account_id, dict(employee_row), _current_month_key())
            conn.commit()

            log_audit_event(
                "employee_created",
                {"employee_id": employee_id, "employee_name": payload.get("full_name")},
                account_id=account_id,
            )
            flash("Funcionário cadastrado com sucesso.", "success")
            return redirect(url_for("employees.funcionarios"))
    except Exception as exc:
        conn.rollback()
        flash(f"Falha ao salvar funcionário: {exc}", "error")
    finally:
        conn.close()

    return render_template(
        "funcionario_form.html",
        title="Novo Funcionário",
        edit_data={},
        positions=positions,
        departments=departments,
        centers=centers,
        is_edit=False,
    )


@employees_bp.route("/funcionarios/<int:employee_id>/editar", methods=["GET", "POST"], endpoint="editar_funcionario")
def editar_funcionario(employee_id):
    account_id = _account_id()
    conn = get_db_connection()
    try:
        employee = conn.execute(
            "SELECT * FROM employees WHERE id = %s AND account_id = %s LIMIT 1",
            (employee_id, account_id),
        ).fetchone()
        if not employee:
            flash("Funcionário não encontrado.", "error")
            return redirect(url_for("employees.funcionarios"))

        positions, departments, centers = _load_dimensions(conn, account_id)

        if request.method == "POST":
            payload = _employee_from_form(request.form)
            _save_employee(conn, account_id, payload, employee_id=employee_id)

            photo = request.files.get("employee_photo")
            if photo and photo.filename:
                photo_url = _upload_employee_photo(photo, account_id, employee_id)
                conn.execute(
                    "UPDATE employees SET photo_url = %s, updated_at = %s WHERE id = %s AND account_id = %s",
                    (photo_url, _now_text(), employee_id, account_id),
                )

            employee_row = conn.execute(
                "SELECT * FROM employees WHERE id = %s AND account_id = %s LIMIT 1",
                (employee_id, account_id),
            ).fetchone()
            _sync_employee_expenses(conn, account_id, dict(employee_row), _current_month_key())

            conn.commit()
            log_audit_event(
                "employee_updated",
                {"employee_id": employee_id, "employee_name": payload.get("full_name")},
                account_id=account_id,
            )
            flash("Funcionário atualizado com sucesso.", "success")
            return redirect(url_for("employees.funcionarios"))
    except Exception as exc:
        conn.rollback()
        flash(f"Falha ao atualizar funcionário: {exc}", "error")
    finally:
        conn.close()

    return render_template(
        "funcionario_form.html",
        title="Editar Funcionário",
        edit_data=dict(employee or {}),
        positions=positions,
        departments=departments,
        centers=centers,
        is_edit=True,
    )


def _dimension_page(table_name: str, title: str, endpoint_name: str):
    account_id = _account_id()
    conn = get_db_connection()
    try:
        if request.method == "POST":
            action = (request.form.get("action") or "").strip().lower()
            now = _now_text()
            if action == "create":
                name = (request.form.get("name") or "").strip()
                description = (request.form.get("description") or "").strip()
                code = (request.form.get("code") or "").strip()
                if not name:
                    flash("Informe o nome para cadastrar.", "error")
                else:
                    if table_name == "employee_cost_centers":
                        conn.execute(
                            "INSERT INTO employee_cost_centers (account_id, empresa_id, name, code, description, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, 1, %s, %s)",
                            (account_id, account_id, name, code, description, now, now),
                        )
                    else:
                        conn.execute(
                            f"INSERT INTO {table_name} (account_id, empresa_id, name, description, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, 1, %s, %s)",
                            (account_id, account_id, name, description, now, now),
                        )
                    conn.commit()
                    flash("Registro adicionado com sucesso.", "success")

            if action == "toggle":
                row_id = request.form.get("row_id")
                row = conn.execute(
                    f"SELECT is_active FROM {table_name} WHERE id = %s AND account_id = %s LIMIT 1",
                    (row_id, account_id),
                ).fetchone()
                if row:
                    next_state = 0 if int(row["is_active"] or 0) == 1 else 1
                    conn.execute(
                        f"UPDATE {table_name} SET is_active = %s, updated_at = %s WHERE id = %s AND account_id = %s",
                        (next_state, now, row_id, account_id),
                    )
                    conn.commit()
                    flash("Status atualizado.", "success")

        rows = conn.execute(
            f"SELECT * FROM {table_name} WHERE account_id = %s ORDER BY name",
            (account_id,),
        ).fetchall()
    except Exception as exc:
        conn.rollback()
        flash(f"Erro ao carregar dados: {exc}", "error")
        rows = []
    finally:
        conn.close()

    return render_template(
        "funcionarios_dimension.html",
        title=title,
        rows=rows,
        endpoint_name=endpoint_name,
        table_name=table_name,
    )


@employees_bp.route("/funcionarios/cargos", methods=["GET", "POST"], endpoint="funcionarios_cargos")
def funcionarios_cargos():
    return _dimension_page("employee_positions", "Cargos", "employees.funcionarios_cargos")


@employees_bp.route("/funcionarios/departamentos", methods=["GET", "POST"], endpoint="funcionarios_departamentos")
def funcionarios_departamentos():
    return _dimension_page("employee_departments", "Departamentos", "employees.funcionarios_departamentos")


@employees_bp.route("/funcionarios/centros-custo", methods=["GET", "POST"], endpoint="funcionarios_centros_custo")
def funcionarios_centros_custo():
    return _dimension_page("employee_cost_centers", "Centro de Custos", "employees.funcionarios_centros_custo")


@employees_bp.route("/funcionarios/despesas", methods=["GET", "POST"], endpoint="funcionarios_despesas")
def funcionarios_despesas():
    account_id = _account_id()
    month_key = _parse_month_key(request.values.get("month"))
    conn = get_db_connection()
    try:
        if request.method == "POST":
            _run_employee_month_generation(conn, account_id, month_key)
            conn.commit()
            flash("Despesas de funcionários sincronizadas com o financeiro.", "success")
            return redirect(url_for("employees.funcionarios_despesas", month=month_key))

        rows = conn.execute(
            "SELECT ex.*, e.full_name, COALESCE(cc.name, '-') AS cost_center_name, fe.status AS financial_status "
            "FROM employee_expenses ex "
            "JOIN employees e ON e.id = ex.employee_id "
            "LEFT JOIN employee_cost_centers cc ON cc.id = ex.cost_center_id "
            "LEFT JOIN financial_entries fe ON fe.id = ex.financial_entry_id "
            "WHERE ex.account_id = %s AND ex.reference_month = %s "
            "ORDER BY e.full_name, ex.expense_type",
            (account_id, month_key),
        ).fetchall()

        summary = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS qty FROM employee_expenses WHERE account_id = %s AND reference_month = %s",
            (account_id, month_key),
        ).fetchone()
    finally:
        conn.close()

    return render_template(
        "funcionarios_despesas.html",
        title="Despesas de Funcionários",
        rows=rows,
        month_key=month_key,
        summary=summary,
    )


@employees_bp.route("/funcionarios/relatorios", endpoint="funcionarios_relatorios")
def funcionarios_relatorios():
    account_id = _account_id()
    month_key = _parse_month_key(request.args.get("month"))
    conn = get_db_connection()
    try:
        active_rows, by_department, by_position, by_center, month_expenses = _load_employee_reports(
            conn,
            account_id,
            month_key,
        )
    finally:
        conn.close()

    return render_template(
        "funcionarios_relatorios.html",
        title="Relatórios de Funcionários",
        month_key=month_key,
        active_rows=active_rows,
        by_department=by_department,
        by_position=by_position,
        by_center=by_center,
        month_expenses=month_expenses,
    )


@employees_bp.route("/funcionarios/relatorios/export", endpoint="funcionarios_relatorios_export")
def funcionarios_relatorios_export():
    account_id = _account_id()
    month_key = _parse_month_key(request.args.get("month"))
    export_format = (request.args.get("format") or "excel").strip().lower()

    conn = get_db_connection()
    try:
        active_rows, by_department, by_position, by_center, month_expenses = _load_employee_reports(
            conn,
            account_id,
            month_key,
        )
    finally:
        conn.close()

    if export_format == "pdf":
        log_audit_event("employees_report_export_pdf", {"month": month_key}, account_id=account_id)
        return _export_employee_reports_pdf(month_key, active_rows, by_department, by_position, by_center, month_expenses)

    if export_format != "excel":
        flash("Formato de exportação inválido. Use excel ou pdf.", "error")
        return redirect(url_for("employees.funcionarios_relatorios", month=month_key))

    log_audit_event("employees_report_export_excel", {"month": month_key}, account_id=account_id)
    return _export_employee_reports_excel(month_key, active_rows, by_department, by_position, by_center, month_expenses)
