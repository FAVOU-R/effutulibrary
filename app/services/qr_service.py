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
    if not QR_AVAILABLE or qrcode is None:
        return "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='150' height='150'><rect width='150' height='150' fill='%23f1f5f9'/><text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' font-size='12' fill='%2364748b'>QR Code Placeholder</text></svg>"

    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(qr_token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#14532d", back_color="#ffffff")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"[QR GENERATION WARNING] {e}")
        return "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='150' height='150'><rect width='150' height='150' fill='%23f1f5f9'/><text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' font-size='12' fill='%2364748b'>QR Code</text></svg>"
