from datetime import datetime

class CNAB240Generator:
    """Gerador de Arquivo de Remessa Febraban CNAB 240 (240 posicoes)"""
    def __init__(self, conta_doc):
        self.conta = conta_doc
        self.linhas = []

    def gerar_arquivo(self, boletos_list, sequencial_remessa=1) -> str:
        self.linhas = []
        agora = datetime.now()
        dt_str = agora.strftime("%d%m%Y")
        hr_str = agora.strftime("%H%M%S")

        banco = str(self.conta.banco[:3]).zfill(3)
        cnpj_clean = self.conta.cnpj.replace(".", "").replace("-", "").replace("/", "").zfill(14)
        convenio = str(self.conta.codigo_beneficiario or "").ljust(20)
        agencia = str(self.conta.agencia or "0").zfill(5)
        conta = str(self.conta.conta_corrente or "0").zfill(12)
        dig_conta = str(self.conta.digito_conta or "0")[:1]
        empresa_nome = str(self.conta.empresa or "EMPRESA")[:30].ljust(30)
        banco_nome = str(self.conta.banco_nome or "BANCO")[:30].ljust(30)
        seq_rem = str(sequencial_remessa).zfill(6)

        # 1. Header de Arquivo
        p1 = banco + "00000" + (" " * 9) + "2" + cnpj_clean + convenio + agencia + " " + conta + dig_conta + " " + empresa_nome + banco_nome + (" " * 10) + "1" + dt_str + hr_str + seq_rem + "08401600" + (" " * 69)
        self.linhas.append(p1[:240].ljust(240))

        # 2. Header de Lote
        p2 = banco + "00011R01  040 2" + cnpj_clean + convenio + agencia + " " + conta + dig_conta + " " + empresa_nome + (" " * 80) + seq_rem + dt_str + "00000000" + (" " * 33)
        self.linhas.append(p2[:240].ljust(240))

        # 3. Detalhes (Segmento P e Segmento Q)
        seq_reg = 1
        tot_valor = 0.0
        for b in boletos_list:
            v_cents = int(round(b.valor_documento * 100))
            tot_valor += b.valor_documento
            dt_venc_str = b.data_vencimento.strftime("%d%m%Y") if b.data_vencimento else dt_str
            nosso_num = str(b.nosso_numero)[:20].ljust(20)
            carteira = str(b.carteira or "1")[:1]
            num_doc = str(b.numero_documento or b.name)[:15].ljust(15)

            # Segmento P
            p_seg = banco + "00013" + f"{seq_reg:05d}" + "P 01" + agencia + " " + conta + dig_conta + " " + nosso_num + carteira + "1122" + num_doc + dt_venc_str + f"{v_cents:015d}" + "00000 02N" + dt_str + "100000000" + ("0" * 45) + num_doc + "105000009" + ("0" * 10) + " "
            self.linhas.append(p_seg[:240].ljust(240))
            seq_reg += 1

            # Segmento Q
            doc_sacado = b.pagador_documento.replace(".", "").replace("-", "").replace("/", "").zfill(14)
            tp_sac = "2" if len(doc_sacado) > 11 else "1"
            nome_sac = str(b.pagador_nome or "PAGADOR")[:40].ljust(40)
            end_sac = str(b.pagador_endereco or "ENDERECO")[:40].ljust(40)
            bairro_sac = str(b.pagador_bairro or "CENTRO")[:15].ljust(15)
            cep_sac = str(b.pagador_cep or "00000000").replace("-", "")[:8].zfill(8)
            cid_sac = str(b.pagador_cidade or "SAO PAULO")[:15].ljust(15)
            uf_sac = str(b.pagador_uf or "SP")[:2]

            q_seg = banco + "00013" + f"{seq_reg:05d}" + "Q 01" + tp_sac + doc_sacado + nome_sac + end_sac + bairro_sac + cep_sac + cid_sac + uf_sac + "0" + ("0" * 15) + (" " * 40) + "000" + (" " * 28)
            self.linhas.append(q_seg[:240].ljust(240))
            seq_reg += 1

        # 4. Trailer de Lote
        qtd_registros_lote = len(self.linhas)
        v_tot_cents = int(round(tot_valor * 100))
        t_lote = banco + "00015" + (" " * 9) + f"{qtd_registros_lote:06d}" + f"{len(boletos_list):06d}" + f"{v_tot_cents:017d}" + ("0" * 54) + (" " * 145)
        self.linhas.append(t_lote[:240].ljust(240))

        # 5. Trailer de Arquivo
        qtd_linhas_totais = len(self.linhas) + 1
        t_arq = banco + "99999" + (" " * 9) + "000001" + f"{qtd_linhas_totais:06d}" + "000000" + (" " * 205)
        self.linhas.append(t_arq[:240].ljust(240))

        return "\r\n".join(self.linhas) + "\r\n"
