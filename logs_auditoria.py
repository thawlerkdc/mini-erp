import logging
import json
from flask import Blueprint, request, render_template, session, flash, redirect, url_for
from models import get_db_connection
from datetime import datetime, timedelta

auditoria_bp = Blueprint('auditoria', __name__)


def log_audit_event(event_type, payload=None):
    """Registra eventos explícitos de auditoria (ex.: acesso negado por permissão)."""
    if not session.get('user_id'):
        return

    conn = None
    try:
        conn = get_db_connection()
        account_id = session.get('account_id')
        user_id = session.get('user_id')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        event_payload = payload or {}
        event_payload['audit_event'] = event_type

        conn.execute(
            """
            INSERT INTO logs (account_id, user_id, endpoint, method, path, data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                account_id,
                user_id,
                request.endpoint or '',
                request.method,
                request.path,
                json.dumps(event_payload, ensure_ascii=False),
                now,
            ),
        )
        conn.commit()
    except Exception as exc:
        logging.exception("Falha ao registrar evento de auditoria: %s", exc)
    finally:
        if conn:
            conn.close()

@auditoria_bp.before_app_request
def registrar_log():
    if not session.get('user_id'):
        return
    conn = None
    try:
        conn = get_db_connection()
        account_id = session.get('account_id')
        user_id = session.get('user_id')
        endpoint = request.endpoint or ''
        method = request.method
        path = request.path
        data = dict(request.form) if request.form else None
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            """
            INSERT INTO logs (account_id, user_id, endpoint, method, path, data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (account_id, user_id, endpoint, method, path, str(data), now),
        )
        conn.commit()
    except Exception as exc:
        logging.exception("Falha ao registrar log de auditoria: %s", exc)
    finally:
        if conn:
            conn.close()

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
    return render_template(
        'auditoria.html',
        logs=logs,
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
        cutoff = (datetime.now() - timedelta(days=retention_days)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "DELETE FROM logs WHERE account_id = %s AND created_at < %s",
            (account_id, cutoff),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logging.exception("Falha ao limpar logs antigos: %s", exc)
