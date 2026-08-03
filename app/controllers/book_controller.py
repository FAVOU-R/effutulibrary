from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Book, BookCopy, Branch, User
from app.controllers.auth_controller import get_current_user
from app.services.openlibrary import fetch_book_by_isbn
from app.services.qr_service import generate_qr_token, generate_qr_code_base64

router = APIRouter(prefix="/api/books", tags=["Books"])

@router.get("/isbn-lookup/{isbn}")
def lookup_isbn(isbn: str):
    book_info = fetch_book_by_isbn(isbn)
    if not book_info:
        return JSONResponse(status_code=404, content={"error": "Book not found in Open Library repository"})
    return book_info

@router.get("")
def list_books(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Book)
    if category:
        query = query.filter(Book.category == category)
    books = query.order_by(Book.id.desc()).all()

    result = []
    for b in books:
        available_count = db.query(BookCopy).filter(BookCopy.book_id == b.id, BookCopy.status == "available").count()
        total_count = db.query(BookCopy).filter(BookCopy.book_id == b.id).count()
        result.append({
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "isbn": b.isbn,
            "publisher": b.publisher,
            "pub_year": b.pub_year,
            "category": b.category,
            "cover_url": b.cover_url or "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300",
            "available_copies": available_count,
            "total_copies": total_count
        })
    return result

@router.get("/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return JSONResponse(status_code=404, content={"error": "Book not found"})

    copies = db.query(BookCopy).filter(BookCopy.book_id == book.id).all()
    copies_data = []
    for c in copies:
        copies_data.append({
            "id": c.id,
            "copy_code": c.copy_code,
            "branch_name": c.branch.name,
            "status": c.status,
            "qr_token": c.qr_token,
            "qr_base64": generate_qr_code_base64(c.qr_token)
        })

    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "publisher": book.publisher,
        "pub_year": book.pub_year,
        "pages": book.pages,
        "category": book.category,
        "description": book.description,
        "cover_url": book.cover_url or "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300",
        "copies": copies_data
    }

@router.post("/add")
def add_book(
    title: str = Form(...),
    author: str = Form(...),
    isbn: Optional[str] = Form(None),
    publisher: Optional[str] = Form(None),
    pub_year: Optional[int] = Form(None),
    pages: Optional[int] = Form(None),
    category: str = Form("General Literature"),
    cover_url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    branch_id: int = Form(...),
    copies_count: int = Form(1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Check if book title/isbn already exists in master catalog
    book = None
    if isbn:
        book = db.query(Book).filter(Book.isbn == isbn.strip()).first()
    
    if not book:
        book = Book(
            title=title.strip(),
            author=author.strip(),
            isbn=isbn.strip() if isbn else None,
            publisher=publisher.strip() if publisher else None,
            pub_year=pub_year,
            pages=pages,
            category=category,
            cover_url=cover_url.strip() if cover_url else None,
            description=description.strip() if description else None
        )
        db.add(book)
        db.commit()
        db.refresh(book)

    # Generate Inventory Copies & QR Tokens
    added_copies = []
    for i in range(copies_count):
        qr_tok = generate_qr_token(book.id, branch_id)
        copy_code = f"B{book.id}-BR{branch_id}-{i+1:02d}"
        copy = BookCopy(
            book_id=book.id,
            branch_id=branch_id,
            copy_code=copy_code,
            qr_token=qr_tok,
            status="available"
        )
        db.add(copy)
        added_copies.append(copy_code)
    
    db.commit()

    return JSONResponse(content={
        "message": f"Book '{book.title}' saved with {copies_count} copies",
        "book_id": book.id,
        "copies": added_copies
    })
