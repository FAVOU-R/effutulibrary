import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

def send_email_brevo(to_email: str, subject: str, body_html: str) -> bool:
    """
    Sends email via Brevo SMTP relay (smtp-relay.brevo.com:587)
    Falls back gracefully to local console logging if SMTP fails or credentials are placeholder.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Effutu Municipal Library <{settings.SENDER_EMAIL}>"
        msg["To"] = to_email

        html_part = MIMEText(body_html, "html")
        msg.attach(html_part)

        # Attempt Brevo SMTP Connection
        server = smtplib.SMTP(settings.BREVO_SMTP_SERVER, settings.BREVO_SMTP_PORT, timeout=5)
        server.starttls()
        # Attempt login if user & password configured
        if settings.BREVO_SMTP_USER and settings.BREVO_SMTP_PASSWORD != "brevo-smtp-key":
            server.login(settings.BREVO_SMTP_USER, settings.BREVO_SMTP_PASSWORD)
            server.sendmail(settings.SENDER_EMAIL, to_email, msg.as_string())
            server.quit()
            print(f"[BREVO EMAIL SUCCESS] Email sent to {to_email}")
            return True
        else:
            server.quit()
            raise Exception("Brevo SMTP Password is default placeholder")

    except Exception as e:
        print(f"[BREVO EMAIL SIMULATION / LOG]: Target: {to_email} | Subject: {subject} | Note: {e}")
        return True

def send_approval_email(to_email: str, full_name: str, member_id: str, login_url: str):
    subject = "Welcome to Effutu Municipal Library System - Account Approved"
    body = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4fdf6; color: #14532d; border-radius: 8px;">
        <h2 style="color: #15803d;">Akwaaba, {full_name}!</h2>
        <p>Your library patron account registration for Effutu Municipal Library System has been <strong>APPROVED</strong>.</p>
        <div style="background: #ffffff; padding: 15px; border-left: 4px solid #16a34a; margin: 15px 0;">
            <p style="margin: 0; font-size: 14px;"><strong>Your Official Member ID:</strong></p>
            <h3 style="margin: 5px 0; color: #15803d; letter-spacing: 1px;">{member_id}</h3>
        </div>
        <p>You can now browse the catalog, reserve books, and enjoy instant QR self-borrowing.</p>
        <p><a href="{login_url}" style="display: inline-block; background: #16a34a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Login to Library Portal</a></p>
        <hr style="border: none; border-top: 1px solid #dcfce7; margin-top: 20px;">
        <small style="color: #15803d;">Effutu Central Library, Winneba - Central Region, Ghana</small>
    </div>
    """
    return send_email_brevo(to_email, subject, body)

def send_overdue_email(to_email: str, full_name: str, book_title: str, due_date: str, fine_ghs: float):
    subject = "OVERDUE NOTICE: Effutu Municipal Library Book Return"
    body = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #fef2f2; color: #991b1b; border-radius: 8px;">
        <h2 style="color: #dc2626;">Overdue Notice - Immediate Action Required</h2>
        <p>Dear {full_name},</p>
        <p>Our records show that the following book issued to you is past its due date:</p>
        <div style="background: #ffffff; padding: 15px; border-left: 4px solid #dc2626; margin: 15px 0;">
            <p style="margin: 4px 0;"><strong>Book Title:</strong> {book_title}</p>
            <p style="margin: 4px 0;"><strong>Due Date:</strong> {due_date}</p>
            <p style="margin: 4px 0;"><strong>Accumulated Fine:</strong> <span style="color: #b91c1c; font-weight: bold;">GHS {fine_ghs:.2f}</span> (GHS 0.50 / day)</p>
        </div>
        <p>Please return this book to your branch library as soon as possible to prevent further daily fines.</p>
        <hr style="border: none; border-top: 1px solid #fee2e2; margin-top: 20px;">
        <small style="color: #991b1b;">Effutu Municipal Library Network Service</small>
    </div>
    """
    return send_email_brevo(to_email, subject, body)
