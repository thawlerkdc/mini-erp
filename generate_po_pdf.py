import io
from flask import Blueprint, request, send_file, session
from models import get_db_connection
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

generate_po_pdf_bp = Blueprint('generate_po_pdf', __name__)

@generate_po_pdf_bp.route('/pedido_compra/pdf/<int:po_id>')
def pedido_compra_pdf(po_id):
    account_id = session.get('account_id')
    conn = get_db_connection()
    po = conn.execute(
        "SELECT po.*, p.name AS product_name, s.name AS supplier_name, s.cnpj AS supplier_cnpj, s.email AS supplier_email, s.phone AS supplier_phone "
        "FROM purchase_orders po "
        "LEFT JOIN products p ON po.product_id = p.id "
        "LEFT JOIN suppliers s ON po.supplier_id = s.id "
        "WHERE po.id = %s AND po.account_id = %s",
        (po_id, account_id)
    ).fetchone()
    conn.close()
    if not po:
        return "Pedido não encontrado", 404
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    x = 40
    y = height - 40
    c.setFont('Helvetica-Bold', 18)
    c.drawString(x, y, f"Pedido de Compra #{po['id']}")
    y -= 30
    c.setFont('Helvetica', 12)
    c.drawString(x, y, f"Data: {po['created_at']}")
    y -= 20
    c.drawString(x, y, f"Fornecedor: {po['supplier_name'] or '-'}")
    y -= 18
    c.drawString(x, y, f"CNPJ: {po['supplier_cnpj'] or '-'}")
    y -= 18
    c.drawString(x, y, f"E-mail: {po['supplier_email'] or '-'}")
    y -= 18
    c.drawString(x, y, f"Telefone: {po['supplier_phone'] or '-'}")
    y -= 28
    c.setFont('Helvetica-Bold', 14)
    c.drawString(x, y, "Itens do Pedido:")
    y -= 22
    c.setFont('Helvetica-Bold', 12)
    c.drawString(x, y, "Produto")
    c.drawString(x+180, y, "Quantidade")
    c.drawString(x+280, y, "Valor Unitário")
    c.drawString(x+400, y, "Total")
    y -= 18
    c.setFont('Helvetica', 12)
    c.drawString(x, y, po['product_name'])
    c.drawString(x+180, y, str(po['quantity']))
    c.drawString(x+280, y, f"R$ {po['unit_cost']:.2f}")
    total = (po['quantity'] or 0) * (po['unit_cost'] or 0)
    c.drawString(x+400, y, f"R$ {total:.2f}")
    y -= 28
    c.setFont('Helvetica-Bold', 12)
    c.drawString(x, y, f"Total do Pedido: R$ {total:.2f}")
    y -= 24
    c.setFont('Helvetica', 12)
    c.drawString(x, y, f"Parcelas: {po['installments']} | 1ª Vencimento: {po['first_due_date'] or '-'}")
    y -= 18
    c.drawString(x, y, f"Previsão de entrega: {po['expected_date'] or '-'}")
    y -= 18
    c.drawString(x, y, f"Status: {po['status']}")
    y -= 18
    if po['notes']:
        c.drawString(x, y, f"Observações: {po['notes']}")
    c.showPage()
    c.save()
    output.seek(0)
    filename = f"pedido_compra_{po['id']}.pdf"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

