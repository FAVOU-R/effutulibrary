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

    # Email Configuration - Brevo SMTP Config
    MAIL_SERVER: str = os.getenv("EMAIL_HOST", os.getenv("MAIL_SERVER", "smtp-relay.brevo.com"))
    MAIL_PORT: int = int(os.getenv("EMAIL_PORT", os.getenv("MAIL_PORT", "587")))
    MAIL_USERNAME: str = os.getenv("EMAIL_USER", os.getenv("MAIL_USERNAME", "b4b291001@smtp-brevo.com"))
    MAIL_PASSWORD: str = os.getenv("EMAIL_PASS", os.getenv("MAIL_PASSWORD", "xsmtpsib-73752bcefb7d8f83cea4ea97251db06731fb9674d2b9611b992b6fd596cb80db-nTxr2DoejSu2wJjo"))
    SENDER_EMAIL: str = os.getenv("EMAIL_FROM", os.getenv("SENDER_EMAIL", "effutulibrarynetwork@gmail.com"))
    SENDER_NAME: str = os.getenv("EMAIL_FROM_NAME", "Effutu Library Network")

    # Library Rules
    LOAN_PERIOD_DAYS: int = 14
    DAILY_FINE_GHS: float = 0.50

settings = Settings()
