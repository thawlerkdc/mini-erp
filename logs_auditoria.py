import logging
import json
from flask import Blueprint, request, render_template, session, flash, redirect, url_for
from models import get_db_connection
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

auditoria_bp = Blueprint('auditoria', __name__)

APP_TIMEZONE = 'America/Sao_Paulo'
_TZ = ZoneInfo(APP_TIMEZONE) if ZoneInfo else None


def _now_local():
    return datetime.now(_TZ) if _TZ else datetime.now()


def _insert_audit_log(account_id, user_id, endpoint, method, path, payload):
    if not account_id:
        return

    conn = None
    try:
        conn = get_db_connection()
        now = _now_local().strftime('%Y-%m-%d %H:%M:%S')
        serialized = json.dumps(payload or {}, ensure_ascii=False)
        conn.execute(
            """
            INSERT INTO logs (account_id, user_id, endpoint, method, path, data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (account_id, user_id, endpoint or '', method or '', path or '', serialized, now),
        )
        conn.commit()
    except Exception as exc:
        logging.exception("Falha ao registrar log de auditoria: %s", exc)
    finally:
        if conn:
            conn.close()


def log_audit_event(event_type, payload=None, account_id=None, user_id=None, endpoint=None, method=None, path=None):
    """Registra eventos explícitos de auditoria (ex.: acesso negado, email enviado, ação administrativa)."""
    resolved_account_id = account_id or session.get('account_id')
    resolved_user_id = session.get('user_id') if user_id is None else user_id
    event_payload = payload or {}
    event_payload['audit_event'] = event_type
    _insert_audit_log(
        resolved_account_id,
        resolved_user_id,
        endpoint or request.endpoint or '',
        method or request.method,
        path or request.path,
        event_payload,
    )


def get_recent_audit_logs(limit=200, account_id=None, event_types=None):
    conn = get_db_connection()

    where = []
    params = []
    if account_id is not None:
        where.append('l.account_id = %s')
        params.append(account_id)

    if event_types:
        event_clauses = []
        for event_type in event_types:
            event_clauses.append("LOWER(COALESCE(l.data, '')) LIKE %s")
            params.append(f'%"audit_event": "{event_type.lower()}"%')
        where.append('(' + ' OR '.join(event_clauses) + ')')

    query = (
        "SELECT l.*, u.username, COALESCE(u.name, u.username) AS user_name, a.name AS account_name "
        "FROM logs l "
        "LEFT JOIN users u ON l.user_id = u.id "
        "LEFT JOIN accounts a ON l.account_id = a.id "
    )
    if where:
        query += 'WHERE ' + ' AND '.join(where) + ' '
    query += 'ORDER BY l.id DESC LIMIT %s'
    params.append(limit)

    rows = conn.execute(query, tuple(params)).fetchall()
    conn.close()

    formatted = []
    for row in rows:
        item = dict(row)
        item['created_at_display'] = _format_datetime_br(item.get('created_at'))
        raw_data = item.get('data') or ''
        try:
            item['data_json'] = json.loads(raw_data) if isinstance(raw_data, str) and raw_data.startswith('{') else None
        except json.JSONDecodeError:
            item['data_json'] = None
        formatted.append(item)
    return formatted


@auditoria_bp.before_app_request
def registrar_log():
    if not session.get('user_id'):
        return
    _insert_audit_log(
        session.get('account_id'),
        session.get('user_id'),
        request.endpoint or '',
        request.method,
        request.path,
        dict(request.form) if request.form else None,
    )

@auditoria_bp.route('/auditoria', endpoint='auditoria')
def auditoria():
    if not session.get('user'):
        return 'Acesso restrito', 403

    account_id = session.get('account_id')
    start_date = (request.args.get('start_date') or '').strip()
    end_date = (request.args.get('end_date') or '').strip()

    # Date range validation
    if start_date and end_date and end_date < start_date:
        flash('A data final não pode ser menor que a data inicial.', 'error')
        return redirect(url_for('auditoria.auditoria'))

    # Auto-purge old logs based on retention setting
    _purge_old_logs(account_id)
    user_id = (request.args.get('user_id') or '').strip()
    method = (request.args.get('method') or '').strip().upper()
    endpoint_q = (request.args.get('endpoint') or '').strip()
    path_q = (request.args.get('path') or '').strip()
    event_type = (request.args.get('event_type') or '').strip()

    where = ["l.account_id = %s"]
    params = [account_id]

    if start_date:
        where.append("SUBSTRING(l.created_at, 1, 10) >= %s")
        params.append(start_date)
    if end_date:
        where.append("SUBSTRING(l.created_at, 1, 10) <= %s")
        params.append(end_date)
    if user_id:
        where.append("CAST(l.user_id AS TEXT) = %s")
        params.append(user_id)
    if method:
        where.append("UPPER(COALESCE(l.method, '')) = %s")
        params.append(method)
    if endpoint_q:
        where.append("LOWER(COALESCE(l.endpoint, '')) LIKE %s")
        params.append(f"%{endpoint_q.lower()}%")
    if path_q:
        where.append("LOWER(COALESCE(l.path, '')) LIKE %s")
        params.append(f"%{path_q.lower()}%")
    if event_type:
        where.append("LOWER(COALESCE(l.data, '')) LIKE %s")
        params.append(f'%"audit_event": "{event_type.lower()}"%')

    conn = get_db_connection()
    users = conn.execute(
        "SELECT id, username FROM users WHERE account_id = %s ORDER BY username",
        (account_id,),
    ).fetchall()

    logs = conn.execute(
        "SELECT l.*, u.username FROM logs l "
        "LEFT JOIN users u ON l.user_id = u.id "
        "WHERE " + " AND ".join(where) + " "
        "ORDER BY l.id DESC LIMIT 500",
        tuple(params),
    ).fetchall()
    conn.close()

    logs_formatted = []
    for row in logs:
        item = dict(row)
        item['created_at_display'] = _format_datetime_br(item.get('created_at'))
        logs_formatted.append(item)

    return render_template(
        'auditoria.html',
        logs=logs_formatted,
        users=users,
        filters={
            'start_date': start_date,
            'end_date': end_date,
            'user_id': user_id,
            'method': method,
            'endpoint': endpoint_q,
            'path': path_q,
            'event_type': event_type,
        },
    )


def _purge_old_logs(account_id):
    """Delete logs older than log_retention_days setting (default 30)."""
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT setting_value FROM account_settings WHERE account_id = %s AND setting_key = 'log_retention_days'",
            (account_id,),
        ).fetchone()
        retention_days = int(row['setting_value']) if row and row['setting_value'] else 30
        if retention_days <= 0:
            conn.close()
            return
        cutoff = (_now_local() - timedelta(days=retention_days)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "DELETE FROM logs WHERE account_id = %s AND created_at < %s",
            (account_id, cutoff),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logging.exception("Falha ao limpar logs antigos: %s", exc)


def _format_datetime_br(value):
    """Converte data/hora para DD/MM/YYYY HH:MM:SS quando possível."""
    if value is None:
        return '-'

    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y %H:%M:%S')

    text = str(value).strip()
    if not text:
        return '-'

    sample = text[:19].replace('T', ' ')
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            parsed = datetime.strptime(sample if fmt.endswith('%S') else sample[:10], fmt)
            return parsed.strftime('%d/%m/%Y %H:%M:%S' if fmt.endswith('%S') else '%d/%m/%Y')
        except ValueError:
            continue

    return text
