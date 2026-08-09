from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Reservation, Book, User, Notification, UserPoint
from app.controllers.auth_controller import get_current_user, send_email, get_current_user_optional

router = APIRouter(prefix="", tags=["Reservations"])

def require_librarian_or_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["librarian", "sys_admin", "hq_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return current_user

@router.post("/api/reservations/reserve/{book_id}")
async def reserve_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "patron":
        raise HTTPException(status_code=403, detail="Only patrons can reserve books")
    
    # Check max 2 active reservations limit per patron
    active_res_count = db.query(Reservation).filter(
        Reservation.user_id == current_user.id,
        Reservation.status.in_(["reserved", "ready"])
    ).count()

    if active_res_count >= 2:
        return JSONResponse(status_code=400, content={"error": "Maximum reservation limit reached (Max 2 active reservations allowed per patron)."})

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return JSONResponse(status_code=404, content={"error": "Book not found"})

    # Create Reservation
    expires = datetime.utcnow() + timedelta(days=2)
    res = Reservation(
        user_id=current_user.id,
        book_id=book.id,
        status="reserved",
        reserved_at=datetime.utcnow(),
        expires_at=expires
    )
    db.add(res)
    
    # Add notification
    notif = Notification(
        user_id=current_user.id,
        title="Book Reserved 📚",
        message=f"You reserved '{book.title}'. We will notify you when ready at your branch.",
        type="info"
    )
    db.add(notif)
    db.commit()

    return JSONResponse(content={"message": f"Successfully reserved '{book.title}'. Reservation valid for 48 hours."})

@router.get("/api/reservations/my")
async def my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res_list = db.query(Reservation).filter(Reservation.user_id == current_user.id).order_by(Reservation.id.desc()).all()
    return [{
        "id": r.id,
        "book_title": r.book.title if r.book else "Unknown",
        "status": r.status,
        "reserved_at": r.reserved_at.strftime("%Y-%m-%d %H:%M"),
        "expires_at": r.expires_at.strftime("%Y-%m-%d %H:%M") if r.expires_at else "-"
    } for r in res_list]

@router.get("/librarian/reservations", response_class=HTMLResponse)
async def librarian_reservations(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["librarian", "sys_admin", "hq_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    reservations = db.query(Reservation).order_by(Reservation.id.desc()).all()
    rows = ""
    for r in reservations:
        patron_name = r.user.full_name if r.user else "Unknown"
        patron_phone = r.user.phone if r.user else "-"
        branch_name = r.user.branch.name if (r.user and r.user.branch) else "Effutu Main"
        book_title = r.book.title if r.book else "Unknown"
        
        status_colors = {
            "reserved": "bg-amber-100 text-amber-800",
            "ready": "bg-blue-100 text-blue-800",
            "collected": "bg-emerald-100 text-emerald-800",
            "cancelled": "bg-slate-100 text-slate-600",
            "expired": "bg-rose-100 text-rose-800"
        }
        badge = f"<span class='px-3 py-1 text-xs font-black rounded-xl uppercase shadow-sm {status_colors.get(r.status, 'bg-slate-100')}'>{r.status}</span>"

        rows += f"""
        <tr class='border-b border-slate-200 hover:bg-slate-50/90 transition text-xs'>
            <td class='p-4 font-mono font-black text-sm text-emerald-900 whitespace-nowrap'>#RES-{r.id}</td>
            <td class='p-4 min-w-[200px]'>
                <div class='text-sm font-black text-slate-900'>{patron_name}</div>
                <div class='text-xs font-bold text-slate-600 mt-0.5'>{patron_phone} • <span class='text-emerald-800 font-mono'>{branch_name}</span></div>
            </td>
            <td class='p-4 min-w-[220px] font-black text-sm text-slate-900 leading-snug'>{book_title}</td>
            <td class='p-4 whitespace-nowrap font-mono font-bold text-xs text-slate-700'>{r.reserved_at.strftime('%Y-%m-%d %H:%M')}</td>
            <td class='p-4 whitespace-nowrap'>{badge}</td>
            <td class='p-4 space-x-1.5 whitespace-nowrap'>
                {'<form method="post" action="/librarian/reservations/' + str(r.id) + '/status" class="inline"><input type="hidden" name="status" value="ready"><button class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-extrabold rounded-xl text-xs shadow">Mark Ready</button></form>' if r.status == 'reserved' else ''}
                {'<form method="post" action="/librarian/reservations/' + str(r.id) + '/fulfill" class="inline"><button class="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-slate-950 font-black rounded-xl text-xs shadow"><i class="fa-solid fa-hand-holding-hand mr-1"></i> Hand Over</button></form>' if r.status == 'ready' else ''}
                {'<button onclick="rejectRes(' + str(r.id) + ')" class="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-extrabold rounded-xl text-xs shadow">Reject / Cancel</button>' if r.status in ['reserved', 'ready'] else ''}
            </td>
        </tr>
        """

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <title>Manage Book Reservations - Effutu Library System</title>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 sm:p-6 font-sans">
        <div class="max-w-[1536px] mx-auto space-y-6">
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 class="text-2xl font-extrabold text-slate-900 flex items-center gap-2">
                        <i class="fa-solid fa-bookmark text-indigo-600"></i> Book Reservation Desk
                    </h2>
                    <p class="text-xs text-slate-500 font-medium mt-1">Track patron 48-hour hold requests, confirm desk handovers, & manage branch pick-ups</p>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/librarian/loans" class="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs rounded-xl shadow transition flex items-center gap-1">
                        <i class="fa-solid fa-file-invoice"></i> Circulation Desk
                    </a>
                    <a href="/dashboard/{current_user.role}" class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-xs rounded-xl transition">
                        Back to Dashboard
                    </a>
                </div>
            </div>

            <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-100 uppercase text-slate-700 font-black text-xs tracking-wider border-b border-slate-300">
                            <tr>
                                <th class="p-4">Reservation ID</th>
                                <th class="p-4">Patron Details</th>
                                <th class="p-4">Book Title</th>
                                <th class="p-4">Reserved Date</th>
                                <th class="p-4">Status</th>
                                <th class="p-4">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else "<tr><td colspan='6' class='p-12 text-center text-slate-400 font-medium'>No book reservations recorded.</td></tr>"}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
        function rejectRes(id) {{
            const reason = prompt("Enter rejection reason (e.g. Unavailable at branch, Damaged copy, Exceeded hold limit):", "Unavailable at branch");
            if (reason !== null && reason.trim() !== "") {{
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/api/reservations/' + id + '/reject';
                
                const inputReason = document.createElement('input');
                inputReason.type = 'hidden';
                inputReason.name = 'reason';
                inputReason.value = reason;
                form.appendChild(inputReason);

                const inputRejectReason = document.createElement('input');
                inputRejectReason.type = 'hidden';
                inputRejectReason.name = 'reject_reason';
                inputRejectReason.value = reason;
                form.appendChild(inputRejectReason);

                document.body.appendChild(form);
                form.submit();
            }}
        }}
        </script>
    </body>
    </html>
    """)

@router.post("/api/reservations/{res_id}/reject")
@router.post("/librarian/reservations/{res_id}/reject")
async def reject_reservation(
    res_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian_or_admin)
):
    r = db.query(Reservation).filter(Reservation.id == res_id).first()
    if not r:
        if "api" in str(request.url):
            return JSONResponse(status_code=404, content={"error": "Reservation not found"})
        return HTMLResponse("<h3>Reservation not found</h3>", status_code=404)

    reason = "Unavailable at branch"
    try:
        data = await request.json()
        reason = data.get("reason") or data.get("reject_reason") or reason
    except Exception:
        try:
            form = await request.form()
            reason = form.get("reason") or form.get("reject_reason") or reason
        except Exception:
            pass

    print(f"Rejecting reservation {res_id} with reason: {reason}")

    r.status = "rejected"
    r.reject_reason = reason
    db.commit()

    try:
        book_title = r.book.title if r.book else "Reserved Book"
        notif = Notification(
            user_id=r.user_id,
            title="Reservation Declined ❌",
            message=f"Your reservation for '{book_title}' was declined. Reason: {reason}",
            type="warning"
        )
        db.add(notif)
        db.commit()
    except Exception as ex:
        print(f"[REJECTION NOTIF WARNING] {ex}")

    try:
        if r.user and r.user.email:
            send_email(
                r.user.email,
                f"Reservation Declined: '{r.book.title if r.book else 'Book'}'",
                f"<p>Hi {r.user.full_name},</p><p>Your reservation for <b>'{r.book.title if r.book else 'Book'}'</b> was declined.</p><p><b>Reason:</b> {reason}</p><p>Effutu Library Network</p>"
            )
    except Exception as ex:
        print(f"[REJECTION EMAIL WARNING] {ex}")

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(content={"message": "Reservation rejected successfully", "reason": reason})

    return RedirectResponse(url="/librarian/reservations", status_code=303)

@router.post("/librarian/reservations/{res_id}/status")
async def update_reservation_status(
    res_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian_or_admin)
):
    r = db.query(Reservation).filter(Reservation.id == res_id).first()
    if not r:
        return HTMLResponse("<h3>Reservation not found</h3>", status_code=404)

    status = "cancelled"
    reason = None
    try:
        form = await request.form()
        status = form.get("status", "cancelled").strip()
        reason = form.get("reason") or form.get("reject_reason")
    except Exception:
        try:
            data = await request.json()
            status = data.get("status", "cancelled").strip()
            reason = data.get("reason") or data.get("reject_reason")
        except Exception:
            pass

    r.status = status
    if reason:
        r.reject_reason = reason
    db.commit()

    book_title = r.book.title if r.book else "Reserved Book"
    branch_name = r.user.branch.name if (r.user and r.user.branch) else "Effutu Municipal Library"

    if status == "ready":
        try:
            notif = Notification(
                user_id=r.user_id,
                title="Book Ready for Pick Up! 📦",
                message=f"Hi {r.user.full_name}, reserved book '{book_title}' is ready at {branch_name}. Collect within 2 days.",
                type="success"
            )
            db.add(notif)
            db.commit()

            if r.user and r.user.email:
                send_email(
                    r.user.email,
                    f"Reserved Book Ready: '{book_title}'",
                    f"<p>Hi {r.user.full_name}, reserved book <b>'{book_title}'</b> is ready at {branch_name}. Collect within 2 days.</p><p>Effutu Library Network</p>"
                )
        except Exception as ex:
            print(f"[STATUS NOTIF WARNING] {ex}")

    elif status in ["cancelled", "rejected"]:
        print(f"Rejecting reservation {res_id} with reason: {reason}")
        try:
            notif = Notification(
                user_id=r.user_id,
                title="Reservation Declined ❌",
                message=f"Your reservation for '{book_title}' was declined. Reason: {reason or 'Unavailable at branch'}",
                type="warning"
            )
            db.add(notif)
            db.commit()

            if r.user and r.user.email:
                send_email(
                    r.user.email,
                    f"Reservation Declined: '{book_title}'",
                    f"<p>Hi {r.user.full_name},</p><p>Your reservation for <b>'{book_title}'</b> was declined.</p><p><b>Reason:</b> {reason or 'Unavailable'}</p><p>Effutu Library Network</p>"
                )
        except Exception as ex:
            print(f"[REJECT EMAIL WARNING] {ex}")

    elif status == "collected":
        try:
            point = UserPoint(user_id=r.user_id, points=5, reason="Reserved Book Collection Bonus")
            db.add(point)
            db.commit()
        except Exception as ex:
            print(f"[POINT WARNING] {ex}")

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(content={"message": f"Reservation updated to {status}"})

    return RedirectResponse(url="/librarian/reservations", status_code=303)

@router.post("/api/reservations/{res_id}/fulfill")
@router.post("/librarian/reservations/{res_id}/fulfill")
async def fulfill_reservation(
    res_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian_or_admin)
):
    from app.models import Transaction, BookCopy
    from app.config import settings

    r = db.query(Reservation).filter(Reservation.id == res_id).first()
    if not r:
        return JSONResponse(status_code=404, content={"error": "Reservation not found"})

    # Find available copy for this book
    copy = db.query(BookCopy).filter(BookCopy.book_id == r.book_id, BookCopy.status == "available").first()
    if not copy:
        copy = db.query(BookCopy).filter(BookCopy.book_id == r.book_id).first()

    if not copy:
        return JSONResponse(status_code=400, content={"error": "No physical copy available for this book"})

    issue_date = datetime.utcnow()
    due_date = issue_date + timedelta(days=getattr(settings, "LOAN_PERIOD_DAYS", 14))

    # 1. Update copy status to issued
    copy.status = "issued"

    # 2. Record Active Checkout Transaction
    tx = Transaction(
        book_copy_id=copy.id,
        patron_id=r.user_id,
        issued_by_id=current_user.id,
        issue_date=issue_date,
        due_date=due_date,
        status="active"
    )
    db.add(tx)

    # 3. Mark reservation as fulfilled/collected
    r.status = "fulfilled"

    # 4. Award bonus points to patron for picking up on time
    try:
        point = UserPoint(user_id=r.user_id, points=5, reason=f"Picked up physical book '{r.book.title}' on time")
        db.add(point)
    except Exception as ex:
        print(f"[POINT WARNING] {ex}")

    # 5. Send notification to patron
    try:
        notif = Notification(
            user_id=r.user_id,
            title="Book Handover Confirmed! 📚",
            message=f"You have picked up '{r.book.title}'. Return due date: {due_date.strftime('%Y-%m-%d')}.",
            type="success"
        )
        db.add(notif)
    except Exception as ex:
        print(f"[NOTIF WARNING] {ex}")

    db.commit()

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(content={
            "message": f"Successfully handed over '{r.book.title}'! Active loan created, return due {due_date.strftime('%Y-%m-%d')}.",
            "due_date": due_date.strftime("%Y-%m-%d")
        })

    return RedirectResponse(url="/dashboard/librarian", status_code=303)
