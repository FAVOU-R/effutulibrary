from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Branch, User
from app.controllers.auth_controller import get_current_user

router = APIRouter(prefix="/api/branches", tags=["Branch Management"])

@router.get("")
def list_branches(db: Session = Depends(get_db)):
    branches = db.query(Branch).all()
    return [{"id": b.id, "code": b.code, "name": b.name, "location": b.location, "status": b.status, "is_hq": b.is_hq} for b in branches]

@router.post("")
def add_branch(
    name: str = Form(...),
    location: str = Form(...),
    code: str = Form(...),
    status: str = Form("active"),
    is_hq: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "sys_admin":
        raise HTTPException(status_code=403, detail="Only System Admin can add new library branches")
    
    new_br = Branch(code=code.upper(), name=name, location=location, status=status, is_hq=is_hq)
    db.add(new_br)
    db.commit()
    db.refresh(new_br)
    return JSONResponse(content={"message": "Branch created successfully", "branch_id": new_br.id})
