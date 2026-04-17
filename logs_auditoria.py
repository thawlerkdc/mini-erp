import logging
import json
from flask import Blueprint, request, render_template, session
from models import get_db_connection
from datetime import datetime

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
    if session.get('role') != 'owner':
        return 'Acesso restrito', 403
    conn = get_db_connection()
    logs = conn.execute("SELECT l.*, u.username FROM logs l LEFT JOIN users u ON l.user_id = u.id ORDER BY l.id DESC LIMIT 200").fetchall()
    conn.close()
    return render_template('auditoria.html', logs=logs)

