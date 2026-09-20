from datetime import date, datetime
from io import BytesIO
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.graphics.shapes import Drawing, Rect
import qrcode

def calcular_fator_vencimento(data_venc):
    """Calcula o Fator de Vencimento Febraban padrão"""
    if not data_venc:
        return "0000"
    base = date(1997, 10, 7)
    delta = (data_venc - base).days
    if delta > 9999:
        base2 = date(2025, 2, 22)
        delta = (data_venc - base2).days + 1000
    return f"{delta:04d}"

def modulo10(num_str: str) -> int:
    """Cálculo do Módulo 10 para os blocos da Linha Digitável"""
    soma = 0
    peso = 2
    for d in reversed(num_str):
        p = int(d) * peso
        soma += (p if p < 10 else (p // 10 + p % 10))
        peso = 1 if peso == 2 else 2
    resto = soma % 10
    return 0 if resto == 0 else (10 - resto)

def modulo11_banco(num_str: str, base_max: int = 9) -> int:
    """Cálculo do Módulo 11 para o Dígito Verificador Geral do Código de Barras"""
    soma = 0
    peso = 2
    for d in reversed(num_str):
        soma += int(d) * peso
        peso += 1
        if peso > base_max:
            peso = 2
    resto = soma % 11
    dv = 11 - resto
    if dv in (0, 10, 11):
        return 1
    return dv

def montar_codigo_barras(banco: str, moeda: str, data_venc, valor: float, campo_livre: str) -> str:
    """Monta os 44 dígitos do Código de Barras Febraban"""
    bc = banco[:3].zfill(3)
    moeda_str = "9"
    fator = calcular_fator_vencimento(data_venc)
    v_centavos = f"{int(round(valor * 100)):010d}"
    cl = campo_livre[:25].zfill(25)

    pre_cod = f"{bc}{moeda_str}{fator}{v_centavos}{cl}"
    dv_geral = modulo11_banco(pre_cod)
    return f"{bc}{moeda_str}{dv_geral}{fator}{v_centavos}{cl}"

def montar_linha_digitavel(codigo_barras_44: str) -> str:
    """Gera a Linha Digitável (47 dígitos) com os DVs dos campos"""
    cb = codigo_barras_44
    if len(cb) != 44:
        return ""
    # Campo 1: pos 1 a 4 + pos 20 a 24 + DV
    c1 = f"{cb[0:4]}{cb[19:24]}"
    dv1 = modulo10(c1)
    f1 = f"{c1[:5]}.{c1[5:]}{dv1}"

    # Campo 2: pos 25 a 34 + DV
    c2 = cb[24:34]
    dv2 = modulo10(c2)
    f2 = f"{c2[:5]}.{c2[5:]}{dv2}"

    # Campo 3: pos 35 a 44 + DV
    c3 = cb[34:44]
    dv3 = modulo10(c3)
    f3 = f"{c3[:5]}.{c3[5:]}{dv3}"

    # Campo 4: DV Geral (pos 5)
    f4 = cb[4]

    # Campo 5: Fator (pos 6 a 9) + Valor (pos 10 a 19)
    f5 = f"{cb[5:9]}{cb[9:19]}"

    return f"{f1} {f2} {f3} {f4} {f5}"

def gerar_pdf_boleto(boleto_doc) -> bytes:
    """Gera o PDF do Boleto Bancário oficial formatado com Ficha de Compensação e QR Code PIX"""
    width = 210 * mm
    height = 297 * mm
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=(width, height))

    # Desenho da Ficha do Boleto
    y = height - 20 * mm
    p.setFont("Helvetica-Bold", 12)
    p.drawString(15 * mm, y, f"Boleto Bancário - {boleto_doc.banco_nome or 'Cobrança Bancária'}")
    y -= 8 * mm

    p.setFont("Helvetica", 9)
    p.drawString(15 * mm, y, f"Beneficiário: {boleto_doc.beneficiario_nome} (CNPJ: {boleto_doc.beneficiario_cnpj})")
    y -= 5 * mm
    p.drawString(15 * mm, y, f"Pagador: {boleto_doc.pagador_nome} (CPF/CNPJ: {boleto_doc.pagador_documento})")
    y -= 8 * mm

    # Linha Digitável
    p.setFont("Helvetica-Bold", 11)
    p.drawString(15 * mm, y, f"Linha Digitável: {boleto_doc.linha_digitavel}")
    y -= 10 * mm

    # Tabela com Vencimento, Valor, Nosso Número
    p.setLineWidth(0.5)
    p.rect(15 * mm, y - 25 * mm, 180 * mm, 30 * mm)

    p.setFont("Helvetica", 8)
    p.drawString(18 * mm, y - 5 * mm, "Data de Vencimento:")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(18 * mm, y - 10 * mm, str(boleto_doc.data_vencimento))

    p.setFont("Helvetica", 8)
    p.drawString(75 * mm, y - 5 * mm, "Valor do Documento:")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(75 * mm, y - 10 * mm, f"R$ {boleto_doc.valor_documento:.2f}")

    p.setFont("Helvetica", 8)
    p.drawString(135 * mm, y - 5 * mm, "Nosso Número:")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(135 * mm, y - 10 * mm, str(boleto_doc.nosso_numero))

    p.setFont("Helvetica", 8)
    p.drawString(18 * mm, y - 18 * mm, "Agência / Código Beneficiário:")
    p.setFont("Helvetica-Bold", 9)
    p.drawString(18 * mm, y - 23 * mm, f"{boleto_doc.agencia} / {boleto_doc.conta_corrente}")

    p.setFont("Helvetica", 8)
    p.drawString(75 * mm, y - 18 * mm, "Carteira:")
    p.setFont("Helvetica-Bold", 9)
    p.drawString(75 * mm, y - 23 * mm, str(boleto_doc.carteira or "109"))

    y -= 45 * mm

    # QR Code PIX (Boleto Híbrido)
    if boleto_doc.qr_code_pix:
        p.setFont("Helvetica-Bold", 9)
        p.drawString(15 * mm, y, "Pague com PIX (Boleto Híbrido):")
        y -= 2 * mm

        qr = qrcode.QRCode(box_size=3, border=1)
        qr.add_data(boleto_doc.qr_code_pix)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        qr_buf = BytesIO()
        img.save(qr_buf, format="PNG")
        qr_buf.seek(0)

        p.drawImage(ImageReader(qr_buf), 15 * mm, y - 32 * mm, width=32 * mm, height=32 * mm)
        p.setFont("Helvetica", 7.5)
        p.drawString(52 * mm, y - 10 * mm, "Abra o aplicativo do seu banco, escolha a opção PIX")
        p.drawString(52 * mm, y - 14 * mm, "e aponte a câmera para o QR Code ao lado.")
        y -= 38 * mm

    # Instruções de Caixa
    p.setFont("Helvetica-Bold", 8)
    p.drawString(15 * mm, y, "Instruções de Responsabilidade do Beneficiário:")
    y -= 5 * mm
    p.setFont("Helvetica", 7.5)
    p.drawString(15 * mm, y, "- Não receber após 30 dias do vencimento.")
    y -= 4 * mm
    p.drawString(15 * mm, y, "- Sujeito a protesto após o prazo legal.")
    y -= 10 * mm

    # Representação visual do Código de Barras Febraban
    p.setLineWidth(1.0)
    p.drawString(15 * mm, y, f"Código de Barras: {boleto_doc.codigo_barras}")

    p.showPage()
    p.save()
    return buffer.getvalue()


import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

@frappe.whitelist()
def gerar_boleto_de_fatura(sales_invoice, conta_bancaria, data_vencimento=None):
    """Gera um Boleto Bancario vinculado a uma Sales Invoice do ERPNext"""
    if not sales_invoice:
        frappe.throw(_("Fatura de Venda não informada."))

    inv = frappe.get_doc("Sales Invoice", sales_invoice)
    bol = frappe.new_doc("Boleto Bancario")
    bol.empresa = inv.company
    bol.fatura_origem = inv.name
    bol.conta_bancaria = conta_bancaria
    bol.cliente = inv.customer
    bol.data_emissao = nowdate()
    bol.data_vencimento = getdate(data_vencimento) if data_vencimento else getdate(inv.due_date or nowdate())
    bol.valor_documento = flt(inv.outstanding_amount or inv.grand_total)
    bol.numero_documento = inv.name
    bol.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "boleto": bol.name}
