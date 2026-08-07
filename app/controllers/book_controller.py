from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Book, BookCopy, User
from app.controllers.auth_controller import get_current_user
from app.services.qr_service import generate_qr_token, generate_qr_code_base64

router = APIRouter(prefix="/api/books", tags=["Catalog Management"])

@router.get("")
def get_books(db: Session = Depends(get_db)):
    books = db.query(Book).all()
    res = []
    for b in books:
        avail = db.query(BookCopy).filter(BookCopy.book_id == b.id, BookCopy.status == "available").count()
        tot = db.query(BookCopy).filter(BookCopy.book_id == b.id).count()
        tok = f"EFF-LIB-B{b.id}-MAIN"
        res.append({
            "id": b.id, "title": b.title, "author": b.author, "isbn": b.isbn,
            "category": b.category, "available_copies": avail, "total_copies": tot,
            "token": tok, "qr_token": tok, "qr": generate_qr_code_base64(tok)
        })
    return res

@router.get("/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    copies = db.query(BookCopy).filter(BookCopy.book_id == book.id).all()
    copies_list = []
    for c in copies:
        copies_list.append({
            "id": c.id,
            "copy_code": c.copy_code,
            "branch_name": c.branch.name if c.branch else "HQ Central Library",
            "status": c.status,
            "qr_token": c.qr_token,
            "qr_base64": generate_qr_code_base64(c.qr_token)
        })

    first_copy = next((c for c in copies if c.status == "available"), copies[0] if copies else None)
    qr_tok = first_copy.qr_token if first_copy else f"EFF-LIB-B{book.id}-MAIN"
    qr_base64 = generate_qr_code_base64(qr_tok)

    avail = sum(1 for c in copies if c.status == "available")
    tot = len(copies)

    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "category": book.category,
        "available_copies": avail,
        "total_copies": tot,
        "token": qr_tok,
        "qr_token": qr_tok,
        "qr": qr_base64,
        "qr_code": qr_base64,
        "copies": copies_list
    }

@router.get("/{book_id}/token")
@router.get("/{book_id}/qr")
def get_book_qr(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    copy = db.query(BookCopy).filter(BookCopy.book_id == book.id, BookCopy.status == "available").first()
    if not copy:
        copy = db.query(BookCopy).filter(BookCopy.book_id == book.id).first()

    qr_tok = copy.qr_token if copy else f"EFF-LIB-B{book.id}-MAIN"
    qr_base64 = generate_qr_code_base64(qr_tok)

    return {
        "book_id": book.id,
        "title": book.title,
        "token": qr_tok,
        "qr_token": qr_tok,
        "qr": qr_base64,
        "qr_code": qr_base64
    }

@router.post("")
def add_book(
    title: str = Form(...),
    author: str = Form(...),
    isbn: str = Form(None),
    category: str = Form("General"),
    branch_id: int = Form(1),
    copies_count: int = Form(1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    new_book = Book(title=title, author=author, isbn=isbn, category=category)
    db.add(new_book)
    db.commit()
    db.refresh(new_book)

    for i in range(copies_count):
        qr_tok = generate_qr_token(new_book.id, branch_id)
        copy = BookCopy(
            book_id=new_book.id,
            branch_id=branch_id,
            copy_code=f"B{new_book.id}-BR{branch_id}-{i+1:02d}",
            qr_token=qr_tok,
            status="available"
        )
        db.add(copy)

    db.commit()
    return JSONResponse(content={"message": "Book added successfully", "book_id": new_book.id})
