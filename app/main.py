from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import os

from app.config import settings
from app.database import get_db, engine, Base
from app.models import Branch, User, Book, BookCopy, Transaction

try:
    from seed_data import seed_database
except ImportError:
    try:
        from app.seed_data import seed_database
    except ImportError:
        seed_database = None

# Include API Controllers
from app.controllers.auth_controller import router as auth_router, get_current_user_optional, get_current_user
from app.controllers.branch_controller import router as branch_router
from app.controllers.user_controller import router as user_router
from app.controllers.book_controller import router as book_router
from app.controllers.issue_controller import router as issue_router
from app.controllers.ai_controller import router as ai_router
from app.controllers.librarian_controller import router as librarian_router

# Direct Module-Level FastAPI Application Instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Effutu Municipal Library Management System (Central Region, Ghana) - Evergreen ILS Inspired Lightweight Platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Absolute Path Resolution for Static & Template Files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(BASE_DIR, "app", "static")
templates_dir = os.path.join(BASE_DIR, "app", "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=templates_dir)

# Register API Routers
app.include_router(auth_router)
app.include_router(branch_router)
app.include_router(user_router)
app.include_router(book_router)
app.include_router(issue_router)
app.include_router(ai_router)
app.include_router(librarian_router)

@app.on_event("startup")
def on_startup():
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)

    statements = [
        """
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='ghana_card_number') THEN
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='ghana_card') THEN
                    ALTER TABLE users RENAME COLUMN ghana_card TO ghana_card_number;
                ELSE
                    ALTER TABLE users ADD COLUMN ghana_card_number VARCHAR(50);
                END IF;
            END IF;
        END $$;
        """,
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ghana_card_number VARCHAR(50);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS id_type VARCHAR(50) DEFAULT 'ghanacard';",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS id_number VARCHAR(50);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS alt_contact VARCHAR(150);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50);",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_status VARCHAR(30) DEFAULT 'verified';",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_physically_verified BOOLEAN DEFAULT FALSE;"
    ]

    for stmt in statements:
        try:
            with engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
        except Exception:
            pass

    if seed_database:
        try:
            seed_database()
        except Exception as e:
            print(f"[STARTUP WARNING] Seed database exception: {e}")

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

@app.get("/users", response_class=HTMLResponse)
def users_directory_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    query = db.query(User)
    if current_user.role == "librarian":
        query = query.filter(User.branch_id == current_user.branch_id)

    users = query.order_by(User.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users/index.html", context={
        "current_user": current_user,
        "users": users
    })

@app.get("/scan-qr", response_class=HTMLResponse)
def qr_scan_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse(request=request, name="catalog/qr_scan.html", context={
        "current_user": user
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=10000, reload=True)
