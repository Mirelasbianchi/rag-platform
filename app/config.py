from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://rag:rag@localhost:5432/rag"
    embedding_model: str = "local/hashing"
    embedding_dim: int = 1536
    chunk_size: int = 800
    chunk_overlap: int = 100
    llm_model: str | None = None  # e.g. anthropic/claude-sonnet-4-5; unset = extractive


@lru_cache
def get_settings() -> Settings:
    return Settings()
