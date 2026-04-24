import io
from flask import Blueprint, request, send_file, session
from models import get_db_connection
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from urllib.request import urlopen
from datetime import datetime

generate_po_pdf_bp = Blueprint('generate_po_pdf', __name__)


def _format_date_br(value):
    if not value:
        return "-"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return f"{text[8:10]}/{text[5:7]}/{text[0:4]}"
    return text


def _money(value):
    return f"R$ {float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _load_logo(logo_url):
    url = (logo_url or "").strip()
    if not url:
        return None
    try:
        if url.startswith("http://") or url.startswith("https://"):
            with urlopen(url, timeout=5) as response:
                return ImageReader(io.BytesIO(response.read()))
    except Exception:
        return None
    return None

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
    settings_rows = conn.execute(
        "SELECT setting_key, setting_value FROM account_settings WHERE account_id = %s "
        "AND setting_key IN ('po_company_name', 'po_logo_url', 'po_footer_notes', 'po_signature_label')",
        (account_id,),
    ).fetchall()
    settings = {row['setting_key']: row['setting_value'] for row in settings_rows}
    conn.close()
    if not po:
        return "Pedido não encontrado", 404

    company_name = (settings.get('po_company_name') or session.get('account_name') or 'Kdc Systems').strip()
    footer_notes = (settings.get('po_footer_notes') or '').strip()
    signature_label = (settings.get('po_signature_label') or '').strip()
    logo_reader = _load_logo(settings.get('po_logo_url'))

    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4

    x = 36
    y = height - 42
    content_width = width - 72
    total = float(po['quantity'] or 0) * float(po['unit_cost'] or 0)

    if logo_reader:
        try:
            c.drawImage(logo_reader, x, y - 28, width=110, height=28, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFont('Helvetica-Bold', 16)
    c.drawRightString(width - 36, y, company_name)
    c.setFont('Helvetica-Bold', 14)
    c.setFillColor(colors.HexColor('#123f86'))
    c.drawString(x, y - 42, f"PEDIDO DE COMPRA #{po['id']}")
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 10)
    c.drawString(x, y - 58, f"Data de emissão: {_format_date_br(po['created_at'])}")

    # Bloco fornecedor
    supplier_box_top = y - 76
    c.roundRect(x, supplier_box_top - 74, content_width, 70, 6, stroke=1, fill=0)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(x + 8, supplier_box_top - 14, 'Dados do fornecedor')
    c.setFont('Helvetica', 10)
    c.drawString(x + 8, supplier_box_top - 30, f"Nome: {po['supplier_name'] or '-'}")
    c.drawString(x + 8, supplier_box_top - 44, f"CNPJ: {po['supplier_cnpj'] or '-'}")
    c.drawString(x + 8, supplier_box_top - 58, f"E-mail: {po['supplier_email'] or '-'}")
    c.drawRightString(x + content_width - 8, supplier_box_top - 58, f"Telefone: {po['supplier_phone'] or '-'}")

    # Cabeçalho da tabela
    table_top = supplier_box_top - 96
    c.setFillColor(colors.HexColor('#e8effa'))
    c.rect(x, table_top, content_width, 20, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(x + 8, table_top + 6, 'Produto')
    c.drawString(x + 300, table_top + 6, 'Quantidade')
    c.drawString(x + 390, table_top + 6, 'Valor unitário')
    c.drawString(x + 500, table_top + 6, 'Total')

    # Linha de item
    row_y = table_top - 22
    c.setFont('Helvetica', 10)
    c.drawString(x + 8, row_y + 6, po['product_name'] or '-')
    c.drawString(x + 300, row_y + 6, f"{float(po['quantity'] or 0):.3f}")
    c.drawString(x + 390, row_y + 6, _money(po['unit_cost']))
    c.drawString(x + 500, row_y + 6, _money(total))
    c.roundRect(x, row_y, content_width, 20, 2, stroke=1, fill=0)

    # Totais e dados complementares
    details_y = row_y - 30
    c.setFont('Helvetica-Bold', 11)
    c.drawRightString(x + content_width, details_y, f"Total do pedido: {_money(total)}")
    c.setFont('Helvetica', 10)
    c.drawString(x, details_y - 18, f"Parcelas: {po['installments'] or 1}")
    c.drawString(x + 120, details_y - 18, f"1º vencimento: {_format_date_br(po['first_due_date'])}")
    c.drawString(x + 320, details_y - 18, f"Previsão de entrega: {_format_date_br(po['expected_date'])}")
    c.drawRightString(x + content_width, details_y - 18, f"Status: {(po['status'] or '-').capitalize()}")

    notes_text = (po['notes'] or '').strip() or footer_notes
    notes_y = details_y - 44
    c.setFont('Helvetica-Bold', 10)
    c.drawString(x, notes_y, 'Observações:')
    c.setFont('Helvetica', 10)
    c.drawString(x + 72, notes_y, notes_text if notes_text else '-')

    if signature_label:
        sign_y = notes_y - 56
        c.line(x + 340, sign_y, x + content_width, sign_y)
        c.setFont('Helvetica', 9)
        c.drawRightString(x + content_width, sign_y - 12, signature_label)

    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#475569'))
    c.drawString(x, 24, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} pelo Mini ERP")

    c.showPage()
    c.save()
    output.seek(0)
    filename = f"pedido_compra_{po['id']}.pdf"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

