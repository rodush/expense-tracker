from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "expense-categorizer"
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    allowed_categories: tuple[str, ...] = tuple(
        category.strip()
        for category in os.getenv("CATEGORIES", "Food,Transport,Utilities,Shopping,Other").split(",")
        if category.strip()
    )


settings = Settings()
