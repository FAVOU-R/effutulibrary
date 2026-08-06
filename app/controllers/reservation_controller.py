from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Reservation, Book, User, Notification, UserPoint
from app.controllers.auth_controller import get_current_user, send_email, get_current_user_optional

router = APIRouter(prefix="", tags=["Reservations"])

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
        badge = f"<span class='px-2 py-0.5 text-[10px] font-bold rounded uppercase {status_colors.get(r.status, 'bg-slate-100')}'>{r.status}</span>"

        rows += f"""
        <tr class='border-b border-slate-200 hover:bg-slate-50 transition text-xs'>
            <td class='p-3 font-mono font-bold text-emerald-800'>#RES-{r.id}</td>
            <td class='p-3 font-bold text-slate-800'>{patron_name}<br><span class='text-[10px] text-slate-400'>{patron_phone} • {branch_name}</span></td>
            <td class='p-3 font-semibold text-slate-700'>{book_title}</td>
            <td class='p-3 font-mono text-slate-500'>{r.reserved_at.strftime('%Y-%m-%d %H:%M')}</td>
            <td class='p-3'>{badge}</td>
            <td class='p-3 space-x-1 whitespace-nowrap'>
                {'<form method="post" action="/librarian/reservations/' + str(r.id) + '/status" class="inline"><input type="hidden" name="status" value="ready"><button class="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded text-[11px]">Mark Ready</button></form>' if r.status == 'reserved' else ''}
                {'<form method="post" action="/librarian/reservations/' + str(r.id) + '/status" class="inline"><input type="hidden" name="status" value="collected"><button class="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded text-[11px]">Mark Collected</button></form>' if r.status == 'ready' else ''}
                {'<form method="post" action="/librarian/reservations/' + str(r.id) + '/status" class="inline"><input type="hidden" name="status" value="cancelled"><button class="px-2 py-1 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded text-[11px]">Cancel</button></form>' if r.status in ['reserved', 'ready'] else ''}
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
        <title>Manage Book Reservations - Effutu Library</title>
    </head>
    <body class="bg-slate-100 min-h-screen p-6 font-sans">
        <div class="max-w-6xl mx-auto space-y-6">
            <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 class="text-2xl font-extrabold text-slate-800">Book Reservation Desk</h2>
                    <p class="text-xs text-slate-500">Track patron hold requests, mark ready for pick up, & notify patrons</p>
                </div>
                <a href="/dashboard/{current_user.role}" class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-xs rounded-lg transition">
                    Back to Dashboard
                </a>
            </div>

            <div class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-100 uppercase text-slate-500 font-bold border-b border-slate-200">
                            <tr>
                                <th class="p-3">Reservation ID</th>
                                <th class="p-3">Patron Details</th>
                                <th class="p-3">Book Title</th>
                                <th class="p-3">Reserved Date</th>
                                <th class="p-3">Status</th>
                                <th class="p-3">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else "<tr><td colspan='6' class='p-8 text-center text-slate-400'>No reservations recorded.</td></tr>"}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

@router.post("/librarian/reservations/{res_id}/status")
async def update_reservation_status(
    res_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian_or_admin)
):
    r = db.query(Reservation).filter(Reservation.id == res_id).first()
    if not r:
        return HTMLResponse("<h3>Reservation not found</h3>", status_code=404)

    r.status = status.strip()
    db.commit()

    book_title = r.book.title if r.book else "Reserved Book"
    branch_name = r.user.branch.name if (r.user and r.user.branch) else "Effutu Municipal Library"

    if status == "ready":
        # Dispatch notification & email
        notif = Notification(
            user_id=r.user_id,
            title="Book Ready for Pick Up! 📦",
            message=f"Hi {r.user.full_name}, reserved book '{book_title}' is ready at {branch_name}. Collect within 2 days.",
            type="success"
        )
        db.add(notif)
        db.commit()

        if r.user.email:
            send_email(
                r.user.email,
                f"Reserved Book Ready: '{book_title}'",
                f"<p>Hi {r.user.full_name}, reserved book <b>'{book_title}'</b> is ready at {branch_name}. Collect within 2 days.</p><p>Effutu Library Network</p>"
            )

    elif status == "collected":
        # Award +5 points for collecting reservation
        point = UserPoint(user_id=r.user_id, points=5, reason="Reserved Book Collection Bonus")
        db.add(point)
        db.commit()

    return RedirectResponse(url="/librarian/reservations", status_code=303)

def require_librarian_or_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["librarian", "sys_admin", "hq_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return current_user
