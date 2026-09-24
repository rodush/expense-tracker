from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


def _parse_categories(raw_value: str) -> tuple[str, ...]:
    raw_value = raw_value.strip()

    if not raw_value:
        raise ValueError("CATEGORIES must contain at least one category")

    categories = tuple(
        category.strip() for category in raw_value.split(",") if category.strip()
    )
    if not categories:
        raise ValueError("CATEGORIES must contain at least one category")

    return categories


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "expense-categorizer"
    gemini_api_key: str | None = None
    log_level: str = "INFO"
    log_format: str = "json"
    allowed_categories: tuple[str, ...] = field(
        default_factory=lambda: _parse_categories(
            os.getenv("CATEGORIES", "Food,Transport,Utilities,Shopping,Other")
        )
    )

    def __post_init__(self) -> None:
        if not self.gemini_api_key:
            object.__setattr__(self, "gemini_api_key", os.getenv("GEMINI_API_KEY"))
        object.__setattr__(
            self, "log_level", os.getenv("LOG_LEVEL", self.log_level).upper()
        )
        object.__setattr__(
            self, "log_format", os.getenv("LOG_FORMAT", self.log_format).lower()
        )
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be a standard logging level")
        if self.log_format not in {"json", "text"}:
            raise ValueError("LOG_FORMAT must be either json or text")


settings = Settings()
