from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
import datetime
from app.database import get_db
from app.models import Notification, Transaction, User
from app.controllers.auth_controller import get_current_user, send_email

router = APIRouter(prefix="", tags=["Notifications"])

@router.get("/notifications", response_class=HTMLResponse)
async def view_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notifs = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.id.desc()).all()
    
    # Mark unread as read when page opens
    db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()

    rows = ""
    for n in notifs:
        type_icon = "fa-circle-info text-blue-500" if n.type == "info" else ("fa-circle-check text-emerald-500" if n.type == "success" else "fa-triangle-exclamation text-rose-500")
        rows += f"""
        <div class='p-4 bg-white border border-slate-200 rounded-xl shadow-sm flex items-start gap-3'>
            <i class='fa-solid {type_icon} text-xl mt-0.5'></i>
            <div class='flex-1'>
                <div class='flex justify-between items-center mb-1'>
                    <h4 class='font-bold text-slate-800 text-sm'>{n.title}</h4>
                    <span class='text-[10px] text-slate-400 font-mono'>{n.created_at.strftime('%Y-%m-%d %H:%M')}</span>
                </div>
                <p class='text-xs text-slate-600'>{n.message}</p>
            </div>
        </div>
        """

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <title>Notifications & Reminders - Effutu Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen p-6 font-sans">
        <div class="max-w-3xl mx-auto space-y-6">
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex justify-between items-center">
                <div>
                    <h2 class="text-2xl font-extrabold text-slate-800">Notifications & Alerts Desk</h2>
                    <p class="text-xs text-slate-500">Loan reminders, reservation pick-ups, & account updates</p>
                </div>
                <a href="/dashboard/{current_user.role}" class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-xs rounded-lg transition">
                    Back to Dashboard
                </a>
            </div>

            <div class="space-y-3">
                {rows if rows else "<div class='bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-400 text-xs'>No notifications found.</div>"}
            </div>
        </div>
    </body>
    </html>
    """)

@router.get("/api/notifications/unread-count")
async def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    count = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).count()
    return {"unread_count": count}

def run_daily_reminders(db: Session):
    """Cron task / daily 8am check for due tomorrow & overdue loans"""
    now = datetime.datetime.utcnow()
    tomorrow = now + datetime.timedelta(days=1)

    # 1. Due Tomorrow
    due_tomorrow_txs = db.query(Transaction).filter(
        Transaction.return_date.is_(None),
        Transaction.due_date >= now,
        Transaction.due_date <= tomorrow
    ).all()

    for t in due_tomorrow_txs:
        if t.patron:
            book_title = t.book_copy.book.title if (t.book_copy and t.book_copy.book) else "Borrowed Book"
            branch_name = t.patron.branch.name if t.patron.branch else "Effutu Library"
            
            # Check if notification already exists for today
            existing = db.query(Notification).filter(
                Notification.user_id == t.patron_id,
                Notification.title == "Book Due Tomorrow! ⏳"
            ).first()

            if not existing:
                notif = Notification(
                    user_id=t.patron_id,
                    title="Book Due Tomorrow! ⏳",
                    message=f"Hi {t.patron.full_name}, book '{book_title}' is due tomorrow {t.due_date.strftime('%Y-%m-%d')}. Please return to {branch_name}.",
                    type="warning"
                )
                db.add(notif)
                db.commit()

                if t.patron.email:
                    send_email(
                        t.patron.email,
                        f"Book Due Tomorrow: '{book_title}'",
                        f"<p>Hi {t.patron.full_name}, book <b>'{book_title}'</b> is due tomorrow {t.due_date.strftime('%Y-%m-%d')}. Please return to {branch_name}.</p>"
                    )
