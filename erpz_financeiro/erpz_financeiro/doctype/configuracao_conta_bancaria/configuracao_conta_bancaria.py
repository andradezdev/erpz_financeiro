import frappe
from frappe.model.document import Document

class ConfiguracaoContaBancaria(Document):
    def validate(self):
        if self.banco:
            self.banco_codigo = self.banco[:3]
            self.banco_nome = self.banco[6:].strip()
        if not self.proximo_nosso_numero:
            self.proximo_nosso_numero = 1
        if not self.sequencial_remessa_atual:
            self.sequencial_remessa_atual = 1
