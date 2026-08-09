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
@router.post("/api/issue/qr-checkout")
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

    # 1. Security Check: Require Physical ID Verification for Patrons
    if current_user.role == "patron":
        if not current_user.is_approved or current_user.verification_status != "verified":
            return JSONResponse(
                status_code=403,
                content={"error": f"Physical ID Verification Required: Hi {current_user.full_name}, please present your Ghana Card, School ID, or Voters ID at the library desk to activate physical book borrowing privileges."}
            )

        # 2. Check Active Loan Limit (Max 3 books)
        from app.models import Transaction
        active_loans_count = db.query(Transaction).filter(
            Transaction.patron_id == current_user.id,
            Transaction.status.in_(["active", "overdue"])
        ).count()
        if active_loans_count >= 3:
            return JSONResponse(
                status_code=400,
                content={"error": f"Borrowing Limit Reached: You currently have {active_loans_count} active physical loans (Max 3 allowed). Please return a book to borrow a new one."}
            )

    # 1. Exact match on full qr_token or full copy_code (case-insensitive)
    copy = db.query(BookCopy).filter(
        (BookCopy.qr_token.ilike(token_clean)) | (BookCopy.copy_code.ilike(token_clean))
    ).first()

    # 2. Match unique token suffix (e.g. 374F383B or 2FOBFA6D)
    if not copy:
        token_parts = token_clean.split('-')
        last_part = token_parts[-1].strip()
        if len(last_part) >= 6:
            copy = db.query(BookCopy).filter(BookCopy.qr_token.ilike(f"%{last_part}")).first()

    # 3. Match full copy code format B{book_id}-BR{branch_id}-{copy_num}
    if not copy and re.match(r'^B\d+[\-_]BR\d+[\-_]\d+$', token_clean, re.IGNORECASE):
        copy = db.query(BookCopy).filter(BookCopy.copy_code.ilike(token_clean)).first()

    if not copy:
        return JSONResponse(
            status_code=404, 
            content={"error": f"Invalid QR Token '{token_clean}'. Please verify all digits or scan the QR sticker on the physical book."}
        )

    if copy.status != "available":
        return JSONResponse(
            status_code=400,
            content={"error": f"Book copy '{copy.copy_code}' ('{copy.book.title}') is currently {copy.status.upper()} and unavailable for checkout."}
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

    # Dispatch notification for patron and librarian desk
    try:
        from app.models import Notification
        notif = Notification(
            user_id=current_user.id,
            title="⚡ In-Library Self-Checkout",
            message=f"Self-checked out '{book.title}' (Copy {copy.copy_code}). Show Exit Pass at desk.",
            type="info"
        )
        db.add(notif)
    except Exception as ex:
        print(f"[NOTIF WARNING] {ex}")

    db.commit()

    return JSONResponse(content={
        "message": f"Successfully checked out '{book.title}'!",
        "book_title": book.title,
        "borrower": current_user.full_name,
        "member_id": current_user.member_id or f"ID-{current_user.id}",
        "copy_code": copy.copy_code,
        "branch_name": copy.branch.name if copy.branch else "Library Desk",
        "checkout_time": issue_date.strftime("%H:%M:%S GMT"),
        "due_date": due_date.strftime("%Y-%m-%d")
    })

@router.post("/extend/{trans_id}")
def extend_loan(
    trans_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tx = db.query(Transaction).filter(Transaction.id == trans_id).first()
    if not tx:
        return JSONResponse(status_code=404, content={"error": "Loan record not found"})

    # Check permission
    if current_user.role == "patron" and tx.patron_id != current_user.id:
        return JSONResponse(status_code=403, content={"error": "Unauthorized to extend this loan"})

    tx.due_date = tx.due_date + timedelta(days=7)
    if tx.status == "overdue":
        tx.status = "active"

    try:
        from app.models import Notification
        b_title = tx.book_copy.book.title if (tx.book_copy and tx.book_copy.book) else "Book"
        notif = Notification(
            user_id=tx.patron_id,
            title="Loan Extended (+7 Days) 📅",
            message=f"Due date for '{b_title}' has been extended to {tx.due_date.strftime('%Y-%m-%d')}.",
            type="success"
        )
        db.add(notif)
    except Exception as ex:
        print(f"[EXTEND NOTIF WARNING] {ex}")

    db.commit()

    return JSONResponse(content={
        "message": f"Loan extended by +7 days! New return due date: {tx.due_date.strftime('%Y-%m-%d')}.",
        "new_due_date": tx.due_date.strftime("%Y-%m-%d")
    })
