from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Branch
from app.controllers.auth_controller import get_current_user, get_password_hash, send_email
import random, os

router = APIRouter(prefix="/api/users", tags=["User Management"])

@router.get("/all")
def list_all_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["sys_admin", "hq_admin", "librarian"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    query = db.query(User)
    if current_user.role == "librarian":
        query = query.filter(User.branch_id == current_user.branch_id)
        
    users = query.order_by(User.id.desc()).all()
    return [{
        "id": u.id,
        "member_id": u.member_id or "Pending Approval",
        "full_name": u.full_name,
        "email": u.email,
        "role": u.role,
        "branch_name": u.branch.name if u.branch else "Unassigned",
        "is_approved": u.is_approved,
        "is_active": u.is_active,
        "is_physically_verified": u.is_physically_verified,
        "created_at": u.created_at.strftime("%Y-%m-%d %H:%M")
    } for u in users]

@router.post("/create-staff")
async def create_staff(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    branch_id: int = Form(1),
    password: str = Form(None),
    phone: str = Form(None),
    ghana_card_number: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RBAC Enforcement: Librarians and Patrons CANNOT create staff
    if current_user.role not in ["sys_admin", "hq_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only System Administrators and HQ Administrators are authorized to provision staff accounts."
        )

    email_clean = email.lower().strip()
    if db.query(User).filter(User.email == email_clean).first():
        return JSONResponse(status_code=400, content={"error": f"An account with email '{email_clean}' already exists."})

    if phone and phone.strip() and db.query(User).filter(User.phone == phone.strip()).first():
        return JSONResponse(status_code=400, content={"error": f"An account with phone '{phone.strip()}' already exists."})

    target_pwd = password.strip() if (password and password.strip()) else f"Effutu@{random.randint(1000, 9999)}"
    role_clean = role.lower().strip()
    if role_clean not in ["librarian", "hq_admin", "sys_admin"]:
        role_clean = "librarian"

    prefix = "LIB" if role_clean == "librarian" else "ADMIN"
    member_id = f"EFL-{prefix}-{random.randint(1000, 9999)}"

    new_staff = User(
        full_name=full_name.strip(),
        email=email_clean,
        phone=phone.strip() if phone else None,
        ghana_card_number=ghana_card_number.strip().upper() if ghana_card_number else None,
        role=role_clean,
        branch_id=branch_id,
        member_id=member_id,
        hashed_password=get_password_hash(target_pwd),
        is_approved=True,
        is_active=True,
        verification_status="verified",
        is_physically_verified=True,
        must_change_password=True
    )
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    # Email Credentials Dispatch
    try:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        branch_name = branch.name if branch else "Effutu Municipal Network"
        base_url = str(request.base_url).rstrip('/')
        
        email_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
            <h2 style="color: #047857;">Staff Account Provisioned</h2>
            <p>Akwaaba <b>{full_name.strip()}</b>,</p>
            <p>Your official staff account has been created for the <b>{branch_name}</b>.</p>
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #cbd5e1; margin: 15px 0;">
                <p style="margin: 4px 0;"><b>Staff ID:</b> {member_id}</p>
                <p style="margin: 4px 0;"><b>Assigned Role:</b> {role_clean.replace('_', ' ').title()}</p>
                <p style="margin: 4px 0;"><b>Temporary Password:</b> <code style="background-color: #f1f5f9; padding: 4px 8px; font-weight: bold;">{target_pwd}</code></p>
            </div>
            <div style="background-color: #fef3c7; padding: 12px; border-left: 4px solid #f59e0b; margin: 15px 0;">
                <b>Mandatory Security Step:</b> You will be prompted to create your own custom password upon your first sign in.
            </div>
            <p><a href="{base_url}/auth/login" style="display: inline-block; padding: 10px 20px; background-color: #047857; color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">Access Staff Portal</a></p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 11px; color: #64748b;">Effutu Municipal Library Network Administration</p>
        </div>
        """
        send_email(email_clean, "Effutu Library - Staff Account Credentials", email_body)
    except Exception as ex:
        print(f"[STAFF PROVISIONING EMAIL DISPATCH WARNING] {ex}")

    return JSONResponse(content={
        "message": f"Staff account provisioned successfully for {full_name.strip()} ({role_clean.replace('_', ' ').title()})!",
        "member_id": member_id
    })
