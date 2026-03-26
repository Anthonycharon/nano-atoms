from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./nano_atoms.db"
    SECRET_KEY: str = "change-this-to-a-random-secret-key-at-least-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: int = 120
    ARCHITECT_PAGE_CONCURRENCY: int = 3
    OPENAI_IMAGE_API_KEY: str = ""
    OPENAI_IMAGE_BASE_URL: str = ""
    OPENAI_IMAGE_MODEL: str = "gpt-image-1"
    OPENAI_IMAGE_ENABLED: bool = True
    OPENAI_IMAGE_MAX_ASSETS: int = 4
    OPENAI_IMAGE_CONCURRENCY: int = 2

    FRONTEND_URL: str = "http://localhost:3000"
    PUBLIC_BACKEND_URL: str = "http://127.0.0.1:8000"
    UPLOAD_DIR: str = "./uploads"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
