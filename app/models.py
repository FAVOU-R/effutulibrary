import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
from app.database import Base

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    location = Column(String(200), nullable=False)
    status = Column(String(20), default="active") # active, target, inactive
    is_hq = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    users = relationship("User", back_populates="branch")
    copies = relationship("BookCopy", back_populates="branch")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=True)
    member_id = Column(String(50), unique=True, index=True, nullable=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False) # sys_admin, hq_admin, librarian, patron
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    ghana_card_number = Column(String(50), unique=True, index=True, nullable=True)
    id_type = Column(String(50), default="ghanacard", nullable=True)
    id_number = Column(String(50), nullable=True)
    alt_contact = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    sex = Column(String(20), nullable=True) # Male, Female
    school_occupation = Column(String(150), nullable=True)
    location = Column(String(150), nullable=True)
    verification_status = Column(String(30), default="pending", nullable=True) # pending, verified, rejected
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    id_photo_url = Column(String(255), nullable=True)
    profile_picture_url = Column(String(255), nullable=True)
    guardian_name = Column(String(150), nullable=True)
    guardian_phone = Column(String(50), nullable=True)
    guardian_email = Column(String(150), nullable=True)
    guardian_relationship = Column(String(50), nullable=True)
    is_approved = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=True)
    is_physically_verified = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0, nullable=True)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def avatar_url(self):
        if self.profile_picture_url and self.profile_picture_url.strip():
            return self.profile_picture_url
        if self.id_photo_url and self.id_photo_url.strip():
            return self.id_photo_url
        return None

    @property
    def display_username(self):
        if self.username:
            return f"@{self.username.lstrip('@')}"
        if self.email:
            return f"@{self.email.split('@')[0]}"
        if self.member_id:
            return f"@{self.member_id.lower()}"
        return f"@{self.full_name.lower().replace(' ', '_')}"


    branch = relationship("Branch", back_populates="users")
    transactions = relationship("Transaction", foreign_keys="Transaction.patron_id", back_populates="patron")
    notifications = relationship("Notification", back_populates="user")

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    isbn = Column(String(30), unique=True, index=True, nullable=True)
    publisher = Column(String(150), nullable=True)
    pub_year = Column(Integer, nullable=True)
    pages = Column(Integer, nullable=True)
    category = Column(String(100), default="General")
    cover_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    copies = relationship("BookCopy", back_populates="book", cascade="all, delete-orphan")

class BookCopy(Base):
    __tablename__ = "book_copies"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    copy_code = Column(String(50), unique=True, nullable=False)
    qr_token = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(30), default="available") # available, issued, maintenance, reserved
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    book = relationship("Book", back_populates="copies")
    branch = relationship("Branch", back_populates="copies")
    transactions = relationship("Transaction", back_populates="book_copy")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    book_copy_id = Column(Integer, ForeignKey("book_copies.id"), nullable=False)
    patron_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    issued_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    issue_date = Column(DateTime, default=datetime.datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    fine_amount = Column(Float, default=0.00)
    status = Column(String(30), default="active") # active, returned, overdue

    book_copy = relationship("BookCopy", back_populates="transactions")
    patron = relationship("User", foreign_keys=[patron_id], back_populates="transactions")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="info")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    status = Column(String(30), default="reserved") # reserved, ready, collected, cancelled, rejected, expired
    reject_reason = Column(Text, nullable=True)
    reserved_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User")
    book = relationship("Book")

class UserPoint(Base):
    __tablename__ = "user_points"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    points = Column(Integer, nullable=False)
    reason = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")

class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    query = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(100), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
