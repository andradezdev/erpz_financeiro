import qrcode
from io import BytesIO
import base64

def crc16_ccitt(payload: str) -> str:
    """Calcula o CRC16-CCITT (0xFFFF) no padrão EMVCo do Banco Central do Brasil"""
    crc = 0xFFFF
    for char in payload:
        crc ^= (ord(char) << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def gerar_payload_pix(chave_pix: str, valor: float, nome_beneficiario: str, cidade: str, txid: str = "***") -> str:
    """Monta o Payload oficial do PIX (Padrão BR Code / Banco Central)"""
    def fmt(id_str, val):
        return f"{id_str}{len(val):02d}{val}"

    # 00: Payload Format Indicator
    p00 = fmt("00", "01")
    # 01: Point of Initiation Method (11: Estático, 12: Dinâmico)
    p01 = fmt("01", "12" if txid != "***" else "11")

    # 26: Merchant Account Information (GUI + Chave)
    gui = fmt("00", "br.gov.bcb.pix")
    key = fmt("01", chave_pix)
    p26 = fmt("26", gui + key)

    # 52: Merchant Category Code
    p52 = fmt("52", "0000")
    # 53: Transaction Currency (986 = BRL)
    p53 = fmt("53", "986")
    # 54: Transaction Amount
    p54 = fmt("54", f"{valor:.2f}") if valor and valor > 0 else ""
    # 58: Country Code
    p58 = fmt("58", "BR")
    # 59: Merchant Name
    nome_clean = (nome_beneficiario or "BENEFICIARIO")[:25].upper()
    p59 = fmt("59", nome_clean)
    # 60: Merchant City
    cidade_clean = (cidade or "SAO PAULO")[:15].upper()
    p60 = fmt("60", cidade_clean)
    # 62: Additional Data Field (txid)
    tx_clean = txid[:25] if txid else "***"
    p62 = fmt("62", fmt("05", tx_clean))

    payload_sem_crc = f"{p00}{p01}{p26}{p52}{p53}{p54}{p58}{p59}{p60}{p62}6304"
    crc = crc16_ccitt(payload_sem_crc)
    return f"{payload_sem_crc}{crc}"

def gerar_qrcode_pix_png(payload: str) -> bytes:
    """Gera a imagem PNG do QR Code PIX"""
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
