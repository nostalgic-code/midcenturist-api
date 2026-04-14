import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    ADMIN_JWT_SECRET = os.environ.get("ADMIN_JWT_SECRET", "admin-secret-change-in-production")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

    # Payment gateways
    PAYFAST_MERCHANT_ID = os.environ.get("PAYFAST_MERCHANT_ID", "")
    PAYFAST_MERCHANT_KEY = os.environ.get("PAYFAST_MERCHANT_KEY", "")
    PAYFAST_PASSPHRASE = os.environ.get("PAYFAST_PASSPHRASE", "")
    PAYFAST_SANDBOX = os.environ.get("PAYFAST_SANDBOX", "true").lower() == "true"

    YOCO_SECRET_KEY = os.environ.get("YOCO_SECRET_KEY", "")
    YOCO_SANDBOX = os.environ.get("YOCO_SANDBOX", "true").lower() == "true"

    # Instagram / Meta Graph API
    INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

    # Email (Resend)
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    CLIENT_EMAIL = os.environ.get("CLIENT_EMAIL", "")
    FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@midcenturist.co.za")

    # CORS
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001"
    ).split(",")

    # Rate limiting storage (use Redis in production)
    RATELIMIT_STORAGE_URL = os.environ.get("REDIS_URL", "memory://")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/midcenturist_dev"
    )
    WTF_CSRF_ENABLED = False  # disable in dev for easier API testing


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")

    # Render provides DATABASE_URL with postgres:// prefix — SQLAlchemy needs postgresql://
    @classmethod
    def init_app(cls, app):
        db_url = cls.SQLALCHEMY_DATABASE_URI
        if db_url and db_url.startswith("postgres://"):
            cls.SQLALCHEMY_DATABASE_URI = db_url.replace("postgres://", "postgresql://", 1)


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
