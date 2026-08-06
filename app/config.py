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

    # Email Configuration
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", os.getenv("BREVO_SMTP_SERVER", "smtp-relay.brevo.com"))
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", os.getenv("BREVO_SMTP_PORT", "587")))
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", os.getenv("BREVO_SMTP_USER", ""))
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", os.getenv("BREVO_SMTP_PASSWORD", ""))
    BREVO_SMTP_SERVER: str = MAIL_SERVER
    BREVO_SMTP_PORT: int = MAIL_PORT
    BREVO_SMTP_USER: str = MAIL_USERNAME
    BREVO_SMTP_PASSWORD: str = MAIL_PASSWORD
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "noreply@effutulibrary.gov.gh")


    # Library Rules
    LOAN_PERIOD_DAYS: int = 14
    DAILY_FINE_GHS: float = 0.50

settings = Settings()
