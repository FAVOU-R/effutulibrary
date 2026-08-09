from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
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
from app.controllers.reservation_controller import router as reservation_router
from app.controllers.points_controller import router as points_router
from app.controllers.reports_controller import router as reports_router
from app.controllers.notifications_controller import router as notifications_router

# Direct Module-Level FastAPI Application Instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Effutu Municipal Library Management System (Central Region, Ghana) - Powered by ITB",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS & Security Hardening Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Absolute Path Resolution for Static & Template Files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(BASE_DIR, "app", "static")
templates_dir = os.path.join(BASE_DIR, "app", "templates")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=templates_dir)

# Global Custom Error Exception Handlers
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: Exception):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"error": "Requested resource not found"})
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        user = get_current_user_optional(request, db)
    except Exception:
        user = None
    finally:
        db.close()
    return templates.TemplateResponse(request=request, name="errors/404.html", context={"current_user": user}, status_code=404)

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc: Exception):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=500, content={"error": "An internal server error occurred"})
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        user = get_current_user_optional(request, db)
    except Exception:
        user = None
    finally:
        db.close()
    return templates.TemplateResponse(request=request, name="errors/500.html", context={"current_user": user}, status_code=500)

# Register API Routers
app.include_router(auth_router)
app.include_router(branch_router)
app.include_router(user_router)
app.include_router(book_router)
app.include_router(issue_router)
app.include_router(ai_router)
app.include_router(librarian_router)
app.include_router(reservation_router)
app.include_router(points_router)
app.include_router(reports_router)
app.include_router(notifications_router)

@app.on_event("startup")
def on_startup():
    from sqlalchemy import text, inspect
    Base.metadata.create_all(bind=engine)

    columns_to_ensure = [
        ("users", "ghana_card_number", "VARCHAR(50)"),
        ("users", "id_type", "VARCHAR(50) DEFAULT 'ghanacard'"),
        ("users", "id_number", "VARCHAR(50)"),
        ("users", "phone", "VARCHAR(50)"),
        ("users", "sex", "VARCHAR(20)"),
        ("users", "school_occupation", "VARCHAR(150)"),
        ("users", "location", "VARCHAR(150)"),
        ("users", "verification_status", "VARCHAR(30) DEFAULT 'pending'"),
        ("users", "verified_by", "INTEGER"),
        ("users", "verified_at", "TIMESTAMP"),
        ("users", "rejection_reason", "TEXT"),
        ("users", "id_photo_url", "VARCHAR(255)"),
        ("users", "guardian_name", "VARCHAR(150)"),
        ("users", "guardian_phone", "VARCHAR(50)"),
        ("users", "guardian_email", "VARCHAR(150)"),
        ("users", "guardian_relationship", "VARCHAR(50)"),
        ("users", "is_approved", "BOOLEAN DEFAULT TRUE"),
        ("users", "is_active", "BOOLEAN DEFAULT TRUE"),
        ("users", "must_change_password", "BOOLEAN DEFAULT TRUE"),
        ("users", "is_physically_verified", "BOOLEAN DEFAULT FALSE"),
        ("users", "failed_login_attempts", "INTEGER DEFAULT 0"),
        ("users", "locked_until", "TIMESTAMP"),
        ("users", "username", "VARCHAR(50)"),
        ("users", "profile_picture_url", "VARCHAR(255)"),
        ("reservations", "reject_reason", "TEXT"),
    ]

    try:
        inspector = inspect(engine)
        for table, col, col_type in columns_to_ensure:
            try:
                existing_cols = [c['name'] for c in inspector.get_columns(table)]
                if col not in existing_cols:
                    with engine.connect() as conn:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"))
                        conn.commit()
                        print(f"[MIGRATION SUCCESS] Added column '{col}' to table '{table}'")
            except Exception as ex:
                print(f"[MIGRATION WARNING] Column '{col}' on '{table}': {ex}")
    except Exception as e:
        print(f"[MIGRATION ERROR] {e}")

    # Backfill usernames for any pre-existing users without a handle
    try:
        from app.database import SessionLocal
        from app.models import User
        import re
        db_s = SessionLocal()
        users_to_fix = db_s.query(User).filter((User.username == None) | (User.username == '')).all()
        if users_to_fix:
            for u in users_to_fix:
                if u.email:
                    base_h = u.email.split("@")[0].lower()
                elif u.full_name:
                    base_h = u.full_name.strip().lower().replace(" ", "_")
                else:
                    base_h = f"user_{u.id}"
                
                base_h = re.sub(r'[^a-z0-9_]', '', base_h)
                if not base_h:
                    base_h = f"user_{u.id}"
                
                cand = base_h
                cnt = 1
                while db_s.query(User).filter(User.username == cand, User.id != u.id).first():
                    cand = f"{base_h}{cnt}"
                    cnt += 1
                u.username = cand
            db_s.commit()
            print(f"[STARTUP] Automatically assigned handles for {len(users_to_fix)} existing user(s).")
        db_s.close()
    except Exception as ex:
        print(f"[STARTUP WARNING] Username backfill exception: {ex}")

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
    return RedirectResponse(url="/auth/login")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url=f"/dashboard/{user.role}")
    return RedirectResponse(url="/auth/login")

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

@app.get("/health")
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "app": "Effutu Library Network",
            "version": settings.VERSION
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
