from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import jose.jwt
from passlib.context import CryptContext

from app.database import get_db
from app.config import settings
from app.models import User, Branch

router = APIRouter(prefix="/auth", tags=["Auth"])
import hashlib
import os

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

@router.post("/login")
def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.hashed_password):
        return JSONResponse(status_code=400, content={"error": "Invalid email or password"})
    
    if not user.is_approved and user.role == "patron":
        return JSONResponse(status_code=403, content={"error": "Account pending approval by branch librarian"})

    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    res = JSONResponse(content={
        "message": "Login successful", 
        "redirect_url": f"/dashboard/{user.role}",
        "user": {"id": user.id, "name": user.full_name, "role": user.role}
    })
    res.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
    return res

@router.post("/register")
def register(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    branch_id: int = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == email.lower().strip()).first()
    if existing:
        return JSONResponse(status_code=400, content={"error": "Email address already registered"})

    hashed_pw = get_password_hash(password)
    
    # New patrons are pending approval by branch librarian
    new_user = User(
        full_name=full_name.strip(),
        email=email.lower().strip(),
        hashed_password=hashed_pw,
        role="patron",
        branch_id=branch_id,
        is_approved=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return JSONResponse(content={
        "message": "Registration submitted! Please await approval from your branch librarian.",
        "user_id": new_user.id
    })

@router.get("/logout")
def logout():
    res = RedirectResponse(url="/login")
    res.delete_cookie("access_token")
    return res
