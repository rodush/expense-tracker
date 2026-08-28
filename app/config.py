from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

def _parse_categories(raw_value: str) -> tuple[str, ...]:
    raw_value = raw_value.strip()

    if not raw_value:
        raise ValueError("CATEGORIES must contain at least one category")

    categories = tuple(category.strip() for category in raw_value.split(",") if category.strip())
    if not categories:
        raise ValueError("CATEGORIES must contain at least one category")

    return categories


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "expense-categorizer"
    gemini_api_key: str | None = None
    allowed_categories: tuple[str, ...] = field(default_factory=lambda: _parse_categories(os.getenv("CATEGORIES", "Grocery,Transport,Utilities,Shopping,Other")))

    def __post_init__(self) -> None:
        if not self.gemini_api_key:
            object.__setattr__(self, "gemini_api_key", os.getenv("GEMINI_API_KEY"))


settings = Settings()
