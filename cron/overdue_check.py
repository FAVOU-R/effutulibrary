import sys
import os
from datetime import datetime

# Add parent directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Transaction, Notification
from app.config import settings
from app.services.email_service import send_overdue_email

def run_overdue_check():
    """
    Overdue Detection Cron Job (Runs daily at 7 AM UTC).
    Identifies past due books, calculates fines at GHS 0.50/day,
    creates in-app notifications, and sends Brevo email notices.
    """
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Starting Effutu Municipal Library Daily Overdue Detection Cron...")
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Find active transactions that are past due
        overdue_trans = db.query(Transaction).filter(
            Transaction.status.in_(["active", "overdue"]),
            Transaction.due_date < now
        ).all()

        processed_count = 0
        email_count = 0

        for trans in overdue_trans:
            trans.status = "overdue"
            overdue_days = (now - trans.due_date).days or 1
            fine = round(overdue_days * settings.DAILY_FINE_GHS, 2)
            trans.fine_amount = fine

            # Create notification if not already created today
            existing_notif = db.query(Notification).filter(
                Notification.user_id == trans.patron_id,
                Notification.title == "OVERDUE BOOK NOTICE"
            ).first()

            if not existing_notif:
                notif = Notification(
                    user_id=trans.patron_id,
                    title="OVERDUE BOOK NOTICE",
                    message=f"Your loan of '{trans.book_copy.book.title}' is overdue. Fine: GHS {fine:.2f}",
                    type="danger"
                )
                db.add(notif)

            # Send Email via Brevo
            if trans.patron.email:
                send_overdue_email(
                    to_email=trans.patron.email,
                    full_name=trans.patron.full_name,
                    book_title=trans.book_copy.book.title,
                    due_date=trans.due_date.strftime("%Y-%m-%d"),
                    fine_ghs=fine
                )
                email_count += 1

            processed_count += 1

        db.commit()
        print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Cron Completed Successfully. Processed {processed_count} overdue loans, sent {email_count} Brevo email notifications.")
    except Exception as e:
        db.rollback()
        print(f"[CRON ERROR] Failed overdue detection run: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_overdue_check()
