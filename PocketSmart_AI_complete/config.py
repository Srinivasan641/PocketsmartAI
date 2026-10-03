import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    app_name: str = "PocketSmart AI"
    secret_key: str = os.getenv("SECRET_KEY", "change-this-secret-in-production")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///pocketsmart.db")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "5"))

settings = Settings()
