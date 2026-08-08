from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Branch, User, BookCopy
from app.controllers.auth_controller import get_current_user

router = APIRouter(prefix="/api/branches", tags=["Branch Management"])

@router.get("")
def list_branches(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.id).all()
    return [{"id": b.id, "code": b.code, "name": b.name, "location": b.location, "status": b.status, "is_hq": b.is_hq} for b in branches]

@router.get("/active")
def list_active_branches(db: Session = Depends(get_db)):
    branches = db.query(Branch).filter(Branch.status == "active").order_by(Branch.name).all()
    return [{"id": b.id, "code": b.code, "name": b.name, "location": b.location} for b in branches]

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
    if current_user.role not in ["sys_admin", "hq_admin"]:
        raise HTTPException(status_code=403, detail="Only System / HQ Admin can add new library branches")
    
    new_br = Branch(code=code.upper(), name=name, location=location, status=status, is_hq=is_hq)
    db.add(new_br)
    db.commit()
    db.refresh(new_br)
    return JSONResponse(content={"message": "Branch created successfully", "branch_id": new_br.id})

@router.post("/{branch_id}/edit")
@router.post("/edit/{branch_id}")
def edit_branch(
    branch_id: int,
    code: str = Form(None),
    name: str = Form(...),
    location: str = Form(...),
    status: str = Form("active"),
    is_hq: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["sys_admin", "hq_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    br = db.query(Branch).filter(Branch.id == branch_id).first()
    if not br:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    if code:
        br.code = code.strip().upper()
    br.name = name.strip()
    br.location = location.strip()
    br.status = status
    br.is_hq = is_hq
    db.commit()
    return JSONResponse(content={"message": f"Branch '{br.name}' updated successfully!"})

@router.post("/{branch_id}/toggle")
@router.post("/toggle-status/{branch_id}")
def toggle_branch_status(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["sys_admin", "hq_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    br = db.query(Branch).filter(Branch.id == branch_id).first()
    if not br:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    br.status = "target" if br.status == "active" else "active"
    db.commit()
    return JSONResponse(content={"message": f"Branch status for '{br.name}' changed to {br.status.upper()}!"})

@router.post("/{branch_id}/delete")
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["sys_admin", "hq_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    br = db.query(Branch).filter(Branch.id == branch_id).first()
    if not br:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check if branch has users or book copies attached
    user_count = db.query(User).filter(User.branch_id == branch_id).count()
    copy_count = db.query(BookCopy).filter(BookCopy.branch_id == branch_id).count()
    
    if user_count > 0 or copy_count > 0:
        return JSONResponse(status_code=400, content={"error": f"Cannot delete branch: {user_count} users and {copy_count} book copies are assigned to this branch. Deactivate instead."})
    
    db.delete(br)
    db.commit()
    return JSONResponse(content={"message": "Branch deleted successfully"})
