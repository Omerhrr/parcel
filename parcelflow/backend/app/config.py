"""
Application Configuration Settings
ParcelFlow - Multi-tenant Logistics Platform
"""
import os
import secrets
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


def generate_secret_key() -> str:
    """Generate a secure secret key"""
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "ParcelFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False  # Default to False for security
    ENVIRONMENT: str = "production"
    
    # Database
    DATABASE_URL: str = "sqlite:///./parcelflow.db"
    # For production: postgresql://user:password@localhost/parcelflow
    
    # JWT Authentication
    # IMPORTANT: Set SECRET_KEY environment variable in production!
    # Use: python -c "import secrets; print(secrets.token_urlsafe(32))"
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")  # No default - must be set
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours (reduced from 24 for security)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS - must be explicitly configured
    CORS_ORIGINS: List[str] = []
    
    # Frontend URLs
    FRONTEND_URL: str = "http://localhost:5000"
    WEBSITE_URL: str = "http://localhost:5001"
    
    # Email Settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    
    # Email Sender Information
    EMAIL_FROM_NAME: str = "ParcelFlow"
    EMAIL_FROM_ADDRESS: Optional[str] = None  # Defaults to SMTP_USER if not set
    
    # Email Development Mode
    EMAIL_DEV_MODE: bool = False  # If True, prints emails to console instead of sending
    EMAIL_TEMPLATES_DIR: str = "./app/templates/emails"
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Security Settings
    SECURE_COOKIES: bool = True
    SESSION_TIMEOUT_MINUTES: int = 60
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Generate a random secret key if not set (development only)
        if not self.SECRET_KEY:
            if self.ENVIRONMENT == "development" or self.DEBUG:
                self.SECRET_KEY = "dev-only-insecure-key-" + secrets.token_urlsafe(16)
                import warnings
                warnings.warn(
                    "Using auto-generated SECRET_KEY. Set SECRET_KEY environment variable for production!",
                    UserWarning
                )
            else:
                raise ValueError(
                    "SECRET_KEY environment variable must be set in production! "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
        
        # Set default CORS origins for development
        if not self.CORS_ORIGINS and (self.ENVIRONMENT == "development" or self.DEBUG):
            self.CORS_ORIGINS = ["http://localhost:5000", "http://localhost:3000"]
        
        # Enable email dev mode in development if SMTP not configured
        if not self.SMTP_HOST and (self.ENVIRONMENT == "development" or self.DEBUG):
            self.EMAIL_DEV_MODE = True
    
    @property
    def email_from_address(self) -> str:
        """Get the email from address, defaults to SMTP_USER"""
        return self.EMAIL_FROM_ADDRESS or self.SMTP_USER or "noreply@parcelflow.com"
    
    @property
    def email_configured(self) -> bool:
        """Check if email is properly configured"""
        return bool(self.SMTP_HOST and self.SMTP_USER)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
