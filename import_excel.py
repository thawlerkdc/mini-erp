import io
import pandas as pd
from flask import Blueprint, request, render_template, send_file, flash, redirect, url_for, session
from models import get_db_connection
from datetime import datetime

import_excel_bp = Blueprint('import_excel', __name__)

MODULES = {
    'clientes': ['Nome', 'Email', 'Telefone', 'CPF/CNPJ', 'Data de nascimento'],
    'produtos': ['Nome', 'Categoria', 'Unidade', 'Custo', 'Preço', 'Estoque'],
    'fornecedores': ['Nome', 'Email', 'Telefone', 'CNPJ'],
}

@import_excel_bp.route('/importar_dados', methods=['GET', 'POST'], endpoint='importar_dados')
def importar_dados():
    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file:
            flash('Selecione um arquivo Excel.', 'error')
            return redirect(url_for('.importar_dados'))
        try:
            df_dict = pd.read_excel(file, sheet_name=None)
        except Exception as e:
            flash(f'Erro ao ler o arquivo: {e}', 'error')
            return redirect(url_for('.importar_dados'))
        errors = {}
        for module, df in df_dict.items():
            expected_cols = MODULES.get(module.lower())
            if not expected_cols:
                errors[module] = ['Módulo não reconhecido.']
                continue
            missing = [col for col in expected_cols if col not in df.columns]
            if missing:
                errors[module] = [f'Colunas ausentes: {", ".join(missing)}']
        if errors:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                for module, df in df_dict.items():
                    df_out = df.copy()
                    if module in errors:
                        for col in df_out.columns:
                            df_out[col] = df_out[col].astype(str)
                        df_out.loc[:, 'ERRO'] = '\n'.join(errors[module])
                    df_out.to_excel(writer, sheet_name=module, index=False)
            output.seek(0)
            return send_file(output, as_attachment=True, download_name='import_erros.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        # TODO: Inserir dados no banco se não houver erros
        flash('Importação realizada com sucesso!', 'success')
        return redirect(url_for('.importar_dados'))
    return render_template('importar_dados.html', modules=MODULES)

@import_excel_bp.route('/download_template', endpoint='download_template')
def download_template():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for module, cols in MODULES.items():
            df = pd.DataFrame(columns=cols)
            df.to_excel(writer, sheet_name=module, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='template_importacao.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

