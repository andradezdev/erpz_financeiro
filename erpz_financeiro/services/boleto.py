from datetime import date, datetime
from io import BytesIO
import qrcode
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import createBarcodeDrawing

# Mapeamento oficial de código e dígitos verificadores dos principais bancos brasileiros
BANCOS_INFO = {
    "001": {"nome": "BANCO DO BRASIL S.A.", "num": "001-9", "carteira_padrao": "17"},
    "033": {"nome": "BANCO SANTANDER (BRASIL) S.A.", "num": "033-7", "carteira_padrao": "101"},
    "104": {"nome": "CAIXA ECONÔMICA FEDERAL", "num": "104-0", "carteira_padrao": "SR"},
    "237": {"nome": "BANCO BRADESCO S.A.", "num": "237-2", "carteira_padrao": "09"},
    "341": {"nome": "BANCO ITAÚ UNIBANCO S.A.", "num": "341-7", "carteira_padrao": "109"},
    "748": {"nome": "BANCO COOPERATIVO SICREDI S.A.", "num": "748-X", "carteira_padrao": "01"},
    "756": {"nome": "BANCOOB / SICOOB", "num": "756-0", "carteira_padrao": "1"},
    "077": {"nome": "BANCO INTER S.A.", "num": "077-9", "carteira_padrao": "101"},
    "260": {"nome": "NU PAGAMENTOS S.A. (NUBANK)", "num": "260-0", "carteira_padrao": "01"}
}

def calcular_fator_vencimento(data_venc):
    if not data_venc:
        return "0000"
    base = date(1997, 10, 7)
    delta = (data_venc - base).days
    if delta > 9999:
        base2 = date(2025, 2, 22)
        delta = (data_venc - base2).days + 1000
    return f"{delta:04d}"

def modulo10(num_str: str) -> int:
    soma = 0
    peso = 2
    for d in reversed(num_str):
        p = int(d) * peso
        soma += (p if p < 10 else (p // 10 + p % 10))
        peso = 1 if peso == 2 else 2
    resto = soma % 10
    return 0 if resto == 0 else (10 - resto)

def modulo11_banco(num_str: str, base_max: int = 9) -> int:
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
    bc = banco[:3].zfill(3)
    moeda_str = "9"
    fator = calcular_fator_vencimento(data_venc)
    v_centavos = f"{int(round(valor * 100)):010d}"
    cl = campo_livre[:25].zfill(25)

    pre_cod = f"{bc}{moeda_str}{fator}{v_centavos}{cl}"
    dv_geral = modulo11_banco(pre_cod)
    return f"{bc}{moeda_str}{dv_geral}{fator}{v_centavos}{cl}"

def montar_linha_digitavel(codigo_barras_44: str) -> str:
    cb = codigo_barras_44
    if len(cb) != 44:
        return ""
    c1 = f"{cb[0:4]}{cb[19:24]}"
    f1 = f"{c1[:5]}.{c1[5:]}{modulo10(c1)}"

    c2 = cb[24:34]
    f2 = f"{c2[:5]}.{c2[5:]}{modulo10(c2)}"

    c3 = cb[34:44]
    f3 = f"{c3[:5]}.{c3[5:]}{modulo10(c3)}"

    f4 = cb[4]
    f5 = f"{cb[5:9]}{cb[9:19]}"

    return f"{f1} {f2} {f3} {f4} {f5}"

def gerar_pdf_boleto(b) -> bytes:
    width = 210 * mm
    height = 297 * mm
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=(width, height))

    banco_cod = str(getattr(b, "banco_codigo", None) or getattr(b, "banco", None) or "341")[:3].zfill(3)
    binfo = BANCOS_INFO.get(banco_cod, {"nome": b.banco_nome or "BANCO", "num": f"{banco_cod}-X"})
    banco_nome = binfo["nome"]
    banco_header = binfo["num"]

    ml = 15 * mm
    mr = 195 * mm
    w_box = 180 * mm
    col_dir = 138 * mm
    w_dir = 57 * mm
    w_esq = 123 * mm

    def desenhar_recibo_ou_ficha(y_top, is_ficha=True):
        p.setStrokeColorRGB(0, 0, 0)
        p.setFillColorRGB(0, 0, 0)

        # Header do Banco
        p.setLineWidth(1.0)
        p.line(ml, y_top, mr, y_top)

        # Logo / Nome Banco
        p.setFont("Helvetica-Bold", 12)
        p.drawString(ml + 2 * mm, y_top - 6 * mm, banco_nome[:28])

        # Caixa com Código do Banco
        p.setLineWidth(1.5)
        p.rect(ml + 68 * mm, y_top - 8 * mm, 18 * mm, 8 * mm)
        p.setFont("Helvetica-Bold", 13)
        p.drawCentredString(ml + 77 * mm, y_top - 6.5 * mm, banco_header)

        # Linha Digitável
        p.setFont("Helvetica-Bold", 10.5)
        linha_dig = b.linha_digitavel or "34191.09008 00000.212340 00567.890009 3 15730000031000"
        p.drawRightString(mr, y_top - 6 * mm, linha_dig)

        y = y_top - 8.5 * mm

        # Grade Principal
        p.setLineWidth(0.5)

        # Linha 1: Local de Pagamento | Vencimento
        p.rect(ml, y - 9 * mm, w_esq, 9 * mm)
        p.rect(col_dir, y - 9 * mm, w_dir, 9 * mm)
        p.setFont("Helvetica", 6)
        p.drawString(ml + 1.5 * mm, y - 2.8 * mm, "LOCAL DE PAGAMENTO")
        p.drawString(col_dir + 1.5 * mm, y - 2.8 * mm, "DATA DE VENCIMENTO")
        p.setFont("Helvetica-Bold", 7.5)
        p.drawString(ml + 1.5 * mm, y - 6.5 * mm, "PAGÁVEL EM QUALQUER BANCO ATÉ O VENCIMENTO")
        p.setFont("Helvetica-Bold", 9)
        dt_venc = b.data_vencimento.strftime("%d/%m/%Y") if hasattr(b.data_vencimento, "strftime") else str(b.data_vencimento)
        p.drawRightString(mr - 2 * mm, y - 6.8 * mm, dt_venc)
        y -= 9 * mm

        # Linha 2: Beneficiário | Agência / Código Beneficiário
        p.rect(ml, y - 9 * mm, w_esq, 9 * mm)
        p.rect(col_dir, y - 9 * mm, w_dir, 9 * mm)
        p.setFont("Helvetica", 6)
        p.drawString(ml + 1.5 * mm, y - 2.8 * mm, "BENEFICIÁRIO")
        p.drawString(col_dir + 1.5 * mm, y - 2.8 * mm, "AGÊNCIA / CÓDIGO BENEFICIÁRIO")
        p.setFont("Helvetica-Bold", 8)
        p.drawString(ml + 1.5 * mm, y - 6.8 * mm, f"{b.beneficiario_nome} - CNPJ: {b.beneficiario_cnpj}")
        p.drawRightString(mr - 2 * mm, y - 6.8 * mm, f"{b.agencia} / {b.conta_corrente}")
        y -= 9 * mm

        # Linha 3: Data Doc | Nº Doc | Espécie Doc | Aceite | Data Proc | Nosso Número
        w_sub = w_esq / 5
        p.rect(ml, y - 9 * mm, w_esq, 9 * mm)
        p.rect(col_dir, y - 9 * mm, w_dir, 9 * mm)
        p.line(ml + w_sub, y, ml + w_sub, y - 9 * mm)
        p.line(ml + w_sub * 2.2, y, ml + w_sub * 2.2, y - 9 * mm)
        p.line(ml + w_sub * 3.1, y, ml + w_sub * 3.1, y - 9 * mm)
        p.line(ml + w_sub * 3.9, y, ml + w_sub * 3.9, y - 9 * mm)

        dt_emi = b.data_emissao.strftime("%d/%m/%Y") if hasattr(b.data_emissao, "strftime") else str(b.data_emissao)
        p.setFont("Helvetica", 5.5)
        p.drawString(ml + 1.5 * mm, y - 2.8 * mm, "DATA DOCUMENTO")
        p.drawString(ml + w_sub + 1.5 * mm, y - 2.8 * mm, "Nº DOCUMENTO")
        p.drawString(ml + w_sub * 2.2 + 1.5 * mm, y - 2.8 * mm, "ESPÉCIE DOC")
        p.drawString(ml + w_sub * 3.1 + 1.5 * mm, y - 2.8 * mm, "ACEITE")
        p.drawString(ml + w_sub * 3.9 + 1.5 * mm, y - 2.8 * mm, "DATA PROCESSAMENTO")
        p.drawString(col_dir + 1.5 * mm, y - 2.8 * mm, "NOSSO NÚMERO")

        p.setFont("Helvetica-Bold", 7.5)
        p.drawString(ml + 1.5 * mm, y - 6.8 * mm, dt_emi)
        p.drawString(ml + w_sub + 1.5 * mm, y - 6.8 * mm, str(b.numero_documento or b.name)[:14])
        p.drawString(ml + w_sub * 2.2 + 1.5 * mm, y - 6.8 * mm, "DM")
        p.drawString(ml + w_sub * 3.1 + 1.5 * mm, y - 6.8 * mm, "N")
        p.drawString(ml + w_sub * 3.9 + 1.5 * mm, y - 6.8 * mm, dt_emi)
        p.setFont("Helvetica-Bold", 8.5)
        p.drawRightString(mr - 2 * mm, y - 6.8 * mm, f"{b.carteira or '109'} / {b.nosso_numero}")
        y -= 9 * mm

        # Linha 4: Uso do Banco | Carteira | Espécie | Quantidade | Valor | (=) Valor do Documento
        p.rect(ml, y - 9 * mm, w_esq, 9 * mm)
        p.rect(col_dir, y - 9 * mm, w_dir, 9 * mm)
        p.line(ml + w_sub, y, ml + w_sub, y - 9 * mm)
        p.line(ml + w_sub * 2, y, ml + w_sub * 2, y - 9 * mm)
        p.line(ml + w_sub * 3, y, ml + w_sub * 3, y - 9 * mm)
        p.line(ml + w_sub * 4, y, ml + w_sub * 4, y - 9 * mm)

        p.setFont("Helvetica", 5.5)
        p.drawString(ml + 1.5 * mm, y - 2.8 * mm, "USO DO BANCO")
        p.drawString(ml + w_sub + 1.5 * mm, y - 2.8 * mm, "CARTEIRA")
        p.drawString(ml + w_sub * 2 + 1.5 * mm, y - 2.8 * mm, "ESPÉCIE MOEDA")
        p.drawString(ml + w_sub * 3 + 1.5 * mm, y - 2.8 * mm, "QUANTIDADE")
        p.drawString(ml + w_sub * 4 + 1.5 * mm, y - 2.8 * mm, "VALOR MOEDA")
        p.drawString(col_dir + 1.5 * mm, y - 2.8 * mm, "(=) VALOR DO DOCUMENTO")

        p.setFont("Helvetica-Bold", 7.5)
        p.drawString(ml + w_sub + 1.5 * mm, y - 6.8 * mm, str(b.carteira or "109"))
        p.drawString(ml + w_sub * 2 + 1.5 * mm, y - 6.8 * mm, "R$")
        p.setFont("Helvetica-Bold", 9.5)
        p.drawRightString(mr - 2 * mm, y - 6.8 * mm, f"R$ {b.valor_documento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        y -= 9 * mm

        # Linha 5: Instruções de Caixa (Esquerda 42mm) x Coluna de Valores (Direita 5 caixas)
        h_inst = 42 * mm
        p.rect(ml, y - h_inst, w_esq, h_inst)
        p.setFont("Helvetica", 6)
        p.drawString(ml + 1.5 * mm, y - 2.8 * mm, "INSTRUÇÕES (Todas as informações deste boleto são de exclusiva responsabilidade do beneficiário)")

        p.setFont("Helvetica", 7.5)
        p.drawString(ml + 2 * mm, y - 7 * mm, "- Cobrar juros de mora de 1,0% ao mês após o vencimento.")
        p.drawString(ml + 2 * mm, y - 11.5 * mm, "- Cobrar multa de 2,0% após o vencimento.")
        p.drawString(ml + 2 * mm, y - 16 * mm, "- Não receber após 30 dias do vencimento.")
        p.drawString(ml + 2 * mm, y - 20.5 * mm, "- Sujeito a protesto após 5 dias úteis do vencimento.")

        # QR Code PIX (Boleto Híbrido) desenhado dentro do quadro de instruções
        if b.qr_code_pix:
            p.setFont("Helvetica-Bold", 7.5)
            p.drawString(ml + 85 * mm, y - 7 * mm, "Pague com PIX:")
            p.setFont("Helvetica", 6)
            p.drawString(ml + 85 * mm, y - 10.5 * mm, "Boleto Híbrido")

            qr = qrcode.QRCode(box_size=3, border=1)
            qr.add_data(b.qr_code_pix)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            qr_buf = BytesIO()
            img_qr.save(qr_buf, format="PNG")
            qr_buf.seek(0)
            p.drawImage(ImageReader(qr_buf), ml + 85 * mm, y - 41 * mm, width=30 * mm, height=30 * mm)

        # Coluna Direita (5 caixas de 8.4mm)
        labels_dir = [
            "(-) DESCONTO / ABATIMENTO",
            "(-) OUTRAS DEDUÇÕES",
            "(+) MORA / MULTA",
            "(+) OUTROS ACRÉSCIMOS",
            "(=) VALOR COBRADO"
        ]
        y_d = y
        for lbl in labels_dir:
            p.rect(col_dir, y_d - 8.4 * mm, w_dir, 8.4 * mm)
            p.setFont("Helvetica", 5.5)
            p.drawString(col_dir + 1.5 * mm, y_d - 2.8 * mm, lbl)
            y_d -= 8.4 * mm

        y -= h_inst

        # Linha 6: Dados do Pagador (Sacado)
        h_sac = 22 * mm
        p.rect(ml, y - h_sac, w_box, h_sac)
        p.setFont("Helvetica", 6)
        p.drawString(ml + 1.5 * mm, y - 2.8 * mm, "PAGADOR")

        p.setFont("Helvetica-Bold", 8)
        p.drawString(ml + 2 * mm, y - 6.5 * mm, f"{b.pagador_nome} - CPF/CNPJ: {b.pagador_documento}")
        p.setFont("Helvetica", 7.5)
        p.drawString(ml + 2 * mm, y - 10.5 * mm, f"{b.pagador_endereco or 'ENDERECO NAO INFORMADO'} - {b.pagador_bairro or 'CENTRO'}")
        p.drawString(ml + 2 * mm, y - 14.5 * mm, f"CEP: {b.pagador_cep or '00000-000'} - {b.pagador_cidade or 'SAO PAULO'}/{b.pagador_uf or 'SP'}")

        p.setFont("Helvetica", 6)
        p.drawString(ml + 2 * mm, y - 19.5 * mm, "Sacador / Avalista:")
        p.drawRightString(mr - 2 * mm, y - 19.5 * mm, "Autenticação Mecânica - Ficha de Compensação" if is_ficha else "Autenticação Mecânica - Recibo do Pagador")
        y -= h_sac

        # Código de Barras I25 Febraban
        if is_ficha and b.codigo_barras and len(b.codigo_barras) == 44:
            d = createBarcodeDrawing("I2of5", value=b.codigo_barras, barWidth=0.254 * mm, barHeight=13 * mm, checksum=False)
            d.drawOn(p, ml, y - 16 * mm)

        return y

    # 1. Recibo do Pagador (Topo da folha A4)
    y_recibo = desenhar_recibo_ou_ficha(height - 15 * mm, is_ficha=False)

    # Linha pontilhada de corte
    y_corte = y_recibo - 10 * mm
    p.setDash(2, 3)
    p.setLineWidth(0.5)
    p.setStrokeColorRGB(0.4, 0.4, 0.4)
    p.line(ml, y_corte, mr, y_corte)
    p.setFont("Helvetica", 6)
    p.setFillColorRGB(0.4, 0.4, 0.4)
    p.drawCentredString(width / 2, y_corte + 1 * mm, "--- Destaque ou corte na linha pontilhada ---")
    p.setDash()

    # 2. Ficha de Compensação Oficial Febraban (Parte inferior)
    desenhar_recibo_ou_ficha(y_corte - 5 * mm, is_ficha=True)

    p.showPage()
    p.save()
    return buffer.getvalue()
