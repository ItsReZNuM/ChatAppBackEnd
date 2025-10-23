from pydantic import BaseModel
import os

class Settings(BaseModel):
    DATABASE_URL_SYNC: str = os.getenv("DATABASE_URL")
    DATABASE_URL_ASYNC: str = os.getenv("ASYNC_DATABASE_URL")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

settings = Settings()
