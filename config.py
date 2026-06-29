import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App General Settings
    APP_NAME: str = "R8 Earn"
    SECRET_KEY: str = "SUPER_SECRET_JWT_SIGNING_KEY_CHANGE_THIS_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 1 Day
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = "1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    
    # Database Settings
    # Default to SQLite, can easily switch to PostgreSQL via env
    DATABASE_URL: str = "sqlite+aiosqlite:///./r8_earn.db"
    
    # Initial Admin Config (Created on startup if not present)
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "R8EarnLuxuryAdmin2026!"
    
    # Business Logic Defaults (Stored/Overridden by Database Settings Table later)
    DEFAULT_MIN_WITHDRAW: float = 500.0
    DEFAULT_MAX_WITHDRAW: float = 10000.0
    DEFAULT_REF_L1_REWARD: float = 10.0
    DEFAULT_REF_L2_REWARD: float = 5.0
    DEFAULT_REF_L3_REWARD: float = 2.0
    DEFAULT_DAILY_REWARD: float = 5.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
