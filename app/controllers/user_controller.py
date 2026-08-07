from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.controllers.auth_controller import get_current_user

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
