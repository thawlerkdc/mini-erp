import io
import pandas as pd
from flask import Blueprint, request, send_file
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

export_bp = Blueprint('export', __name__)

# Exportação para Excel
@export_bp.route('/export/excel', methods=['POST'])
def export_excel():
    data = request.json
    df = pd.DataFrame(data['rows'], columns=data['headers'])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatório')
    output.seek(0)
    filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Exportação para PDF
@export_bp.route('/export/pdf', methods=['POST'])
def export_pdf():
    data = request.json
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=landscape(A4))
    width, height = landscape(A4)
    x = 40
    y = height - 40
    c.setFont('Helvetica-Bold', 16)
    c.drawString(x, y, data.get('title', 'Relatório'))
    y -= 30
    c.setFont('Helvetica', 12)
    # Cabeçalhos
    for idx, header in enumerate(data['headers']):
        c.drawString(x + idx*120, y, str(header))
    y -= 20
    # Dados
    for row in data['rows']:
        for idx, cell in enumerate(row):
            c.drawString(x + idx*120, y, str(cell))
        y -= 18
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
    output.seek(0)
    filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

