from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.config import settings
from app.models import BookCopy, Transaction, User, Book
from app.controllers.auth_controller import get_current_user

router = APIRouter(prefix="/api/issue", tags=["Transactions"])

@router.post("/checkout")
def checkout_book(
    copy_id: int = Form(...),
    patron_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Only staff can issue books manually")

    copy = db.query(BookCopy).filter(BookCopy.id == copy_id).first()
    if not copy or copy.status != "available":
        return JSONResponse(status_code=400, content={"error": "Book copy is currently unavailable"})

    patron = db.query(User).filter(User.id == patron_id, User.role == "patron").first()
    if not patron or not patron.is_approved:
        return JSONResponse(status_code=400, content={"error": "Patron not found or not approved"})

    due = datetime.utcnow() + timedelta(days=settings.LOAN_PERIOD_DAYS)
    trans = Transaction(
        book_copy_id=copy.id,
        patron_id=patron.id,
        issued_by_id=current_user.id,
        due_date=due,
        status="active"
    )
    copy.status = "issued"
    db.add(trans)
    db.commit()

    return JSONResponse(content={
        "message": f"Book '{copy.book.title}' issued to {patron.full_name}",
        "due_date": due.strftime("%Y-%m-%d"),
        "transaction_id": trans.id
    })

@router.post("/qr-checkout")
def qr_checkout(
    qr_token: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI Feature 4: Fast QR Borrow under 10 seconds.
    Can be initiated by patron (self-service) or librarian.
    """
    copy = db.query(BookCopy).filter(BookCopy.qr_token == qr_token.strip()).first()
    if not copy:
        return JSONResponse(status_code=404, content={"error": "Invalid QR Token"})

    if copy.status != "available":
        return JSONResponse(status_code=400, content={"error": f"Copy '{copy.copy_code}' is currently {copy.status}"})

    # If current_user is patron, borrow for self. If staff, borrow for self or prompt
    due = datetime.utcnow() + timedelta(days=settings.LOAN_PERIOD_DAYS)
    trans = Transaction(
        book_copy_id=copy.id,
        patron_id=current_user.id,
        issued_by_id=current_user.id if current_user.role != "patron" else None,
        due_date=due,
        status="active"
    )
    copy.status = "issued"
    db.add(trans)
    db.commit()

    return JSONResponse(content={
        "message": f"SUCCESS! '{copy.book.title}' checked out instantly.",
        "book_title": copy.book.title,
        "due_date": due.strftime("%b %d, %Y"),
        "borrower": current_user.full_name
    })

@router.post("/return/{transaction_id}")
def return_book(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    trans = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.status.in_(["active", "overdue"])).first()
    if not trans:
        return JSONResponse(status_code=404, content={"error": "Active transaction not found"})

    now = datetime.utcnow()
    trans.return_date = now
    trans.status = "returned"

    # Calculate fine: GHS 0.50/day overdue
    fine = 0.00
    if now > trans.due_date:
        overdue_days = (now - trans.due_date).days or 1
        fine = round(overdue_days * settings.DAILY_FINE_GHS, 2)
    
    trans.fine_amount = fine

    # Restore book copy status
    trans.book_copy.status = "available"
    db.commit()

    return JSONResponse(content={
        "message": f"Book '{trans.book_copy.book.title}' returned successfully",
        "fine_amount_ghs": fine
    })

@router.get("/active")
def list_active_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(Transaction.status.in_(["active", "overdue"]))
    
    if current_user.role == "patron":
        query = query.filter(Transaction.patron_id == current_user.id)
    elif current_user.role == "librarian":
        query = query.join(BookCopy).filter(BookCopy.branch_id == current_user.branch_id)

    transactions = query.all()
    now = datetime.utcnow()

    res = []
    for t in transactions:
        is_overdue = now > t.due_date
        overdue_days = (now - t.due_date).days if is_overdue else 0
        fine = round(overdue_days * settings.DAILY_FINE_GHS, 2) if is_overdue else 0.00

        res.append({
            "id": t.id,
            "book_title": t.book_copy.book.title,
            "copy_code": t.book_copy.copy_code,
            "patron_name": t.patron.full_name,
            "patron_email": t.patron.email,
            "issue_date": t.issue_date.strftime("%Y-%m-%d"),
            "due_date": t.due_date.strftime("%Y-%m-%d"),
            "is_overdue": is_overdue,
            "overdue_days": overdue_days,
            "fine_amount_ghs": fine
        })
    return res
