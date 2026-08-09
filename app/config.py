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

    # Brevo SMTP Configuration
    BREVO_SMTP_SERVER: str = os.getenv("BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
    BREVO_SMTP_PORT: int = int(os.getenv("BREVO_SMTP_PORT", "2525"))
    BREVO_SMTP_LOGIN: str = os.getenv("BREVO_SMTP_LOGIN", "b428a1001@smtp-brevo.com")
    BREVO_SMTP_KEY: str = os.getenv("BREVO_SMTP_KEY", "")
    BREVO_SENDER_EMAIL: str = os.getenv("BREVO_SENDER_EMAIL", "effutulibrarynetwork@gmail.com")
    BREVO_SENDER_NAME: str = os.getenv("BREVO_SENDER_NAME", "Effutu Library Network")

    # Library Rules & Borrowing Limits
    LOAN_PERIOD_DAYS: int = 14
    DAILY_FINE_GHS: float = 0.50
    MAX_BOOKS_PER_PATRON: int = int(os.getenv("MAX_BOOKS_PER_PATRON", "3"))

    # Security & Password Policies
    MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    ACCOUNT_LOCKOUT_MINUTES: int = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "15"))

settings = Settings()

