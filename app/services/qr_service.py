import qrcode
import io
import base64
import uuid

def generate_qr_token(book_id: int, branch_id: int) -> str:
    """Generates a unique QR Token string for a book copy"""
    unique_suffix = str(uuid.uuid4())[:8].upper()
    return f"EFF-LIB-B{book_id}-BR{branch_id}-{unique_suffix}"

def generate_qr_code_base64(qr_token: str) -> str:
    """Generates base64 encoded PNG data URI of QR Code for embedding in UI"""
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
