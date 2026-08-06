from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Book, BookCopy, User
from app.controllers.auth_controller import get_current_user
from app.services.qr_service import generate_qr_token

router = APIRouter(prefix="/api/books", tags=["Catalog Management"])

@router.get("")
def get_books(db: Session = Depends(get_db)):
    books = db.query(Book).all()
    res = []
    for b in books:
        avail = db.query(BookCopy).filter(BookCopy.book_id == b.id, BookCopy.status == "available").count()
        tot = db.query(BookCopy).filter(BookCopy.book_id == b.id).count()
        res.append({
            "id": b.id, "title": b.title, "author": b.author, "isbn": b.isbn,
            "category": b.category, "available_copies": avail, "total_copies": tot
        })
    return res

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
