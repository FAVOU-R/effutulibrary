from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Transaction, BookCopy, User
from app.controllers.auth_controller import get_current_user

router = APIRouter(prefix="/api/circulation", tags=["Circulation & Loans"])

@router.post("/issue")
def issue_book(
    copy_code: str = Form(...),
    patron_email: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    copy = db.query(BookCopy).filter(BookCopy.copy_code == copy_code).first()
    if not copy or copy.status != "available":
        raise HTTPException(status_code=400, detail="Book copy not available")

    patron = db.query(User).filter(User.email == patron_email).first()
    if not patron or not patron.is_approved:
        raise HTTPException(status_code=400, detail="Patron not found or pending approval")

    # Enforce Configurable Maximum Borrowing Limit
    from app.config import settings
    active_loans_count = db.query(Transaction).filter(
        Transaction.patron_id == patron.id,
        Transaction.status.in_(["active", "overdue"])
    ).count()

    max_allowed = getattr(settings, "MAX_BOOKS_PER_PATRON", 3)
    if active_loans_count >= max_allowed:
        raise HTTPException(
            status_code=400, 
            detail=f"Patron has reached the maximum allowed limit of {max_allowed} active book loans."
        )

    issue_date = datetime.utcnow()
    due_date = issue_date + timedelta(days=settings.LOAN_PERIOD_DAYS)

    tx = Transaction(
        book_copy_id=copy.id,
        patron_id=patron.id,
        issued_by_id=current_user.id,
        issue_date=issue_date,
        due_date=due_date,
        status="active"
    )
    copy.status = "issued"

    db.add(tx)
    db.commit()
    return JSONResponse(content={"message": "Book issued successfully", "due_date": due_date.strftime("%Y-%m-%d")})

@router.post("/return")
def return_book(
    copy_code: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    copy = db.query(BookCopy).filter(BookCopy.copy_code == copy_code).first()
    if not copy or copy.status != "issued":
        raise HTTPException(status_code=400, detail="Invalid or unissued copy")

    tx = db.query(Transaction).filter(Transaction.book_copy_id == copy.id, Transaction.status.in_(["active", "overdue"])).first()
    if tx:
        tx.return_date = datetime.utcnow()
        tx.status = "returned"
    
    copy.status = "available"
    db.commit()
    return JSONResponse(content={"message": "Book returned successfully"})
