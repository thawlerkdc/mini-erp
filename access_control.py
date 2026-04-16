from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from models import get_db_connection
from datetime import datetime

access_bp = Blueprint('access', __name__)

MODULES = [
    'dashboard', 'vendas', 'financeiro', 'estoque', 'compras', 'relatorios', 'cadastro', 'parametros', 'usuarios'
]

@access_bp.route('/controle_acesso', methods=['GET', 'POST'])
def controle_acesso():
    if session.get('role') != 'owner':
        flash('Acesso restrito ao administrador.', 'error')
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    account_id = session.get('account_id')
    users = conn.execute("SELECT * FROM users WHERE account_id = %s AND id != %s", (account_id, session.get('user_id'))).fetchall()
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        for module in MODULES:
            can_view = 1 if request.form.get(f'{module}_view') else 0
            can_edit = 1 if request.form.get(f'{module}_edit') else 0
            can_delete = 1 if request.form.get(f'{module}_delete') else 0
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute("""
                INSERT INTO user_permissions (account_id, user_id, module, can_view, can_edit, can_delete, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (account_id, user_id, module) DO UPDATE SET
                  can_view=EXCLUDED.can_view, can_edit=EXCLUDED.can_edit, can_delete=EXCLUDED.can_delete, updated_at=EXCLUDED.updated_at
            """, (account_id, user_id, module, can_view, can_edit, can_delete, now, now))
        conn.commit()
        flash('Permissões atualizadas!', 'success')
        return redirect(url_for('controle_acesso'))
    permissions = {}
    for user in users:
        perms = conn.execute("SELECT module, can_view, can_edit, can_delete FROM user_permissions WHERE account_id = %s AND user_id = %s", (account_id, user['id'])).fetchall()
        permissions[user['id']] = {p['module']: p for p in perms}
    conn.close()
    return render_template('controle_acesso.html', users=users, modules=MODULES, permissions=permissions)

