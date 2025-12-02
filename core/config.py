"""
Application configuration management
"""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # App Settings
    app_name: str = "Harmoni AI News API"
    debug: bool = os.environ.get("DEBUG", "false").lower() == "true"
    
    # Database
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./news.db")
    
    # Security
    secret_key: str = os.environ.get("SECRET_KEY", "dev_secret_key_1234")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day
    cron_secret_key: str = os.environ.get("CRON_SECRET_KEY", "")
    
    # Naver API
    naver_client_id: str = os.environ.get("NAVER_CLIENT_ID", "")
    naver_client_secret: str = os.environ.get("NAVER_CLIENT_SECRET", "")
    naver_redirect_uri: str = os.environ.get(
        "NAVER_REDIRECT_URI", 
        "https://sdhs-webapp-2025.onrender.com/auth/naver/callback"
    )
    
    # Google OAuth
    google_client_id: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.environ.get(
        "GOOGLE_REDIRECT_URI",
        "https://sdhs-webapp-2025.onrender.com/google/callback"
    )
    
    # Perplexity AI API
    pplx_api_key: str = os.environ.get("PPLX_API_KEY", "")
    
    @property
    def sqlalchemy_database_url(self) -> str:
        """Get SQLAlchemy-compatible database URL"""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
