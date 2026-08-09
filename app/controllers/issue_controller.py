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

@router.post("/qr-checkout")
def qr_checkout(
    qr_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import re
    from app.models import Book
    from app.config import settings

    token_clean = (qr_token or "").strip()
    if not token_clean:
        return JSONResponse(status_code=400, content={"error": "QR Token cannot be empty"})

    # 1. Exact match by qr_token or copy_code
    copy = db.query(BookCopy).filter(
        (BookCopy.qr_token == token_clean) | (BookCopy.copy_code == token_clean)
    ).first()

    # 2. Pattern match by book ID (e.g. EFF-LIB-B1-MAIN -> B1 -> book_id=1)
    if not copy:
        m = re.search(r'B(\d+)', token_clean, re.IGNORECASE)
        if m:
            book_id = int(m.group(1))
            copy = db.query(BookCopy).filter(BookCopy.book_id == book_id, BookCopy.status == "available").first()
            if not copy:
                copy = db.query(BookCopy).filter(BookCopy.book_id == book_id).first()

    # 3. Fallback: Search Book by title / ID
    if not copy:
        m_id = re.search(r'(\d+)', token_clean)
        if m_id:
            b_id = int(m_id.group(1))
            book_obj = db.query(Book).filter(Book.id == b_id).first()
            if book_obj:
                copy = db.query(BookCopy).filter(BookCopy.book_id == book_obj.id, BookCopy.status == "available").first()
                if not copy:
                    copy = db.query(BookCopy).filter(BookCopy.book_id == book_obj.id).first()

    if not copy:
        return JSONResponse(
            status_code=404, 
            content={"error": f"Resource not available for token '{token_clean}'. Please verify token code or copy ID."}
        )

    book = copy.book
    issue_date = datetime.utcnow()
    due_date = issue_date + timedelta(days=getattr(settings, "LOAN_PERIOD_DAYS", 14))

    # Record checkout transaction
    tx = Transaction(
        book_copy_id=copy.id,
        patron_id=current_user.id,
        issued_by_id=current_user.id if current_user.role in ["sys_admin", "hq_admin", "librarian"] else None,
        issue_date=issue_date,
        due_date=due_date,
        status="active"
    )
    copy.status = "issued"
    db.add(tx)
    db.commit()

    return JSONResponse(content={
        "message": f"Successfully checked out '{book.title}'!",
        "book_title": book.title,
        "borrower": current_user.full_name,
        "due_date": due_date.strftime("%Y-%m-%d")
    })
