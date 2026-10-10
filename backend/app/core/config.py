import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ExamGuard AI API"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://examguard_user:examguard_password@localhost:5432/examguard_db"
    )
    
    # Security / Auth
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_key_change_in_production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Cookie Configuration
    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = os.getenv("ENVIRONMENT", "development") == "production"
    COOKIE_SAMESITE: str = "lax"
    
    # CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # AI Configuration
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
