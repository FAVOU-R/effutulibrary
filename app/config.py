import os

class Settings:
    PROJECT_NAME: str = "Effutu Municipal Library Management System"
    VERSION: str = "1.0.0"
    
    # Database URL configuration (Postgres with SQLite local fallback)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./effutu_library.db"
    )
    # Fix for Heroku/Render postgres:// vs postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # JWT & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "effutu-lib-secret-key-ghana-2026-central-region")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours

    # Email Configuration - Env Vars Only
    MAIL_SERVER: str = os.getenv("EMAIL_HOST", "smtp-relay.brevo.com")
    MAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
    MAIL_USERNAME: str = os.getenv("EMAIL_USER", "")
    MAIL_PASSWORD: str = os.getenv("EMAIL_PASS", "")
    SENDER_EMAIL: str = os.getenv("EMAIL_FROM", "effutulibrarynetwork@gmail.com")
    SENDER_NAME: str = os.getenv("EMAIL_FROM_NAME", "Effutu Library Network")

    # Library Rules & Borrowing Limits
    LOAN_PERIOD_DAYS: int = 14
    DAILY_FINE_GHS: float = 0.50
    MAX_BOOKS_PER_PATRON: int = int(os.getenv("MAX_BOOKS_PER_PATRON", "3"))

    # Security & Password Policies
    MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    ACCOUNT_LOCKOUT_MINUTES: int = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "15"))

settings = Settings()

