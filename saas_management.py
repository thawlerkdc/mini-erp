from datetime import datetime, timedelta
import io
import json
import os
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for

from models import create_account_with_owner, get_db_connection
from logs_auditoria import log_audit_event

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except ImportError:
    colors = None
    A4 = None
    getSampleStyleSheet = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None


saas_bp = Blueprint("saas", __name__)


ACCOUNT_STATUS = ["ativa", "suspensa", "bloqueada", "inativa"]
BILLING_STATUS = ["pendente", "pago", "atrasado"]
PLAN_CYCLES = ["mensal", "anual"]


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today_str():
    return datetime.now().strftime("%Y-%m-%d")


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        text = str(value).strip().replace(",", ".")
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        if value is None:
            return default
        text = str(value).strip()
        if not text:
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _parse_datetime(value):
    text = (value or "").strip()
    if not text or text == "-":
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def _format_datetime_br(value):
    dt = _parse_datetime(value)
    if not dt:
        return "-"
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def _format_date_br(value):
    dt = _parse_datetime(value)
    if not dt:
        return "-"
    return dt.strftime("%d/%m/%Y")


def _format_reference_period(value):
    text = (value or "").strip()
    if not text or text == "-":
        return "-"
    if len(text) == 7 and text[4] == "-":
        return f"{text[5:7]}/{text[:4]}"
    dt = _parse_datetime(text)
    if dt:
        return dt.strftime("%d/%m/%Y")
    return text


def _add_cycle_date(start_date, cycle):
    base = _parse_datetime(start_date) or datetime.now()
    if cycle == "anual":
        try:
            return base.replace(year=base.year + 1).strftime("%Y-%m-%d")
        except ValueError:
            # 29/02 fallback
            return (base + timedelta(days=365)).strftime("%Y-%m-%d")

    # mensal
    month = base.month + 1
    year = base.year
    if month > 12:
        month = 1
        year += 1
    day = base.day
    while day > 28:
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            day -= 1
    return datetime(year, month, day).strftime("%Y-%m-%d")


def _parse_json_or_text(raw_text):
    text = (raw_text or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            loaded = json.loads(text)
            if isinstance(loaded, list):
                return [str(item).strip() for item in loaded if str(item).strip()]
        except Exception:
            pass
    lines = []
    for line in text.splitlines():
        clean = line.strip(" -\t")
        if clean:
            lines.append(clean)
    return lines


def _serialize_json(items):
    return json.dumps(items or [], ensure_ascii=False)


def _current_user_id():
    return session.get("user_id")


def _current_account_id():
    return session.get("account_id")


def _is_owner_system_admin():
    return bool(session.get("user") and session.get("role") == "owner" and session.get("is_admin"))


def _dependent_permission_row(conn):
    return conn.execute(
        """
        SELECT up.can_view, up.can_edit, up.can_delete
        FROM user_permissions up
        WHERE up.account_id = %s
          AND up.user_id = %s
          AND up.module = 'gestao_saas'
        LIMIT 1
        """,
        (_current_account_id(), _current_user_id()),
    ).fetchone()


def _can_access_saas(require_edit=False, require_delete=False):
    if not session.get("user"):
        return False

    if _is_owner_system_admin():
        return True

    # Dono que nao e admin global nao pode operar o modulo central SaaS.
    if session.get("role") == "owner":
        return False

    conn = get_db_connection()
    try:
        owner_admin = conn.execute(
            """
            SELECT 1
            FROM users
            WHERE account_id = %s
              AND role = 'owner'
              AND is_admin = 1
            LIMIT 1
            """,
            (_current_account_id(),),
        ).fetchone()
        if not owner_admin:
            return False

        perm = _dependent_permission_row(conn)
        if not perm:
            return False
        if require_delete:
            return bool(perm["can_delete"])
        if require_edit:
            return bool(perm["can_edit"])
        return bool(perm["can_view"])
    finally:
        conn.close()


def _log_panel_access(action, payload=None):
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO saas_panel_access_logs (user_id, account_id, username, action, method, path, payload, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                _current_user_id(),
                _current_account_id(),
                session.get("user") or "",
                action,
                request.method,
                request.path,
                json.dumps(payload or {}, ensure_ascii=False),
                _now_str(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    log_audit_event(
        "saas_panel_action",
        {
            "action": action,
            "payload": payload or {},
            "panel": "gestao_saas",
        },
        account_id=_current_account_id(),
    )


def _ensure_saas_defaults(conn):
    existing_count = conn.execute("SELECT COUNT(*) AS total FROM saas_plans").fetchone()["total"]
    if existing_count == 0:
        now = _now_str()
        plans = [
            ("Básico", 129.90, 1299.00, 299.00, ["Vendas", "Estoque", "Financeiro básico"], ["2 usuários", "1 filial"]),
            ("Completo", 249.90, 2499.00, 199.00, ["Todos os módulos operacionais", "Relatórios avançados"], ["8 usuários", "3 filiais"]),
            ("Premium", 499.90, 4999.00, 0.00, ["Tudo do Completo", "Automações", "Insights inteligentes"], ["Usuários ilimitados", "Filiais ilimitadas"]),
        ]
        for name, monthly, yearly, setup_fee, features, limits in plans:
            conn.execute(
                """
                INSERT INTO saas_plans (name, price_monthly, price_yearly, setup_fee, features_json, limits_json, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s)
                """,
                (name, monthly, yearly, setup_fee, _serialize_json(features), _serialize_json(limits), now, now),
            )

    defaults = {
        "auto_block_enabled": "1",
        "default_suspension_days": "10",
        "send_billing_email": "1",
        "send_billing_whatsapp": "0",
        "daily_monitor_hour": "07:30",
        "apply_new_prices_default": "novos",
        "whatsapp_api_url": os.environ.get("SAAS_WHATSAPP_API_URL", ""),
        "whatsapp_api_token": os.environ.get("SAAS_WHATSAPP_API_TOKEN", ""),
        "whatsapp_timeout_seconds": os.environ.get("SAAS_WHATSAPP_TIMEOUT", "12"),
        "whatsapp_template_overdue": "Sua assinatura no Mini ERP está em atraso. Regularize para evitar bloqueio.",
        "whatsapp_template_blocked": "Sua conta foi bloqueada por inadimplência. Assim que houver pagamento, ela será reativada automaticamente.",
        "whatsapp_template_reactivated": "Pagamento confirmado. Sua conta no Mini ERP foi reativada com sucesso.",
        "whatsapp_template_low_usage": "Notamos baixa utilização da conta. Podemos ajudar com uma consultoria rápida para aumentar resultados.",
    }
    for key, value in defaults.items():
        conn.execute(
            """
            INSERT INTO saas_automation_settings (setting_key, setting_value, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (setting_key) DO UPDATE
            SET setting_value = EXCLUDED.setting_value,
                updated_at = EXCLUDED.updated_at
            """,
            (key, value, _now_str()),
        )


def _automation_settings_map(conn):
    return {
        row["setting_key"]: (row["setting_value"] or "")
        for row in conn.execute("SELECT setting_key, setting_value FROM saas_automation_settings").fetchall()
    }


def _post_json(url, payload, token=None, timeout_seconds=12):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib_request.Request(url=url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib_request.urlopen(req, timeout=max(3, int(timeout_seconds))) as response:
        return response.getcode(), response.read().decode("utf-8", errors="ignore")


def _send_whatsapp_notification(conn, account_row, event_type, message):
    settings = _automation_settings_map(conn)
    if str(settings.get("send_billing_whatsapp", "0")) != "1":
        return False, "whatsapp_disabled"

    api_url = (settings.get("whatsapp_api_url") or "").strip()
    api_token = (settings.get("whatsapp_api_token") or "").strip()
    timeout_seconds = _safe_int(settings.get("whatsapp_timeout_seconds"), 12)
    to_phone = (account_row.get("whatsapp") or "").strip()
    if not api_url or not to_phone:
        return False, "missing_api_url_or_phone"

    payload = {
        "to": to_phone,
        "message": message,
        "event": event_type,
        "account_id": account_row.get("id"),
        "account_name": account_row.get("name"),
    }
    try:
        status_code, response_text = _post_json(api_url, payload, token=api_token, timeout_seconds=timeout_seconds)
        success = 200 <= int(status_code) < 300
        return success, f"http_{status_code}:{response_text[:180]}"
    except urllib_error.HTTPError as exc:
        return False, f"http_error_{exc.code}"
    except Exception as exc:
        return False, f"error_{exc}"


def _collect_daily_usage_snapshot(conn, usage_date):
    day_start = f"{usage_date} 00:00:00"
    day_end = f"{usage_date} 23:59:59"
    rows = conn.execute(
        """
        SELECT account_id, user_id, endpoint, path, created_at
        FROM logs
        WHERE created_at BETWEEN %s AND %s
        ORDER BY account_id, user_id, created_at
        """,
        (day_start, day_end),
    ).fetchall()

    by_account = {}
    for row in rows:
        endpoint = (row["endpoint"] or "-").strip() or "-"
        path = (row["path"] or "-").strip() or "-"
        # Ignore static asset loads to keep usage analytics focused on feature interactions.
        if endpoint.lower() == "static" or path.lower().startswith("/static/"):
            continue

        account_id = row["account_id"]
        account_data = by_account.setdefault(
            account_id,
            {
                "users": set(),
                "events": 0,
                "path_count": {},
                "endpoint_count": {},
                "user_times": {},
            },
        )
        account_data["events"] += 1
        account_data["users"].add(row["user_id"])

        account_data["path_count"][path] = account_data["path_count"].get(path, 0) + 1
        account_data["endpoint_count"][endpoint] = account_data["endpoint_count"].get(endpoint, 0) + 1

        user_key = row["user_id"] or 0
        user_track = account_data["user_times"].setdefault(user_key, {"min": row["created_at"], "max": row["created_at"]})
        if row["created_at"] < user_track["min"]:
            user_track["min"] = row["created_at"]
        if row["created_at"] > user_track["max"]:
            user_track["max"] = row["created_at"]

    now = _now_str()
    for account_id, data in by_account.items():
        total_minutes = 0.0
        tracked_users = 0
        for timer in data["user_times"].values():
            try:
                dt_min = datetime.strptime(timer["min"], "%Y-%m-%d %H:%M:%S")
                dt_max = datetime.strptime(timer["max"], "%Y-%m-%d %H:%M:%S")
                diff_minutes = max(1.0, min(480.0, (dt_max - dt_min).total_seconds() / 60.0))
                total_minutes += diff_minutes
                tracked_users += 1
            except Exception:
                continue

        avg_session_minutes = round((total_minutes / tracked_users), 2) if tracked_users else 0.0
        top_screen = max(data["path_count"], key=data["path_count"].get) if data["path_count"] else "-"
        top_feature = max(data["endpoint_count"], key=data["endpoint_count"].get) if data["endpoint_count"] else "-"

        conn.execute(
            """
            INSERT INTO saas_usage_daily (
                account_id, usage_date, active_users, total_sessions, avg_session_minutes,
                top_screen, top_feature, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (account_id, usage_date) DO UPDATE SET
                active_users = EXCLUDED.active_users,
                total_sessions = EXCLUDED.total_sessions,
                avg_session_minutes = EXCLUDED.avg_session_minutes,
                top_screen = EXCLUDED.top_screen,
                top_feature = EXCLUDED.top_feature,
                created_at = EXCLUDED.created_at
            """,
            (
                account_id,
                usage_date,
                len(data["users"]),
                data["events"],
                avg_session_minutes,
                top_screen,
                top_feature,
                now,
            ),
        )


def _run_daily_monitor(conn, reference_date=None):
    today = reference_date or _today_str()
    yesterday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    _collect_daily_usage_snapshot(conn, yesterday)

    conn.execute(
        """
        UPDATE saas_billing_events
        SET status = 'atrasado', updated_at = %s
        WHERE status = 'pendente' AND due_date < %s
        """,
        (_now_str(), today),
    )

    blocking_rules = _automation_settings_map(conn)
    auto_block_enabled = str(blocking_rules.get("auto_block_enabled", "1")) == "1"
    default_suspension_days = _safe_int(blocking_rules.get("default_suspension_days"), 10)

    account_map = {
        row["id"]: dict(row)
        for row in conn.execute("SELECT id, name, whatsapp, primary_email FROM accounts").fetchall()
    }

    if auto_block_enabled:
        overdue_rows = conn.execute(
            """
            SELECT s.account_id, COALESCE(s.suspension_days, %s) AS suspension_days, MIN(b.due_date) AS oldest_due
            FROM saas_subscriptions s
            JOIN saas_billing_events b ON b.account_id = s.account_id
            WHERE b.status = 'atrasado' AND s.status IN ('ativa', 'suspensa')
            GROUP BY s.account_id, s.suspension_days
            """,
            (default_suspension_days,),
        ).fetchall()

        for row in overdue_rows:
            oldest_due = row["oldest_due"]
            if not oldest_due:
                continue
            try:
                overdue_days = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(oldest_due, "%Y-%m-%d")).days
            except Exception:
                continue
            if overdue_days in {3, 7}:
                template = (blocking_rules.get("whatsapp_template_overdue") or "").strip()
                account_row = account_map.get(row["account_id"], {})
                message = f"{template} (Conta: {account_row.get('name', '-')}, atraso: {overdue_days} dias)"
                sent, note = _send_whatsapp_notification(conn, account_row, "overdue_warning", message)
                conn.execute(
                    """
                    INSERT INTO saas_panel_access_logs (user_id, account_id, username, action, method, path, payload, created_at)
                    VALUES (NULL, %s, %s, 'daily_whatsapp_overdue', 'AUTO', '/admin/saas-management', %s, %s)
                    """,
                    (row["account_id"], "saas_monitor", json.dumps({"sent": sent, "note": note}, ensure_ascii=False), _now_str()),
                )
            if overdue_days >= _safe_int(row["suspension_days"], default_suspension_days):
                conn.execute("UPDATE accounts SET status = 'bloqueada', updated_at = %s WHERE id = %s", (_now_str(), row["account_id"]))
                conn.execute("UPDATE saas_subscriptions SET status = 'bloqueada', updated_at = %s WHERE account_id = %s", (_now_str(), row["account_id"]))
                template = (blocking_rules.get("whatsapp_template_blocked") or "").strip()
                account_row = account_map.get(row["account_id"], {})
                message = f"{template} (Conta: {account_row.get('name', '-')})"
                sent, note = _send_whatsapp_notification(conn, account_row, "account_blocked", message)
                conn.execute(
                    """
                    INSERT INTO saas_panel_access_logs (user_id, account_id, username, action, method, path, payload, created_at)
                    VALUES (NULL, %s, %s, 'daily_whatsapp_blocked', 'AUTO', '/admin/saas-management', %s, %s)
                    """,
                    (row["account_id"], "saas_monitor", json.dumps({"sent": sent, "note": note}, ensure_ascii=False), _now_str()),
                )

    paid_ready = conn.execute(
        """
        SELECT s.account_id
        FROM saas_subscriptions s
        WHERE s.status = 'bloqueada'
          AND NOT EXISTS (
            SELECT 1 FROM saas_billing_events b
            WHERE b.account_id = s.account_id
              AND b.status IN ('pendente', 'atrasado')
          )
        """
    ).fetchall()
    for row in paid_ready:
        conn.execute("UPDATE accounts SET status = 'ativa', updated_at = %s WHERE id = %s", (_now_str(), row["account_id"]))
        conn.execute("UPDATE saas_subscriptions SET status = 'ativa', updated_at = %s WHERE account_id = %s", (_now_str(), row["account_id"]))
        template = (blocking_rules.get("whatsapp_template_reactivated") or "").strip()
        account_row = account_map.get(row["account_id"], {})
        message = f"{template} (Conta: {account_row.get('name', '-')})"
        sent, note = _send_whatsapp_notification(conn, account_row, "account_reactivated", message)
        conn.execute(
            """
            INSERT INTO saas_panel_access_logs (user_id, account_id, username, action, method, path, payload, created_at)
            VALUES (NULL, %s, %s, 'daily_whatsapp_reactivated', 'AUTO', '/admin/saas-management', %s, %s)
            """,
            (row["account_id"], "saas_monitor", json.dumps({"sent": sent, "note": note}, ensure_ascii=False), _now_str()),
        )

    low_usage_accounts = conn.execute(
        """
        SELECT u.account_id, a.name, u.active_users, u.avg_session_minutes
        FROM saas_usage_daily u
        JOIN accounts a ON a.id = u.account_id
        WHERE u.usage_date = %s
          AND (u.active_users <= 1 OR u.avg_session_minutes < 8)
        """,
        (yesterday,),
    ).fetchall()

    for row in low_usage_accounts:
        title = "Risco de churn por baixa utilização"
        message = (
            f"A conta {row['name']} apresentou baixa atividade em {yesterday}. "
            f"Usuários ativos: {row['active_users']}, média de sessão: {row['avg_session_minutes']} min."
        )
        already_exists = conn.execute(
            """
            SELECT id
            FROM saas_insights
            WHERE account_id = %s
              AND insight_type = 'alerta'
              AND title = %s
              AND generated_on = %s
            LIMIT 1
            """,
            (row["account_id"], title, today),
        ).fetchone()
        if already_exists:
            continue

        conn.execute(
            """
            INSERT INTO saas_insights (account_id, insight_type, severity, title, message, generated_on, resolved)
            VALUES (%s, 'alerta', 'alta', %s, %s, %s, 0)
            """,
            (row["account_id"], title, message, today),
        )
        template = (blocking_rules.get("whatsapp_template_low_usage") or "").strip()
        account_row = account_map.get(row["account_id"], {})
        auto_message = f"{template} (Conta: {account_row.get('name', '-')})"
        sent, note = _send_whatsapp_notification(conn, account_row, "low_usage_alert", auto_message)
        conn.execute(
            """
            INSERT INTO saas_panel_access_logs (user_id, account_id, username, action, method, path, payload, created_at)
            VALUES (NULL, %s, %s, 'daily_whatsapp_low_usage', 'AUTO', '/admin/saas-management', %s, %s)
            """,
            (row["account_id"], "saas_monitor", json.dumps({"sent": sent, "note": note}, ensure_ascii=False), _now_str()),
        )


def run_saas_daily_monitor_job(reference_date=None):
    conn = get_db_connection()
    try:
        _ensure_saas_defaults(conn)
        _run_daily_monitor(conn, reference_date=reference_date or _today_str())
        conn.commit()
    finally:
        conn.close()


def _upsert_subscription(conn, form_data):
    account_id = _safe_int(form_data.get("account_id"), 0)
    plan_id = _safe_int(form_data.get("plan_id"), 0)
    if account_id <= 0 or plan_id <= 0:
        return False, "Conta e plano são obrigatórios para assinatura."

    cycle = (form_data.get("billing_cycle") or "mensal").strip().lower()
    if cycle not in PLAN_CYCLES:
        cycle = "mensal"

    plan_row = conn.execute(
        "SELECT id, name, price_monthly, price_yearly, setup_fee FROM saas_plans WHERE id = %s LIMIT 1",
        (plan_id,),
    ).fetchone()
    if not plan_row:
        return False, "Plano selecionado não foi encontrado."

    default_amount = _safe_float(plan_row["price_yearly"] if cycle == "anual" else plan_row["price_monthly"], 0.0)
    amount = _safe_float(form_data.get("amount"), default_amount)
    if amount <= 0:
        amount = default_amount

    setup_fee_amount = _safe_float(plan_row["setup_fee"], 0.0)
    starts_at = (form_data.get("starts_at") or _today_str()).strip()
    next_due_date = (form_data.get("next_due_date") or "").strip()
    if not next_due_date:
        next_due_date = _add_cycle_date(starts_at, cycle)
    status = (form_data.get("subscription_status") or "ativa").strip().lower()
    if status not in ACCOUNT_STATUS:
        status = "ativa"

    suspension_days = _safe_int(form_data.get("suspension_days"), 10)
    auto_block_enabled = 1 if form_data.get("auto_block_enabled") else 0
    apply_new_prices_to_existing = 1 if form_data.get("apply_new_prices_to_existing") else 0

    now = _now_str()
    conn.execute(
        """
        INSERT INTO saas_subscriptions (
            account_id, plan_id, billing_cycle, amount, setup_fee_amount, starts_at, next_due_date,
            status, suspension_days, auto_block_enabled, apply_new_prices_to_existing, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (account_id) DO UPDATE SET
            plan_id = EXCLUDED.plan_id,
            billing_cycle = EXCLUDED.billing_cycle,
            amount = EXCLUDED.amount,
            setup_fee_amount = EXCLUDED.setup_fee_amount,
            starts_at = EXCLUDED.starts_at,
            next_due_date = EXCLUDED.next_due_date,
            status = EXCLUDED.status,
            suspension_days = EXCLUDED.suspension_days,
            auto_block_enabled = EXCLUDED.auto_block_enabled,
            apply_new_prices_to_existing = EXCLUDED.apply_new_prices_to_existing,
            updated_at = EXCLUDED.updated_at
        """,
        (
            account_id,
            plan_id,
            cycle,
            amount,
            setup_fee_amount,
            starts_at,
            next_due_date,
            status,
            suspension_days,
            auto_block_enabled,
            apply_new_prices_to_existing,
            now,
        ),
    )

    subscription = conn.execute(
        "SELECT id FROM saas_subscriptions WHERE account_id = %s LIMIT 1",
        (account_id,),
    ).fetchone()
    subscription_id = subscription["id"] if subscription else None

    setup_already = conn.execute(
        "SELECT id FROM saas_billing_events WHERE account_id = %s AND charge_type = 'adesao' LIMIT 1",
        (account_id,),
    ).fetchone()
    if setup_fee_amount > 0 and not setup_already:
        conn.execute(
            """
            INSERT INTO saas_billing_events (
                account_id, subscription_id, charge_type, reference_period,
                due_date, amount, status, notes, created_at, updated_at
            )
            VALUES (%s, %s, 'adesao', %s, %s, %s, 'pendente', %s, %s, %s)
            """,
            (
                account_id,
                subscription_id,
                starts_at[:7],
                starts_at,
                setup_fee_amount,
                f"Taxa de adesão do plano {plan_row['name']}",
                now,
                now,
            ),
        )

    charge_type = "anuidade" if cycle == "anual" else "mensalidade"
    reference_period = next_due_date[:7]
    recurring_exists = conn.execute(
        """
        SELECT id
        FROM saas_billing_events
        WHERE account_id = %s
          AND charge_type = %s
          AND reference_period = %s
        LIMIT 1
        """,
        (account_id, charge_type, reference_period),
    ).fetchone()
    if not recurring_exists and amount > 0:
        conn.execute(
            """
            INSERT INTO saas_billing_events (
                account_id, subscription_id, charge_type, reference_period,
                due_date, amount, status, notes, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'pendente', %s, %s, %s)
            """,
            (
                account_id,
                subscription_id,
                charge_type,
                reference_period,
                next_due_date,
                amount,
                f"Cobrança automática de {charge_type} ({plan_row['name']})",
                now,
                now,
            ),
        )

    return True, "Assinatura atualizada com sucesso."


def _build_report_rows(conn, report_type, start_date, end_date):
    if report_type == "financeiro":
        return conn.execute(
            """
            SELECT a.name AS empresa, b.charge_type AS tipo_cobranca, b.reference_period AS referencia,
                   b.due_date AS vencimento, b.amount AS valor, b.status AS status, COALESCE(b.paid_at, '-') AS pago_em
            FROM saas_billing_events b
            JOIN accounts a ON a.id = b.account_id
            WHERE b.due_date BETWEEN %s AND %s
            ORDER BY b.due_date DESC, a.name
            """,
            (start_date, end_date),
        ).fetchall()

    if report_type == "uso_cliente":
        return conn.execute(
            """
            SELECT a.name AS empresa, u.usage_date AS data, u.active_users AS usuarios_ativos,
                   u.total_sessions AS sessoes, u.avg_session_minutes AS media_minutos,
                   u.top_screen AS tela_principal, u.top_feature AS funcionalidade_principal
            FROM saas_usage_daily u
            JOIN accounts a ON a.id = u.account_id
            WHERE u.usage_date BETWEEN %s AND %s
            ORDER BY u.usage_date DESC, a.name
            """,
            (start_date, end_date),
        ).fetchall()

    if report_type == "uso_funcionalidade":
        return conn.execute(
            """
            SELECT u.top_feature AS funcionalidade, COUNT(*) AS dias_no_topo,
                   SUM(u.total_sessions) AS total_sessoes
            FROM saas_usage_daily u
            WHERE u.usage_date BETWEEN %s AND %s
            GROUP BY u.top_feature
            ORDER BY total_sessoes DESC
            """,
            (start_date, end_date),
        ).fetchall()

    return conn.execute(
        """
        SELECT a.name AS empresa,
               COUNT(DISTINCT l.user_id) AS usuarios_ativos,
               COUNT(*) AS eventos,
               MIN(l.created_at) AS primeiro_evento,
               MAX(l.created_at) AS ultimo_evento
        FROM logs l
        JOIN accounts a ON a.id = l.account_id
        WHERE SUBSTRING(l.created_at, 1, 10) BETWEEN %s AND %s
        GROUP BY a.name
        ORDER BY eventos DESC
        """,
        (start_date, end_date),
    ).fetchall()


@saas_bp.before_request
def _guard_saas_module():
    if not _can_access_saas():
        flash("Acesso restrito ao módulo de Gestão SaaS.", "error")
        return redirect(url_for("dashboard"))

    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not _can_access_saas(require_edit=True):
        flash("Seu usuário possui acesso somente leitura no módulo de Gestão SaaS.", "error")
        return redirect(url_for("saas.gestao_saas"))

    if request.method == "POST":
        action = (request.form.get("action") or "acao_nao_informada").strip().lower()
        if action in {"delete_company", "delete_plan", "delete_charge"} and not _can_access_saas(require_delete=True):
            flash("Você não possui permissão de exclusão no módulo de Gestão SaaS.", "error")
            return redirect(url_for("saas.gestao_saas"))


@saas_bp.route("/admin/saas-management", methods=["GET", "POST"], endpoint="gestao_saas")
def gestao_saas():
    conn = get_db_connection()
    try:
        _ensure_saas_defaults(conn)

        company_name_filter = (request.args.get("company_name") or "").strip().lower()
        plan_filter = (request.args.get("plan_name") or "").strip().lower()
        status_filter = (request.args.get("status_filter") or "ativo").strip().lower()
        sort_field = (request.args.get("sort_field") or "name").strip().lower()
        sort_dir = (request.args.get("sort_dir") or "asc").strip().lower()
        if sort_field not in {"name", "created_at", "last_access_at", "value"}:
            sort_field = "name"
        if sort_dir not in {"asc", "desc"}:
            sort_dir = "asc"

        if request.method == "POST":
            action = (request.form.get("action") or "").strip().lower()
            now = _now_str()

            if action == "save_company":
                account_id = _safe_int(request.form.get("account_id"), 0)
                legal_name = (request.form.get("legal_name") or "").strip()
                trade_name = (request.form.get("trade_name") or "").strip()
                cnpj = (request.form.get("cnpj") or "").strip()
                email = (request.form.get("email") or "").strip() or None
                phone = (request.form.get("phone") or "").strip() or None
                whatsapp = (request.form.get("whatsapp") or "").strip()
                responsible_name = (request.form.get("responsible_name") or "").strip()
                status = (request.form.get("account_status") or "ativa").strip().lower()
                owner_username = (request.form.get("owner_username") or "").strip()
                owner_password = request.form.get("owner_password") or ""

                if status not in ACCOUNT_STATUS:
                    status = "ativa"

                if not legal_name or not whatsapp:
                    flash("Razão social e WhatsApp são obrigatórios.", "error")
                    return redirect(url_for("saas.gestao_saas"))

                if account_id > 0:
                    conn.execute(
                        """
                        UPDATE accounts
                        SET name = %s,
                            trade_name = %s,
                            cnpj = %s,
                            primary_email = %s,
                            phone = %s,
                            whatsapp = %s,
                            responsible_name = %s,
                            status = %s,
                            updated_at = %s
                        WHERE id = %s
                        """,
                        (legal_name, trade_name or legal_name, cnpj, email, phone, whatsapp, responsible_name, status, now, account_id),
                    )
                    conn.commit()
                    _log_panel_access("update_company", {"account_id": account_id, "status": status})
                    flash("Empresa atualizada com sucesso.", "success")
                else:
                    if not all([responsible_name, owner_username, owner_password]):
                        flash("Para nova empresa informe responsável, login principal e senha.", "error")
                        return redirect(url_for("saas.gestao_saas"))

                    new_account_id = create_account_with_owner(
                        account_name=legal_name,
                        owner_name=responsible_name,
                        username=owner_username,
                        password=owner_password,
                        email=email,
                    )
                    conn.execute(
                        """
                        UPDATE accounts
                        SET trade_name = %s,
                            cnpj = %s,
                            primary_email = %s,
                            phone = %s,
                            whatsapp = %s,
                            responsible_name = %s,
                            status = %s,
                            updated_at = %s
                        WHERE id = %s
                        """,
                        (trade_name or legal_name, cnpj, email, phone, whatsapp, responsible_name, status, now, new_account_id),
                    )
                    conn.commit()
                    _log_panel_access("create_company", {"account_id": new_account_id})
                    flash("Empresa criada com sucesso.", "success")

                return redirect(url_for("saas.gestao_saas"))

            if action == "inactivate_company":
                account_id = _safe_int(request.form.get("account_id"), 0)
                if account_id > 0:
                    conn.execute(
                        "UPDATE accounts SET status = 'inativa', updated_at = %s WHERE id = %s",
                        (now, account_id),
                    )
                    conn.commit()
                    _log_panel_access("inactivate_company", {"account_id": account_id})
                    flash("Empresa inativada com sucesso.", "success")
                return redirect(url_for("saas.gestao_saas"))

            if action == "save_plan":
                plan_id = _safe_int(request.form.get("plan_id"), 0)
                name = (request.form.get("plan_name") or "").strip()
                monthly = _safe_float(request.form.get("price_monthly"), 0.0)
                yearly = _safe_float(request.form.get("price_yearly"), 0.0)
                setup_fee = _safe_float(request.form.get("setup_fee"), 0.0)
                features = _parse_json_or_text(request.form.get("plan_features"))
                limits = _parse_json_or_text(request.form.get("plan_limits"))
                apply_scope = (request.form.get("apply_price_scope") or "novos").strip().lower()

                if not name:
                    flash("Nome do plano e obrigatorio.", "error")
                    return redirect(url_for("saas.gestao_saas"))

                if plan_id > 0:
                    old = conn.execute(
                        "SELECT price_monthly, price_yearly FROM saas_plans WHERE id = %s",
                        (plan_id,),
                    ).fetchone()
                    conn.execute(
                        """
                        UPDATE saas_plans
                        SET name = %s,
                            price_monthly = %s,
                            price_yearly = %s,
                            setup_fee = %s,
                            features_json = %s,
                            limits_json = %s,
                            updated_at = %s
                        WHERE id = %s
                        """,
                        (name, monthly, yearly, setup_fee, _serialize_json(features), _serialize_json(limits), now, plan_id),
                    )
                    conn.execute(
                        """
                        INSERT INTO saas_plan_price_history (
                            plan_id, old_monthly, old_yearly, new_monthly, new_yearly,
                            apply_scope, changed_by_user_id, changed_by_user_name, changed_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            plan_id,
                            _safe_float(old["price_monthly"] if old else 0),
                            _safe_float(old["price_yearly"] if old else 0),
                            monthly,
                            yearly,
                            apply_scope,
                            _current_user_id(),
                            session.get("user_name") or session.get("user"),
                            now,
                        ),
                    )
                    if apply_scope == "existentes":
                        conn.execute(
                            """
                            UPDATE saas_subscriptions
                            SET amount = CASE WHEN billing_cycle = 'anual' THEN %s ELSE %s END,
                                updated_at = %s
                            WHERE plan_id = %s
                            """,
                            (yearly, monthly, now, plan_id),
                        )
                    flash("Plano atualizado com sucesso.", "success")
                    _log_panel_access("update_plan", {"plan_id": plan_id, "apply_scope": apply_scope})
                else:
                    conn.execute(
                        """
                        INSERT INTO saas_plans (
                            name, price_monthly, price_yearly, setup_fee, features_json,
                            limits_json, is_active, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s)
                        """,
                        (name, monthly, yearly, setup_fee, _serialize_json(features), _serialize_json(limits), now, now),
                    )
                    flash("Plano criado com sucesso.", "success")
                    _log_panel_access("create_plan", {"name": name})

                conn.commit()
                return redirect(url_for("saas.gestao_saas"))

            if action == "delete_plan":
                plan_id = _safe_int(request.form.get("plan_id"), 0)
                if plan_id > 0:
                    conn.execute("UPDATE saas_plans SET is_active = 0, updated_at = %s WHERE id = %s", (now, plan_id))
                    conn.commit()
                    _log_panel_access("inactivate_plan", {"plan_id": plan_id})
                    flash("Plano inativado.", "success")
                return redirect(url_for("saas.gestao_saas"))

            if action == "assign_subscription":
                ok, message = _upsert_subscription(conn, request.form)
                if ok:
                    conn.commit()
                    _log_panel_access("assign_subscription", {"account_id": _safe_int(request.form.get("account_id"), 0)})
                    flash(message, "success")
                else:
                    flash(message, "error")
                return redirect(url_for("saas.gestao_saas"))

            if action == "save_charge":
                account_id = _safe_int(request.form.get("account_id"), 0)
                charge_type = (request.form.get("charge_type") or "mensalidade").strip().lower()
                reference_period = (request.form.get("reference_period") or "").strip() or _today_str()[:7]
                due_date = (request.form.get("due_date") or _today_str()).strip()
                amount = _safe_float(request.form.get("amount"), 0.0)
                notes = (request.form.get("notes") or "").strip() or None
                subscription = conn.execute("SELECT id FROM saas_subscriptions WHERE account_id = %s", (account_id,)).fetchone()

                if account_id <= 0 or amount <= 0:
                    flash("Conta e valor são obrigatórios para cobrança.", "error")
                    return redirect(url_for("saas.gestao_saas"))

                conn.execute(
                    """
                    INSERT INTO saas_billing_events (
                        account_id, subscription_id, charge_type, reference_period,
                        due_date, amount, status, notes, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 'pendente', %s, %s, %s)
                    """,
                    (account_id, subscription["id"] if subscription else None, charge_type, reference_period, due_date, amount, notes, now, now),
                )
                conn.commit()
                _log_panel_access("create_charge", {"account_id": account_id, "amount": amount})
                flash("Cobrança registrada com sucesso.", "success")
                return redirect(url_for("saas.gestao_saas"))

            if action in {"mark_paid", "mark_pending"}:
                billing_id = _safe_int(request.form.get("billing_id"), 0)
                if billing_id > 0:
                    if action == "mark_paid":
                        conn.execute(
                            "UPDATE saas_billing_events SET status = 'pago', paid_at = %s, updated_at = %s WHERE id = %s",
                            (now, now, billing_id),
                        )
                    else:
                        conn.execute(
                            "UPDATE saas_billing_events SET status = 'pendente', paid_at = NULL, updated_at = %s WHERE id = %s",
                            (now, billing_id),
                        )
                    conn.commit()
                    _log_panel_access(action, {"billing_id": billing_id})
                    flash("Status da cobrança atualizado.", "success")
                return redirect(url_for("saas.gestao_saas"))

            if action == "run_daily_monitor":
                _run_daily_monitor(conn, reference_date=_today_str())
                conn.commit()
                _log_panel_access("run_daily_monitor", {})
                flash("Monitoramento diário executado com sucesso.", "success")
                return redirect(url_for("saas.gestao_saas"))

            if action == "save_automation":
                settings_map = {
                    "auto_block_enabled": "1" if request.form.get("auto_block_enabled") else "0",
                    "default_suspension_days": str(_safe_int(request.form.get("default_suspension_days"), 10)),
                    "send_billing_email": "1" if request.form.get("send_billing_email") else "0",
                    "send_billing_whatsapp": "1" if request.form.get("send_billing_whatsapp") else "0",
                    "daily_monitor_hour": (request.form.get("daily_monitor_hour") or "07:30").strip(),
                    "apply_new_prices_default": (request.form.get("apply_new_prices_default") or "novos").strip(),
                    "whatsapp_api_url": (request.form.get("whatsapp_api_url") or "").strip(),
                    "whatsapp_api_token": (request.form.get("whatsapp_api_token") or "").strip(),
                    "whatsapp_timeout_seconds": str(_safe_int(request.form.get("whatsapp_timeout_seconds"), 12)),
                    "whatsapp_template_overdue": (request.form.get("whatsapp_template_overdue") or "").strip(),
                    "whatsapp_template_blocked": (request.form.get("whatsapp_template_blocked") or "").strip(),
                    "whatsapp_template_reactivated": (request.form.get("whatsapp_template_reactivated") or "").strip(),
                    "whatsapp_template_low_usage": (request.form.get("whatsapp_template_low_usage") or "").strip(),
                }
                for key, value in settings_map.items():
                    conn.execute(
                        """
                        INSERT INTO saas_automation_settings (setting_key, setting_value, updated_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (setting_key) DO UPDATE
                        SET setting_value = EXCLUDED.setting_value,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (key, value, now),
                    )
                conn.commit()
                _log_panel_access("save_automation", settings_map)
                flash("Configurações avançadas salvas.", "success")
                return redirect(url_for("saas.gestao_saas"))

        _run_daily_monitor(conn, reference_date=_today_str())
        conn.commit()

        selected_account_id = _safe_int(request.args.get("edit_account_id"), 0)
        selected_plan_id = _safe_int(request.args.get("edit_plan_id"), 0)

        insight_company_filter = (request.args.get("insight_company") or "").strip().lower()
        insight_type_filter = (request.args.get("insight_type") or "").strip().lower()
        insight_severity_filter = (request.args.get("insight_severity") or "").strip().lower()
        insight_term_filter = (request.args.get("insight_term") or "").strip().lower()
        insight_start_date = (request.args.get("insight_start_date") or "").strip()
        insight_end_date = (request.args.get("insight_end_date") or "").strip()

        companies = conn.execute(
            """
            SELECT a.id, a.name, a.slug, a.trade_name, a.cnpj, a.primary_email, a.phone, a.whatsapp,
                   a.responsible_name, COALESCE(a.status, 'ativa') AS status, a.created_at,
                   COALESCE(a.last_access_at, '-') AS last_access_at,
                   o.username AS owner_username,
                   s.status AS subscription_status,
                   p.name AS plan_name,
                   COALESCE(s.amount, 0) AS subscription_amount,
                   COALESCE(s.billing_cycle, '-') AS billing_cycle
            FROM accounts a
            LEFT JOIN users o ON o.account_id = a.id AND o.role = 'owner'
            LEFT JOIN saas_subscriptions s ON s.account_id = a.id
            LEFT JOIN saas_plans p ON p.id = s.plan_id
            ORDER BY a.id DESC
            """
        ).fetchall()
        companies = [dict(row) for row in companies]

        for company in companies:
            company["created_at_display"] = _format_datetime_br(company.get("created_at"))
            company["last_access_at_display"] = _format_datetime_br(company.get("last_access_at"))

        if company_name_filter:
            companies = [
                c
                for c in companies
                if company_name_filter in (c.get("name") or "").lower()
                or company_name_filter in (c.get("trade_name") or "").lower()
            ]

        if plan_filter:
            companies = [c for c in companies if plan_filter in (c.get("plan_name") or "").lower()]

        if status_filter == "ativo":
            companies = [c for c in companies if (c.get("status") or "").lower() == "ativa"]
        elif status_filter == "inativos":
            companies = [c for c in companies if (c.get("status") or "").lower() != "ativa"]

        def company_sort_key(item):
            if sort_field == "created_at":
                dt = _parse_datetime(item.get("created_at"))
                return dt or datetime.min
            if sort_field == "last_access_at":
                dt = _parse_datetime(item.get("last_access_at"))
                return dt or datetime.min
            if sort_field == "value":
                return _safe_float(item.get("subscription_amount"), 0)
            return (item.get("name") or "").lower()

        companies = sorted(companies, key=company_sort_key, reverse=(sort_dir == "desc"))

        plans = conn.execute(
            """
            SELECT id, name, price_monthly, price_yearly, setup_fee, features_json, limits_json, is_active, updated_at
            FROM saas_plans
            ORDER BY is_active DESC, name
            """
        ).fetchall()
        plans = [
            {
                **dict(row),
                "features_text": "\n".join(_parse_json_or_text(row["features_json"])),
                "limits_text": "\n".join(_parse_json_or_text(row["limits_json"])),
            }
            for row in plans
        ]

        subscriptions = conn.execute(
            """
            SELECT s.id, s.account_id, a.name AS account_name, p.name AS plan_name, s.billing_cycle,
                   s.amount, s.setup_fee_amount, s.status, s.starts_at, s.next_due_date,
                   s.suspension_days, s.auto_block_enabled, s.apply_new_prices_to_existing
            FROM saas_subscriptions s
            JOIN accounts a ON a.id = s.account_id
            JOIN saas_plans p ON p.id = s.plan_id
            ORDER BY a.name
            """
        ).fetchall()
        subscriptions = [
            {
                **dict(row),
                "starts_at_display": _format_date_br(row["starts_at"]),
                "next_due_date_display": _format_date_br(row["next_due_date"]),
            }
            for row in subscriptions
        ]

        billings = conn.execute(
            """
            SELECT b.id, b.account_id, a.name AS account_name, b.charge_type, b.reference_period,
                   b.due_date, b.amount, b.status, COALESCE(b.paid_at, '-') AS paid_at
            FROM saas_billing_events b
            JOIN accounts a ON a.id = b.account_id
            ORDER BY b.id DESC
            LIMIT 250
            """
        ).fetchall()
        billings = [
            {
                **dict(row),
                "due_date_display": _format_date_br(row["due_date"]),
                "paid_at_display": _format_datetime_br(row["paid_at"]),
                "reference_period_display": _format_reference_period(row["reference_period"]),
            }
            for row in billings
        ]

        insight_where = []
        insight_params = []
        if insight_company_filter:
            insight_where.append("LOWER(a.name) LIKE %s")
            insight_params.append(f"%{insight_company_filter}%")
        if insight_type_filter and insight_type_filter != "todos":
            insight_where.append("LOWER(i.insight_type) = %s")
            insight_params.append(insight_type_filter)
        if insight_severity_filter and insight_severity_filter != "todas":
            insight_where.append("LOWER(i.severity) = %s")
            insight_params.append(insight_severity_filter)
        if insight_term_filter:
            insight_where.append("(LOWER(i.title) LIKE %s OR LOWER(i.message) LIKE %s)")
            insight_params.append(f"%{insight_term_filter}%")
            insight_params.append(f"%{insight_term_filter}%")
        if insight_start_date:
            insight_where.append("i.generated_on >= %s")
            insight_params.append(insight_start_date)
        if insight_end_date:
            insight_where.append("i.generated_on <= %s")
            insight_params.append(insight_end_date)

        insight_sql = (
            """
            SELECT i.id, i.account_id, a.name AS account_name, i.insight_type, i.severity, i.title,
                   i.message, i.generated_on, i.resolved
            FROM saas_insights i
            JOIN accounts a ON a.id = i.account_id
            """
        )
        if insight_where:
            insight_sql += " WHERE " + " AND ".join(insight_where)
        insight_sql += " ORDER BY i.id DESC LIMIT 300"

        insights = conn.execute(insight_sql, tuple(insight_params)).fetchall()
        insights = [{**dict(row), "generated_on_display": _format_date_br(row["generated_on"])} for row in insights]

        access_logs = conn.execute(
            """
            SELECT id, username, action, method, path, created_at
            FROM saas_panel_access_logs
            ORDER BY id DESC
            LIMIT 200
            """
        ).fetchall()
        access_logs = [{**dict(row), "created_at_display": _format_datetime_br(row["created_at"])} for row in access_logs]

        usage_last_30 = conn.execute(
            """
            SELECT u.account_id, a.name AS account_name, u.usage_date, u.active_users,
                   u.total_sessions, u.avg_session_minutes, u.top_feature
            FROM saas_usage_daily u
            JOIN accounts a ON a.id = u.account_id
            WHERE u.usage_date >= %s
            ORDER BY u.usage_date DESC
            """,
            ((datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),),
        ).fetchall()

        automation_settings = _automation_settings_map(conn)

        price_history = conn.execute(
            """
            SELECT h.id, p.name AS plan_name, h.old_monthly, h.old_yearly, h.new_monthly, h.new_yearly,
                   h.apply_scope, h.changed_by_user_name, h.changed_at
            FROM saas_plan_price_history h
            JOIN saas_plans p ON p.id = h.plan_id
            ORDER BY h.id DESC
            LIMIT 120
            """
        ).fetchall()

        kpi = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM accounts WHERE COALESCE(status, 'ativa') = 'ativa') AS active_accounts,
              (SELECT COUNT(*) FROM accounts WHERE COALESCE(status, 'ativa') <> 'ativa') AS inactive_accounts,
              (SELECT COUNT(*) FROM saas_billing_events WHERE status IN ('pendente', 'atrasado')) AS delinquent_count,
              (SELECT COALESCE(SUM(amount), 0) FROM saas_billing_events WHERE status = 'pago' AND due_date >= %s) AS monthly_revenue,
              (SELECT COALESCE(SUM(amount), 0) FROM saas_billing_events WHERE status = 'pago' AND due_date >= %s) AS annual_revenue,
              (SELECT COALESCE(AVG(avg_session_minutes), 0) FROM saas_usage_daily WHERE usage_date >= %s) AS avg_usage_minutes
            """,
            (
                datetime.now().replace(day=1).strftime("%Y-%m-%d"),
                datetime.now().replace(month=1, day=1).strftime("%Y-%m-%d"),
                (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            ),
        ).fetchone()

        top_features = conn.execute(
            """
            SELECT top_feature, COUNT(*) AS total
            FROM saas_usage_daily
            WHERE usage_date >= %s
              AND top_feature IS NOT NULL
              AND top_feature <> '-'
              AND LOWER(top_feature) <> 'static'
            GROUP BY top_feature
            ORDER BY total DESC
            LIMIT 8
            """,
            ((datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),),
        ).fetchall()

        top_accounts = conn.execute(
            """
            SELECT a.name AS account_name, COALESCE(SUM(u.total_sessions), 0) AS sessions
            FROM saas_usage_daily u
            JOIN accounts a ON a.id = u.account_id
            WHERE u.usage_date >= %s
            GROUP BY a.name
            ORDER BY sessions DESC
            LIMIT 8
            """,
            ((datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),),
        ).fetchall()

        usage_daily_rows = conn.execute(
            """
            SELECT usage_date, SUM(total_sessions) AS sessions, AVG(active_users) AS active_users
            FROM saas_usage_daily
            WHERE usage_date >= %s
            GROUP BY usage_date
            ORDER BY usage_date
            """,
            ((datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),),
        ).fetchall()
        usage_chart_labels = [row["usage_date"] for row in usage_daily_rows]
        usage_chart_sessions = [int(row["sessions"] or 0) for row in usage_daily_rows]
        usage_chart_active_users = [round(float(row["active_users"] or 0), 2) for row in usage_daily_rows]

        feature_chart_labels = [str(row["top_feature"] or "-") for row in top_features]
        feature_chart_values = [int(row["total"] or 0) for row in top_features]

        account_chart_labels = [str(row["account_name"] or "-") for row in top_accounts]
        account_chart_values = [int(row["sessions"] or 0) for row in top_accounts]

        selected_company = None
        if selected_account_id > 0:
            selected_company = next((row for row in companies if int(row["id"]) == selected_account_id), None)

        selected_plan = None
        if selected_plan_id > 0:
            selected_plan = next((row for row in plans if int(row["id"]) == selected_plan_id), None)

        _log_panel_access("view_dashboard", {"selected_account_id": selected_account_id})
        return render_template(
            "saas_management.html",
            title="Gestão SaaS Multiempresa",
            companies=companies,
            plans=plans,
            subscriptions=subscriptions,
            billings=billings,
            insights=insights,
            usage_last_30=usage_last_30,
            top_features=top_features,
            top_accounts=top_accounts,
            access_logs=access_logs,
            automation_settings=automation_settings,
            price_history=price_history,
            kpi=kpi,
            selected_company=selected_company,
            selected_plan=selected_plan,
            usage_chart_labels_json=json.dumps(usage_chart_labels, ensure_ascii=False),
            usage_chart_sessions_json=json.dumps(usage_chart_sessions, ensure_ascii=False),
            usage_chart_active_users_json=json.dumps(usage_chart_active_users, ensure_ascii=False),
            feature_chart_labels_json=json.dumps(feature_chart_labels, ensure_ascii=False),
            feature_chart_values_json=json.dumps(feature_chart_values, ensure_ascii=False),
            account_chart_labels_json=json.dumps(account_chart_labels, ensure_ascii=False),
            account_chart_values_json=json.dumps(account_chart_values, ensure_ascii=False),
            can_edit_saas=_can_access_saas(require_edit=True),
            can_delete_saas=_can_access_saas(require_delete=True),
            company_filters={
                "company_name": request.args.get("company_name") or "",
                "plan_name": request.args.get("plan_name") or "",
                "status_filter": status_filter,
                "sort_field": sort_field,
                "sort_dir": sort_dir,
            },
            insight_filters={
                "insight_company": request.args.get("insight_company") or "",
                "insight_type": request.args.get("insight_type") or "todos",
                "insight_severity": request.args.get("insight_severity") or "todas",
                "insight_term": request.args.get("insight_term") or "",
                "insight_start_date": request.args.get("insight_start_date") or "",
                "insight_end_date": request.args.get("insight_end_date") or "",
            },
        )
    finally:
        conn.close()


@saas_bp.route("/admin/saas-management/export", methods=["GET"], endpoint="export_saas_report")
def export_saas_report():
    if not _can_access_saas():
        flash("Acesso negado.", "error")
        return redirect(url_for("dashboard"))

    report_type = (request.args.get("report_type") or "financeiro").strip().lower()
    report_format = (request.args.get("format") or "excel").strip().lower()
    start_date = (request.args.get("start_date") or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")).strip()
    end_date = (request.args.get("end_date") or _today_str()).strip()

    conn = get_db_connection()
    try:
        rows = _build_report_rows(conn, report_type, start_date, end_date)
    finally:
        conn.close()

    data = [dict(r) for r in rows]
    filename_base = f"relatorio_saas_{report_type}_{start_date}_{end_date}".replace("/", "-")

    if report_format == "excel":
        if pd is None:
            flash("Dependência pandas não disponível para exportação Excel.", "error")
            return redirect(url_for("saas.gestao_saas"))

        df = pd.DataFrame(data)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Relatório")
        buffer.seek(0)
        _log_panel_access("export_report", {"type": report_type, "format": "excel"})
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{filename_base}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    if report_format == "pdf":
        if SimpleDocTemplate is None:
            flash("Dependência reportlab não disponível para exportação PDF.", "error")
            return redirect(url_for("saas.gestao_saas"))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = [
            Paragraph("Relatório SaaS", styles["Title"]),
            Paragraph(f"Tipo: {report_type} | Período: {start_date} a {end_date}", styles["Normal"]),
            Spacer(1, 12),
        ]

        if data:
            headers = list(data[0].keys())
            table_data = [headers] + [[str(item.get(h, "")) for h in headers] for item in data[:80]]
            table = Table(table_data, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b4a82")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            elements.append(table)
        else:
            elements.append(Paragraph("Sem dados para o período selecionado.", styles["Normal"]))

        doc.build(elements)
        buffer.seek(0)
        _log_panel_access("export_report", {"type": report_type, "format": "pdf"})
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{filename_base}.pdf",
            mimetype="application/pdf",
        )

    flash("Formato de exportacao invalido.", "error")
    return redirect(url_for("saas.gestao_saas"))
