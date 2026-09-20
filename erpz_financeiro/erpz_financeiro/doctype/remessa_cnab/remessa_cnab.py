import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, getdate
from erpz_financeiro.services.cnab240 import CNAB240Generator
from erpz_financeiro.services.cnab400 import CNAB400Generator

class RemessaCNAB(Document):
    @frappe.whitelist()
    def gerar_arquivo_remessa(self):
        if not self.boletos:
            frappe.throw(_("Nenhum boleto selecionado para inclusão na remessa."))

        conta = frappe.get_doc("Configuracao Conta Bancaria", self.conta_bancaria)
        comp = frappe.get_doc("Company", self.empresa)
        conta.cnpj = comp.tax_id or "18.594.769/0001-40"

        boletos_docs = [frappe.get_doc("Boleto Bancario", b.boleto) for b in self.boletos]
        seq = conta.sequencial_remessa_atual or 1
        self.sequencial_remessa = seq
        self.data_geracao = getdate(nowdate())
        self.padrao_cnab = conta.padrao_cnab
        self.quantidade_titulos = len(boletos_docs)
        self.valor_total = sum(b.valor_documento for b in boletos_docs)

        if "240" in str(conta.padrao_cnab):
            gen = CNAB240Generator(conta)
            txt = gen.gerar_arquivo(boletos_docs, sequencial_remessa=seq)
        else:
            gen = CNAB400Generator(conta)
            txt = gen.gerar_arquivo(boletos_docs, sequencial_remessa=seq)

        self.conteudo_arquivo = txt

        # Cria anexo .REM
        banco_cod = conta.banco_codigo or "001"
        file_name = f"CB{banco_cod}_{seq:04d}.REM"
        _file = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "attached_to_doctype": self.doctype,
            "attached_to_name": self.name,
            "content": txt,
            "is_private": 1
        })
        _file.insert(ignore_permissions=True)
        self.arquivo_remessa = _file.file_url

        # Atualiza status dos boletos
        for b in boletos_docs:
            b.db_set("status", "Remessa Gerada")

        conta.db_set("sequencial_remessa_atual", seq + 1)
        self.save(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True, "file_url": self.arquivo_remessa, "file_name": file_name}
