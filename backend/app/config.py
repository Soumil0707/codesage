"""CodeSage backend configuration."""
from typing import Any
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CodeSage"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "mysql+aiomysql://codesage_user:codesage_pass_2024@localhost:3306/codesage"
    DATABASE_URL_SYNC: str = "mysql+pymysql://codesage_user:codesage_pass_2024@localhost:3306/codesage"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # Auth
    SECRET_KEY: str = "super-secret-key-change-in-production-2024"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Upload
    UPLOAD_DIR: str = "uploads"
    UPLOAD_MAX_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = ".py,.js,.ts,.java,.jsx,.tsx,.json,.md,.txt,.yaml,.yml,.xml,.html,.css,.sql,.sh,.cfg,.ini,.toml,.lock"

    # GitHub
    GITHUB_TOKEN: str = ""

    # LLM
    LLM_PROVIDER: str = "openai"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT: int = 60

    def model_post_init(self, __context: Any) -> None:
        if self.GROQ_API_KEY or self.LLM_PROVIDER.lower() == "groq":
            if not self.LLM_API_KEY and self.GROQ_API_KEY:
                self.LLM_API_KEY = self.GROQ_API_KEY
            if self.LLM_API_BASE == "https://api.openai.com/v1":
                self.LLM_API_BASE = "https://api.groq.com/openai/v1"
            if self.LLM_MODEL == "gpt-4o-mini" and self.GROQ_MODEL:
                self.LLM_MODEL = self.GROQ_MODEL
        elif self.OPENAI_API_KEY and not self.LLM_API_KEY:
            self.LLM_API_KEY = self.OPENAI_API_KEY
            if self.OPENAI_MODEL:
                self.LLM_MODEL = self.OPENAI_MODEL

    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    # Worker
    WORKER_CONCURRENCY: int = 2
    WORKER_POLL_INTERVAL: int = 5
    JOB_TIMEOUT: int = 600
    JOB_MAX_RETRIES: int = 3

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [e.strip() for e in self.ALLOWED_EXTENSIONS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
