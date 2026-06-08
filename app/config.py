from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./data/sales_assistant.db")
    catalog_path: Path = Field(default=Path("catalog.json"))
    confidence_flag_threshold: float = Field(default=0.55)

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
