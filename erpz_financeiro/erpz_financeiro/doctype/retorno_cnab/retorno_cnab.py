import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, getdate, flt
from datetime import datetime

class RetornoCNAB(Document):
    @frappe.whitelist()
    def processar_arquivo_retorno(self):
        if not self.arquivo_retorno:
            frappe.throw(_("Nenhum arquivo de retorno anexado."))

        file_doc = frappe.get_doc("File", {"file_url": self.arquivo_retorno})
        raw = file_doc.get_content()
        content = raw if isinstance(raw, str) else raw.decode("latin-1", errors="ignore")
        lines = content.splitlines()

        self.titulos_processados = []
        tot_liquidado = 0.0
        qtd_processados = 0

        for l in lines:
            if len(l) >= 100 and l[7] == "3" and l[13] == "T":
                # CNAB 240 - Segmento T (Identificação do Título)
                nosso_num = l[37:57].strip()
                v_cents = flt(l[81:96]) / 100.0
                dt_str = l[73:81]
                ocorrencia = l[15:17]

                self.append("titulos_processados", {
                    "nosso_numero": nosso_num,
                    "ocorrencia": f"{ocorrencia} - Ocorrência Bancária",
                    "data_ocorrencia": datetime.strptime(dt_str, "%d%m%Y").date() if dt_str.isdigit() else getdate(nowdate()),
                    "valor_titulo": v_cents,
                    "valor_pago": v_cents if ocorrencia in ("06", "05") else 0.0,
                    "status_processamento": "Baixado com Sucesso" if ocorrencia in ("06", "05") else "Pendente"
                })
                if ocorrencia in ("06", "05"):
                    tot_liquidado += v_cents
                    self.liquidar_boleto(nosso_num, v_cents)
                qtd_processados += 1

            elif len(l) >= 100 and l[0] == "1":
                # CNAB 400 - Registro 1 (Detalhe Retorno)
                nosso_num = l[85:93].strip() or l[62:70].strip()
                num_doc = l[116:126].strip()
                ocorrencia = l[108:110]
                v_cents = flt(l[152:165]) / 100.0
                tarifa = flt(l[175:188]) / 100.0 if len(l) >= 188 else 0.0
                dt_str = l[110:116]

                self.append("titulos_processados", {
                    "nosso_numero": nosso_num,
                    "numero_documento": num_doc,
                    "ocorrencia": f"{ocorrencia} - Liquidação" if ocorrencia == "06" else f"{ocorrencia} - Ocorrência",
                    "data_ocorrencia": datetime.strptime(dt_str, "%d%m%y").date() if dt_str.isdigit() and len(dt_str) == 6 else getdate(nowdate()),
                    "valor_titulo": v_cents,
                    "valor_pago": v_cents if ocorrencia == "06" else 0.0,
                    "valor_tarifa": tarifa,
                    "status_processamento": "Baixado com Sucesso" if ocorrencia == "06" else "Pendente"
                })
                if ocorrencia == "06":
                    tot_liquidado += v_cents
                    self.liquidar_boleto(nosso_num, v_cents)
                qtd_processados += 1

        self.data_processamento = getdate(nowdate())
        self.quantidade_titulos = qtd_processados
        self.valor_total_liquidado = tot_liquidado
        self.save(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True, "titulos_processados": qtd_processados, "total_liquidado": tot_liquidado}

    def liquidar_boleto(self, nosso_num, valor_pago):
        bol_name = frappe.db.get_value("Boleto Bancario", {"nosso_numero": nosso_num}, "name")
        if bol_name:
            b = frappe.get_doc("Boleto Bancario", bol_name)
            b.registrar_liquidacao(valor_pago=valor_pago)
