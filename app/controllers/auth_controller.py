from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import jose.jwt
from passlib.context import CryptContext
import hashlib
import os
import smtplib
from email.mime.text import MIMEText

from app.database import get_db
from app.config import settings
from app.models import User, Branch

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_password_hash(password: str) -> str:
    salt = "effutu_ghana_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_password_hash(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jose.jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token and "Authorization" in request.headers:
        auth_header = request.headers.get("Authorization")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    if not token:
        return None
    try:
        payload = jose.jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
        return db.query(User).filter(User.id == user_id).first()
    except Exception as e:
        print(f"[JWT DECODE ERROR] {e}")
        return None

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user_optional(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

# ===== EMAIL FUNCTION =====
def send_reset_email(to_email: str, reset_link: str):
    try:
        msg = MIMEText(f"""
        Hello from Effutu Library!

        You requested password reset.
        Click link to reset (valid 15 mins):
        {reset_link}

        If you didn't request, ignore.
        """)
        msg['Subject'] = 'Effutu Library - Password Reset'
        msg['From'] = settings.MAIL_FROM or os.getenv("MAIL_FROM", "noreply@effutulibrary.com")
        msg['To'] = to_email

        server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
        server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

@router.post("/login")
def login(response: Response, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.hashed_password):
        return JSONResponse(status_code=400, content={"error": "Invalid email or password"})
    if not user.is_approved and user.role == "patron":
        return JSONResponse(status_code=403, content={"error": "Account pending approval by branch librarian"})
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    res = JSONResponse(content={"message": "Login successful", "redirect_url": f"/dashboard/{user.role}", "user": {"id": user.id, "name": user.full_name, "role": user.role}})
    res.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
    return res

@router.post("/register")
def register(full_name: str = Form(...), email: str = Form(...), password: str = Form(...), branch_id: int = Form(...), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == email.lower().strip()).first()
    if existing:
        return JSONResponse(status_code=400, content={"error": "Email address already registered"})
    hashed_pw = get_password_hash(password)
    new_user = User(full_name=full_name.strip(), email=email.lower().strip(), hashed_password=hashed_pw, role="patron", branch_id=branch_id, is_approved=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return JSONResponse(content={"message": "Registration submitted! Please await approval from your branch librarian.", "user_id": new_user.id})

@router.get("/logout")
def logout():
    res = RedirectResponse(url="/login")
    res.delete_cookie("access_token")
    return res

# ===== NEW FORGOT PASSWORD =====
@router.get("/forgot-password")
def forgot_password_page():
    return HTMLResponse("""
    <html><body style="font-family:Arial; padding:40px;">
    <h2>Forgot Password - Effutu Library</h2>
    <form method="post" action="/auth/forgot-password">
        <input type="email" name="email" placeholder="Enter your email" required style="padding:10px; width:300px;"><br><br>
        <button type="submit" style="padding:10px 20px; background:blue; color:white;">Send Reset Link</button>
    </form>
    <a href="/login">Back to Login</a>
    </body></html>
    """)

@router.post("/forgot-password")
def forgot_password(email: str = Form(...), request: Request = None, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user:
        return JSONResponse(content={"message": "If email exists, reset link sent!"})

    # Create reset token valid 15 mins
    reset_token = create_access_token(data={"sub": str(user.id), "type": "reset"}, expires_delta=timedelta(minutes=15))
    base_url = str(request.base_url) if request else "https://effutulibrary.onrender.com/"
    reset_link = f"{base_url}auth/reset-password?token={reset_token}"

    send_reset_email(user.email, reset_link)
    return JSONResponse(content={"message": f"Reset link sent to {user.email} (check spam). Link: {reset_link}"})

@router.get("/reset-password")
def reset_password_page(token: str):
    return HTMLResponse(f"""
    <html><body style="font-family:Arial; padding:40px;">
    <h2>Reset Password</h2>
    <form method="post" action="/auth/reset-password?token={token}">
        <input type="password" name="new_password" placeholder="New Password" required style="padding:10px; width:300px;"><br><br>
        <button type="submit" style="padding:10px 20px; background:green; color:white;">Reset Password</button>
    </form>
    </body></html>
    """)

@router.post("/reset-password")
def reset_password(token: str, new_password: str = Form(...), db: Session = Depends(get_db)):
    try:
        payload = jose.jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type")!= "reset":
            raise HTTPException(status_code=400, detail="Invalid token")
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        return RedirectResponse(url="/login?msg=password_reset_success", status_code=303)
    except Exception as e:
        return HTMLResponse(f"<h3>Link expired or invalid: {e}</h3><a href='/auth/forgot-password'>Try again</a>", status_code=400)
