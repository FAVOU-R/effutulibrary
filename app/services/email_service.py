import os
import smtplib
import threading
from email.mime.text import MIMEText

def send_email_sync(to_email: str, subject: str, body_html: str) -> bool:
    """Synchronous BREVO SMTP email dispatcher using Port 2525"""
    if not to_email or "@" not in to_email:
        print(f"[BREVO EMAIL CANCELLED] Invalid recipient address: {to_email}")
        return False

    try:
        smtp_server = os.getenv("BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
        smtp_port = int(os.getenv("BREVO_SMTP_PORT", "2525"))
        smtp_login = os.getenv("BREVO_SMTP_LOGIN", "b428a1001@smtp-brevo.com")
        smtp_key = os.getenv("BREVO_SMTP_KEY", "").strip()
        sender_email = os.getenv("BREVO_SENDER_EMAIL", "effutulibrarynetwork@gmail.com")
        sender_name = os.getenv("BREVO_SENDER_NAME", "Effutu Municipal Library")

        if not smtp_key:
            print(f"[BREVO EMAIL NOT SENT] Missing BREVO_SMTP_KEY for {to_email}. Please set BREVO_SMTP_KEY in Render Environment Variables.")
            return False

        msg = MIMEText(body_html, 'html')
        msg['Subject'] = subject
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = to_email

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.starttls()
        server.login(smtp_login, smtp_key)
        server.send_message(msg)
        server.quit()
        print(f"[BREVO EMAIL DISPATCH SUCCESS] Sent email to {to_email} via {smtp_server}:{smtp_port}")
        return True
    except Exception as e:
        print(f"[BREVO EMAIL DISPATCH ERROR] Failed to send email to {to_email}: {e}")
        return False

def send_email(to_email: str, subject: str, body_html: str) -> bool:
    """Non-blocking asynchronous BREVO email dispatcher"""
    threading.Thread(target=send_email_sync, args=(to_email, subject, body_html), daemon=True).start()
    return True
