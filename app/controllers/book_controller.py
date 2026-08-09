from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from typing import List
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Book, BookCopy, User
from app.controllers.auth_controller import get_current_user
from app.services.qr_service import generate_qr_token, generate_qr_code_base64
import io
import re

router = APIRouter(prefix="/api/books", tags=["Catalog Management"])

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            if txt.strip():
                pages_text.append(f"--- PAGE {i+1} ---\n{txt.strip()}")
        if pages_text:
            return "\n\n".join(pages_text)
    except Exception as e:
        print(f"[PDF EXTRACTION WARNING] {e}")
    return ""

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
@router.post("/add")
async def add_book(
    title: str = Form(...),
    author: str = Form(...),
    isbn: str = Form(None),
    category: str = Form("General Literature"),
    publisher: str = Form(None),
    pub_year: int = Form(None),
    cover_url: str = Form(None),
    description: str = Form(None),
    content_text: str = Form(None),
    branch_id: int = Form(1),
    copies_count: int = Form(1),
    pdf_file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    pdf_extracted_text = ""
    if pdf_file and pdf_file.filename:
        pdf_bytes = await pdf_file.read()
        pdf_extracted_text = extract_text_from_pdf_bytes(pdf_bytes)

    provided_content = (content_text or "").strip()
    if pdf_extracted_text and provided_content:
        clean_content = f"{provided_content}\n\n=== EXTRACTED PDF TEXT ({pdf_file.filename}) ===\n{pdf_extracted_text}"
    elif pdf_extracted_text:
        clean_content = f"=== EXTRACTED PDF TEXT ({pdf_file.filename}) ===\n{pdf_extracted_text}"
    elif provided_content:
        clean_content = provided_content
    else:
        clean_content = f"""CHAPTER 1: Introduction to {title.strip()}

Author: {author.strip()}
Category: {category.strip()}

Welcome to the digital softcopy edition of '{title.strip()}'.
This book is preserved in the Effutu Municipal Library Network softcopy archives.

SECTION 1: Core Content & Study Summary
{description.strip() if description else 'Detailed study guide, chapter notes, and references for students and patrons.'}

You can read all chapters directly in this non-downloadable softcopy viewer or reserve the physical hard copy at any branch desk."""

    new_book = Book(
        title=title.strip(),
        author=author.strip(),
        isbn=isbn.strip() if (isbn and isbn.strip()) else None,
        category=category.strip() if category else "General Literature",
        publisher=publisher.strip() if (publisher and publisher.strip()) else None,
        pub_year=pub_year,
        cover_url=cover_url.strip() if (cover_url and cover_url.strip()) else "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400",
        description=description.strip() if (description and description.strip()) else None,
        content_text=clean_content
    )
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
    return JSONResponse(content={
        "message": f"Book '{new_book.title}' & softcopy text saved successfully! Araba AI has studied the content.",
        "book_id": new_book.id
    })

@router.post("/batch-add-pdf")
async def batch_add_pdf(
    pdf_files: List[UploadFile] = File(...),
    category: str = Form("General Literature"),
    branch_id: int = Form(1),
    copies_count: int = Form(1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if not pdf_files:
        return JSONResponse(status_code=400, content={"error": "No PDF files selected for batch upload."})

    imported_books = []
    for f in pdf_files:
        if not f.filename:
            continue
        pdf_bytes = await f.read()
        extracted_txt = extract_text_from_pdf_bytes(pdf_bytes)

        # Derive title from filename
        raw_name = f.filename.rsplit('.', 1)[0]
        clean_title = re.sub(r'[\-_]', ' ', raw_name).title().strip()
        author_name = "Effutu Educational Publishers"

        full_content = extracted_txt if extracted_txt else f"=== SOFTCOPY EDITION: {clean_title} ===\nImported from {f.filename}."

        book_obj = Book(
            title=clean_title,
            author=author_name,
            category=category.strip() if category else "General Literature",
            cover_url="https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400",
            description=f"Digitized eBook softcopy imported from PDF ({f.filename}).",
            content_text=full_content
        )
        db.add(book_obj)
        db.commit()
        db.refresh(book_obj)

        for i in range(copies_count):
            qr_tok = generate_qr_token(book_obj.id, branch_id)
            copy = BookCopy(
                book_id=book_obj.id,
                branch_id=branch_id,
                copy_code=f"B{book_obj.id}-BR{branch_id}-{i+1:02d}",
                qr_token=qr_tok,
                status="available"
            )
            db.add(copy)

        db.commit()
        imported_books.append(book_obj.title)

    return JSONResponse(content={
        "message": f"Successfully batch imported {len(imported_books)} PDF eBook(s) into the catalog!",
        "imported_count": len(imported_books),
        "books": imported_books
    })
