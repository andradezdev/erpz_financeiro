import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate
from erpz_financeiro.services.boleto import montar_codigo_barras, montar_linha_digitavel, gerar_pdf_boleto
from erpz_financeiro.services.pix import gerar_payload_pix

class BoletoBancario(Document):
    def validate(self):
        self.preencher_dados_pagador()
        if not self.nosso_numero:
            self.gerar_nosso_numero()
        self.calcular_codigo_barras_e_linha()
        self.gerar_pix_hibrido()

    def preencher_dados_pagador(self):
        if self.cliente and not self.pagador_nome:
            cust = frappe.get_doc("Customer", self.cliente)
            self.pagador_nome = cust.customer_name or cust.name
            self.pagador_documento = cust.get("tax_id") or ""
            # Puxa endereço se houver
            addr_name = frappe.db.get_value("Dynamic Link", {"parenttype": "Address", "link_doctype": "Customer", "link_name": self.cliente}, "parent")
            if addr_name:
                addr = frappe.get_doc("Address", addr_name)
                self.pagador_endereco = f"{addr.address_line1 or ''} {addr.address_line2 or ''}".strip()
                self.pagador_bairro = addr.address_line2 or "CENTRO"
                self.pagador_cidade = addr.city or "SAO PAULO"
                self.pagador_uf = addr.state or "SP"
                self.pagador_cep = addr.pincode or "00000000"

    def gerar_nosso_numero(self):
        if not self.conta_bancaria:
            return
        conta = frappe.get_doc("Configuracao Conta Bancaria", self.conta_bancaria)
        num = conta.proximo_nosso_numero or 1
        self.nosso_numero = str(num).zfill(8)
        self.carteira = conta.carteira or "109"
        conta.db_set("proximo_nosso_numero", num + 1)

    def calcular_codigo_barras_e_linha(self):
        if not self.conta_bancaria or not self.valor_documento:
            return
        conta = frappe.get_doc("Configuracao Conta Bancaria", self.conta_bancaria)
        banco = conta.banco_codigo or "001"
        data_venc = getdate(self.data_vencimento) if self.data_vencimento else getdate(nowdate())

        # Campo Livre padrão: Carteira (3) + Nosso Número (8) + Agência (4) + Conta (7) + Zero (3)
        ag = str(conta.agencia or "0").zfill(4)[:4]
        cc = str(conta.conta_corrente or "0").zfill(7)[:7]
        nn = str(self.nosso_numero or "1").zfill(8)[:8]
        cart = str(self.carteira or "109").zfill(3)[:3]
        campo_livre = f"{cart}{nn}{ag}{cc}000"

        cb = montar_codigo_barras(banco, "9", data_venc, flt(self.valor_documento), campo_livre)
        self.codigo_barras = cb
        self.linha_digitavel = montar_linha_digitavel(cb)

    def gerar_pix_hibrido(self):
        if not self.conta_bancaria:
            return
        conta = frappe.get_doc("Configuracao Conta Bancaria", self.conta_bancaria)
        if conta.chave_pix:
            empresa_nome = frappe.db.get_value("Company", self.empresa, "company_name") or self.empresa
            self.qr_code_pix = gerar_payload_pix(
                chave_pix=conta.chave_pix,
                valor=flt(self.valor_documento),
                nome_beneficiario=conta.nome_beneficiario_pix or empresa_nome,
                cidade=conta.cidade_pix or "SAO PAULO",
                txid=self.nosso_numero or "BOL001"
            )

    @frappe.whitelist()
    def baixar_boleto_pdf(self):
        """Retorna o PDF do boleto bancário formatado"""
        conta = frappe.get_doc("Configuracao Conta Bancaria", self.conta_bancaria)
        comp = frappe.get_doc("Company", self.empresa)
        self.banco_nome = conta.banco_nome
        self.beneficiario_nome = comp.company_name or comp.name
        self.beneficiario_cnpj = comp.tax_id or conta.get("cnpj") or "18.594.769/0001-40"
        self.agencia = f"{conta.agencia}-{conta.digito_agencia or '0'}"
        self.conta_corrente = f"{conta.conta_corrente}-{conta.digito_conta or '0'}"

        pdf_bytes = gerar_pdf_boleto(self)
        frappe.local.response["filename"] = f"Boleto_{self.nosso_numero or self.name}.pdf"
        frappe.local.response["filecontent"] = pdf_bytes
        frappe.local.response["type"] = "download"

    @frappe.whitelist()
    def registrar_liquidacao(self, valor_pago=None, data_pagamento=None):
        """Registra a liquidação e cria automaticamente o Payment Entry no ERPNext"""
        self.status = "Liquidado / Pago"
        self.valor_pago = flt(valor_pago) or flt(self.valor_documento)
        self.data_pagamento = getdate(data_pagamento) or getdate(nowdate())
        self.save(ignore_permissions=True)

        if self.fatura_origem:
            # Cria Payment Entry para baixar a fatura
            from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
            pe = get_payment_entry("Sales Invoice", self.fatura_origem)
            pe.received_amount = self.valor_pago
            pe.posting_date = self.data_pagamento
            pe.reference_no = f"Boleto {self.nosso_numero}"
            pe.reference_date = self.data_pagamento
            pe.insert(ignore_permissions=True)
            pe.submit()

        frappe.db.commit()
        return {"success": True, "message": "Boleto liquidado e fatura baixada no ERPNext!"}


@frappe.whitelist()
def baixar_boleto_pdf(docname=None, boleto=None):
    """Gera e faz o download direto do Boleto Bancário em PDF"""
    name = docname or boleto or frappe.form_dict.get("docname") or frappe.form_dict.get("boleto")
    if not name:
        frappe.throw(_("Boleto Bancário não informado."))

    bol_doc = frappe.get_doc("Boleto Bancario", name)
    conta = frappe.get_doc("Configuracao Conta Bancaria", bol_doc.conta_bancaria)
    comp = frappe.get_doc("Company", bol_doc.empresa)
    bol_doc.banco_nome = conta.banco_nome
    bol_doc.beneficiario_nome = comp.company_name or comp.name
    bol_doc.beneficiario_cnpj = comp.tax_id or conta.get("cnpj") or "18.594.769/0001-40"
    bol_doc.agencia = f"{conta.agencia}-{conta.digito_agencia or '0'}"
    bol_doc.conta_corrente = f"{conta.conta_corrente}-{conta.digito_conta or '0'}"

    pdf_bytes = gerar_pdf_boleto(bol_doc)
    frappe.local.response["filename"] = f"Boleto_{bol_doc.nosso_numero or bol_doc.name}.pdf"
    frappe.local.response["filecontent"] = pdf_bytes
    frappe.local.response["type"] = "download"
