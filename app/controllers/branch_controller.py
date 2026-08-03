from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Branch, User
from app.controllers.auth_controller import get_current_user

router = APIRouter(prefix="/api/branches", tags=["Branches"])

@router.get("")
def list_branches(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id).all()
    return [{
        "id": b.id,
        "code": b.code,
        "name": b.name,
        "location": b.location,
        "status": b.status,
        "is_hq": b.is_hq
    } for b in branches]

@router.post("/add")
def create_branch(
    code: str = Form(...),
    name: str = Form(...),
    location: str = Form(...),
    status: str = Form("active"),
    is_hq: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "sys_admin":
        raise HTTPException(status_code=403, detail="Only System Admin can create new branches")

    existing = db.query(Branch).filter(Branch.code == code.upper().strip()).first()
    if existing:
        return JSONResponse(status_code=400, content={"error": f"Branch code '{code}' already exists"})

    branch = Branch(
        code=code.upper().strip(),
        name=name.strip(),
        location=location.strip(),
        status=status,
        is_hq=is_hq
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)

    return JSONResponse(content={"message": f"Branch '{branch.name}' created successfully", "id": branch.id})

@router.post("/toggle-status/{branch_id}")
def toggle_branch_status(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "sys_admin":
        raise HTTPException(status_code=403, detail="Only System Admin can update branch status")

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        return JSONResponse(status_code=404, content={"error": "Branch not found"})

    branch.status = "active" if branch.status != "active" else "target"
    db.commit()

    return JSONResponse(content={"message": f"Branch {branch.code} status updated to {branch.status}"})
