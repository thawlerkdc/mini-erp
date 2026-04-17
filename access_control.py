from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from models import get_db_connection
from datetime import datetime

access_bp = Blueprint('access', __name__)

MODULES = [
    {'key': 'dashboard', 'label': 'Dashboard'},
    {'key': 'vendas', 'label': 'Vendas'},
    {'key': 'financeiro', 'label': 'Financeiro'},
    {'key': 'estoque', 'label': 'Estoque'},
    {'key': 'compras', 'label': 'Compras'},
    {'key': 'relatorios', 'label': 'Relatórios'},
    {'key': 'cadastro', 'label': 'Cadastros'},
    {'key': 'parametros', 'label': 'Parâmetros'},
    {'key': 'usuarios', 'label': 'Usuários'},
    {'key': 'auditoria', 'label': 'Logs e Auditoria'},
]

@access_bp.route('/controle_acesso', methods=['GET', 'POST'], endpoint='controle_acesso')
def controle_acesso():
    if session.get('role') != 'owner':
        flash('Acesso restrito ao administrador.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    account_id = session.get('account_id')
    users = conn.execute(
        "SELECT id, username, name FROM users WHERE account_id = %s AND id != %s ORDER BY username",
        (account_id, session.get('user_id')),
    ).fetchall()

    selected_user_id = request.args.get('user_id')

    if request.method == 'POST':
        selected_user_id = request.form.get('user_id')
        if not selected_user_id:
            flash('Selecione um usuário para configurar as permissões.', 'error')
            conn.close()
            return redirect(url_for('.controle_acesso'))

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for module in MODULES:
            module_key = module['key']
            can_view = 1 if request.form.get(f'{module_key}_view') else 0
            can_edit = 1 if request.form.get(f'{module_key}_edit') else 0
            can_delete = 1 if request.form.get(f'{module_key}_delete') else 0
            conn.execute(
                """
                INSERT INTO user_permissions (account_id, user_id, module, can_view, can_edit, can_delete, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (account_id, user_id, module) DO UPDATE SET
                  can_view=EXCLUDED.can_view, can_edit=EXCLUDED.can_edit, can_delete=EXCLUDED.can_delete, updated_at=EXCLUDED.updated_at
                """,
                (account_id, selected_user_id, module_key, can_view, can_edit, can_delete, now, now),
            )
        conn.commit()
        flash('Permissões atualizadas com sucesso.', 'success')
        conn.close()
        return redirect(url_for('.controle_acesso', user_id=selected_user_id))

    if not selected_user_id and users:
        selected_user_id = str(users[0]['id'])

    selected_permissions = {}
    if selected_user_id:
        perms = conn.execute(
            "SELECT module, can_view, can_edit, can_delete FROM user_permissions WHERE account_id = %s AND user_id = %s",
            (account_id, selected_user_id),
        ).fetchall()
        selected_permissions = {p['module']: p for p in perms}

    conn.close()
    return render_template(
        'controle_acesso.html',
        users=users,
        modules=MODULES,
        selected_user_id=selected_user_id,
        selected_permissions=selected_permissions,
    )

