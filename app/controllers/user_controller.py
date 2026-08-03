from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import random
from app.database import get_db
from app.models import User, Branch, Notification
from app.controllers.auth_controller import get_current_user, get_password_hash
from app.services.email_service import send_approval_email

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/pending")
def list_pending_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Librarians see pending patrons in their branch. Admins see all.
    query = db.query(User).filter(User.is_approved == False)
    if current_user.role == "librarian":
        query = query.filter(User.branch_id == current_user.branch_id)
    
    pending = query.all()
    return [{
        "id": u.id,
        "full_name": u.full_name,
        "email": u.email,
        "branch_name": u.branch.name if u.branch else "Unassigned",
        "created_at": u.created_at.strftime("%Y-%m-%d %H:%M")
    } for u in pending]

@router.post("/approve/{user_id}")
def approve_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    # Branch scoping check for librarian
    if current_user.role == "librarian" and target_user.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Librarians can only approve patrons assigned to their branch")

    # Generate unique Member ID: EFF-MBR-1000 to 9999
    member_num = random.randint(1000, 9999)
    target_user.member_id = f"EFF-MBR-{member_num}"
    target_user.is_approved = True
    
    # Create notification entry
    notif = Notification(
        user_id=target_user.id,
        title="Account Approved",
        message=f"Welcome! Your Member ID is {target_user.member_id}.",
        type="success"
    )
    db.add(notif)
    db.commit()

    # Trigger Brevo Email with login link
    base_url = str(request.base_url).rstrip("/")
    login_link = f"{base_url}/login"
    send_approval_email(
        to_email=target_user.email,
        full_name=target_user.full_name,
        member_id=target_user.member_id,
        login_url=login_link
    )

    return JSONResponse(content={
        "message": f"User {target_user.full_name} approved! Member ID: {target_user.member_id}",
        "member_id": target_user.member_id
    })

@router.post("/create-staff")
def create_staff(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    branch_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "sys_admin":
        raise HTTPException(status_code=403, detail="Only System Admin can create staff users")

    if role not in ["sys_admin", "hq_admin", "librarian"]:
        return JSONResponse(status_code=400, content={"error": "Invalid role specified"})

    existing = db.query(User).filter(User.email == email.lower().strip()).first()
    if existing:
        return JSONResponse(status_code=400, content={"error": "Email already exists"})

    hashed_pw = get_password_hash(password)
    member_num = random.randint(1000, 9999)
    prefix = "SYS" if role == "sys_admin" else ("HQ" if role == "hq_admin" else "LIB")
    
    staff = User(
        full_name=full_name.strip(),
        email=email.lower().strip(),
        hashed_password=hashed_pw,
        role=role,
        branch_id=branch_id,
        is_approved=True,
        member_id=f"EFF-{prefix}-{member_num}"
    )
    db.add(staff)
    db.commit()

    return JSONResponse(content={"message": f"Staff user '{full_name}' ({role}) created successfully"})
