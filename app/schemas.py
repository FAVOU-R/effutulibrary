from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    branch_id: Optional[int] = None

class UserCreate(UserBase):
    password: str
    role: str = "patron"

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: int
    member_id: Optional[str]
    role: str
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Branch Schemas
class BranchBase(BaseModel):
    code: str
    name: str
    location: str
    status: str = "active"
    is_hq: bool = False

class BranchCreate(BranchBase):
    pass

class BranchResponse(BranchBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Book Schemas
class BookBase(BaseModel):
    title: str
    author: str
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    pub_year: Optional[int] = None
    pages: Optional[int] = None
    category: str = "General"
    cover_url: Optional[str] = None
    description: Optional[str] = None

class BookCreate(BookBase):
    initial_copies: int = 1
    branch_id: int

class BookResponse(BookBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Issue / Checkout Schemas
class IssueRequest(BaseModel):
    qr_token: str
    patron_id: Optional[int] = None # Optional if patron scans self-service

class ReturnRequest(BaseModel):
    transaction_id: int

# AI Request
class AIChatRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
