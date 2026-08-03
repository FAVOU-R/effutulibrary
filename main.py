from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import os

from app.config import settings
from app.database import get_db, engine, Base
from app.models import Branch, User, Book, BookCopy, Transaction
from seed_data import seed_database

# Include API Controllers
from app.controllers.auth_controller import router as auth_router, get_current_user_optional, get_current_user
from app.controllers.branch_controller import router as branch_router
from app.controllers.user_controller import router as user_router
from app.controllers.book_controller import router as book_router
from app.controllers.issue_controller import router as issue_router
from app.controllers.ai_controller import router as ai_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Effutu Municipal Library Management System (Central Region, Ghana) - Evergreen ILS Inspired Lightweight Platform"
)

# Mount Static Files
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "app", "static")
templates_dir = os.path.join(base_dir, "app", "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Register API Routers
app.include_router(auth_router)
app.include_router(branch_router)
app.include_router(user_router)
app.include_router(book_router)
app.include_router(issue_router)
app.include_router(ai_router)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_database()

# --- HTML Template Views ---

@app.get("/", response_class=HTMLResponse)
def home_redirect(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url=f"/dashboard/{user.role}")
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url=f"/dashboard/{user.role}")
    return templates.TemplateResponse(request=request, name="auth/login.html", context={"current_user": None})

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    branches = db.query(Branch).filter(Branch.status == "active").all()
    return templates.TemplateResponse(request=request, name="auth/register.html", context={"branches": branches, "current_user": None})

@app.get("/dashboard/{role}", response_class=HTMLResponse)
def role_dashboard(role: str, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_optional(request, db)
    if not current_user:
        return RedirectResponse(url="/login")

    # Role Security Guard
    if current_user.role != role:
        return RedirectResponse(url=f"/dashboard/{current_user.role}")

    # 1. System Admin View
    if role == "sys_admin":
        branches = db.query(Branch).order_by(Branch.id).all()
        stats = {
            "total_branches": len(branches),
            "active_branches": len([b for b in branches if b.status == "active"]),
            "total_users": db.query(User).count(),
            "total_books": db.query(Book).count(),
            "active_loans": db.query(Transaction).filter(Transaction.status == "active").count()
        }
        return templates.TemplateResponse(request=request, name="dashboards/sys_admin.html", context={
            "current_user": current_user,
            "branches": branches,
            "stats": stats
        })

    # 2. HQ Admin View
    elif role == "hq_admin":
        hq_branch = db.query(Branch).filter(Branch.is_hq == True).first() or current_user.branch
        sub_branches = db.query(Branch).filter(Branch.is_hq == False).all()
        active_loans = db.query(Transaction).filter(Transaction.status.in_(["active", "overdue"])).all()
        loans_data = [{
            "id": t.id,
            "book_title": t.book_copy.book.title,
            "patron_name": t.patron.full_name,
            "due_date": t.due_date.strftime("%Y-%m-%d"),
            "is_overdue": t.status == "overdue",
            "fine_amount_ghs": t.fine_amount
        } for t in active_loans]

        return templates.TemplateResponse(request=request, name="dashboards/hq_admin.html", context={
            "current_user": current_user,
            "branch": hq_branch,
            "sub_branches": sub_branches,
            "active_loans": loans_data
        })

    # 3. Librarian View
    elif role == "librarian":
        branch = current_user.branch or db.query(Branch).first()
        pending_users = db.query(User).filter(User.is_approved == False, User.branch_id == branch.id).all()
        active_loans = db.query(Transaction).join(BookCopy).filter(
            BookCopy.branch_id == branch.id,
            Transaction.status.in_(["active", "overdue"])
        ).all()
        loans_data = [{
            "id": t.id,
            "book_title": t.book_copy.book.title,
            "patron_name": t.patron.full_name,
            "due_date": t.due_date.strftime("%Y-%m-%d"),
            "is_overdue": t.status == "overdue",
            "fine_amount_ghs": t.fine_amount
        } for t in active_loans]

        return templates.TemplateResponse(request=request, name="dashboards/librarian.html", context={
            "current_user": current_user,
            "branch": branch,
            "pending_users": pending_users,
            "active_loans": loans_data
        })

    # 4. Patron View
    elif role == "patron":
        active_loans = db.query(Transaction).filter(
            Transaction.patron_id == current_user.id,
            Transaction.status.in_(["active", "overdue"])
        ).all()
        loans_data = [{
            "id": t.id,
            "book_title": t.book_copy.book.title,
            "issue_date": t.issue_date.strftime("%Y-%m-%d"),
            "due_date": t.due_date.strftime("%Y-%m-%d"),
            "is_overdue": t.status == "overdue",
            "fine_amount_ghs": t.fine_amount
        } for t in active_loans]

        return templates.TemplateResponse(request=request, name="dashboards/patron.html", context={
            "current_user": current_user,
            "patron": current_user,
            "active_loans": loans_data
        })

    return RedirectResponse(url="/login")

@app.get("/catalog", response_class=HTMLResponse)
def catalog_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    books = db.query(Book).all()
    books_data = []
    for b in books:
        avail = db.query(BookCopy).filter(BookCopy.book_id == b.id, BookCopy.status == "available").count()
        tot = db.query(BookCopy).filter(BookCopy.book_id == b.id).count()
        books_data.append({
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "isbn": b.isbn,
            "category": b.category,
            "cover_url": b.cover_url or "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300",
            "available_copies": avail,
            "total_copies": tot
        })

    return templates.TemplateResponse(request=request, name="catalog/index.html", context={
        "current_user": user,
        "books": books_data
    })

@app.get("/catalog/add", response_class=HTMLResponse)
def add_book_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    branches = db.query(Branch).filter(Branch.status == "active").all()
    return templates.TemplateResponse(request=request, name="catalog/add_book.html", context={
        "current_user": user,
        "branches": branches
    })

@app.get("/scan-qr", response_class=HTMLResponse)
def qr_scan_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse(request=request, name="catalog/qr_scan.html", context={
        "current_user": user
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
