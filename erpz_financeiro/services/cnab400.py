from datetime import datetime

class CNAB400Generator:
    """Gerador de Arquivo de Remessa Febraban CNAB 400 (400 posicoes)"""
    def __init__(self, conta_doc):
        self.conta = conta_doc
        self.linhas = []

    def gerar_arquivo(self, boletos_list, sequencial_remessa=1) -> str:
        self.linhas = []
        agora = datetime.now()
        dt_str = agora.strftime("%d%m%y")

        banco = str(self.conta.banco[:3]).zfill(3)
        agencia = str(self.conta.agencia or "0").zfill(4)
        conta = str(self.conta.conta_corrente or "0").zfill(5)
        dig_conta = str(self.conta.digito_conta or "0")[:1]
        empresa_nome = str(self.conta.empresa or "EMPRESA")[:30].ljust(30)
        banco_nome = str(self.conta.banco_nome or "BANCO")[:15].ljust(15)

        # Header 400
        h_0 = "01REMESSA01COBRANCA       " + agencia + conta + dig_conta + (" " * 8) + empresa_nome + banco + banco_nome + dt_str + (" " * 294) + "000001"
        self.linhas.append(h_0[:400].ljust(400))

        # Detalhes
        seq = 2
        for b in boletos_list:
            v_cents = int(round(b.valor_documento * 100))
            dt_venc_str = b.data_vencimento.strftime("%d%m%y") if b.data_vencimento else dt_str
            nosso_num = str(b.nosso_numero)[:8].zfill(8)
            carteira = str(b.carteira or "109")[:3]
            num_doc = str(b.numero_documento or b.name)[:10].ljust(10)

            doc_sacado = b.pagador_documento.replace(".", "").replace("-", "").replace("/", "").zfill(14)
            tp_sac = "02" if len(doc_sacado) > 11 else "01"
            nome_sac = str(b.pagador_nome or "PAGADOR")[:30].ljust(30)
            end_sac = str(b.pagador_endereco or "ENDERECO")[:40].ljust(40)
            cep_sac = str(b.pagador_cep or "00000000").replace("-", "")[:8].zfill(8)

            r_1 = "102" + (" " * 14) + agencia + conta + dig_conta + (" " * 4) + "0000" + num_doc + nosso_num + ("0" * 13) + carteira + "01" + num_doc + dt_venc_str + f"{v_cents:013d}" + banco + "0000001N" + dt_str + ("0" * 44) + tp_sac + doc_sacado + nome_sac + end_sac + (" " * 12) + cep_sac + (" " * 60) + f"{seq:06d}"
            self.linhas.append(r_1[:400].ljust(400))
            seq += 1

        # Trailer 9
        t_9 = "9" + (" " * 393) + f"{seq:06d}"
        self.linhas.append(t_9[:400].ljust(400))

        return "\r\n".join(self.linhas) + "\r\n"
