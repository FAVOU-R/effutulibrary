import io
import base64
import uuid

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    qrcode = None
    QR_AVAILABLE = False

def generate_qr_token(book_id: int, branch_id: int) -> str:
    """Generates a unique QR Token string for a book copy"""
    unique_suffix = str(uuid.uuid4())[:8].upper()
    return f"EFF-LIB-B{book_id}-BR{branch_id}-{unique_suffix}"

def generate_qr_code_base64(qr_token: str) -> str:
    """Generates base64 encoded PNG data URI of QR Code for embedding in UI"""
    token_clean = (qr_token or "EFF-LIB-TOKEN").replace('<', '').replace('>', '').replace('"', '')
    if not QR_AVAILABLE or qrcode is None:
        return f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'><rect width='200' height='200' fill='%23ffffff' rx='12'/><rect x='15' y='15' width='50' height='50' fill='%23047857' rx='4'/><rect x='25' y='25' width='30' height='30' fill='%23ffffff' rx='2'/><rect x='30' y='30' width='20' height='20' fill='%23047857' rx='1'/><rect x='135' y='15' width='50' height='50' fill='%23047857' rx='4'/><rect x='145' y='25' width='30' height='30' fill='%23ffffff' rx='2'/><rect x='150' y='30' width='20' height='20' fill='%23047857' rx='1'/><rect x='15' y='135' width='50' height='50' fill='%23047857' rx='4'/><rect x='25' y='145' width='30' height='30' fill='%23ffffff' rx='2'/><rect x='30' y='150' width='20' height='20' fill='%23047857' rx='1'/><rect x='80' y='80' width='40' height='40' fill='%23047857' rx='4'/><text x='100' y='155' dominant-baseline='middle' text-anchor='middle' font-size='8' font-family='sans-serif' font-weight='bold' fill='%23064e3b'>{token_clean}</text></svg>"

    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(qr_token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#047857", back_color="#ffffff")
        buffered = io.BytesIO()
        img.save(buffered)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"[QR GENERATION WARNING] {e}")
        return f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'><rect width='200' height='200' fill='%23ffffff' rx='12'/><rect x='15' y='15' width='50' height='50' fill='%23047857' rx='4'/><rect x='135' y='15' width='50' height='50' fill='%23047857' rx='4'/><rect x='15' y='135' width='50' height='50' fill='%23047857' rx='4'/><text x='100' y='110' dominant-baseline='middle' text-anchor='middle' font-size='8' font-family='sans-serif' font-weight='bold' fill='%23064e3b'>{token_clean}</text></svg>"
