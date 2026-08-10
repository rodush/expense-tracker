from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _parse_categories(raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None:
        raw_value = "Grocery,Transport,Utilities,Shopping,Other"
    else:
        raw_value = raw_value.strip()

    if not raw_value:
        raise ValueError("CATEGORIES must contain at least one category")

    categories = tuple(category.strip() for category in raw_value.split(",") if category.strip())
    if not categories:
        raise ValueError("CATEGORIES must contain at least one category")

    return categories


def load_environment() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_environment()


@dataclass(frozen=True)
class Settings:
    app_name: str = "expense-categorizer"
    gemini_api_key: str | None = None
    allowed_categories: tuple[str, ...] = field(default_factory=lambda: _parse_categories(os.getenv("CATEGORIES", "Grocery,Transport,Utilities,Shopping,Other")))

    def __post_init__(self) -> None:
        if not self.gemini_api_key:
            object.__setattr__(self, "gemini_api_key", os.getenv("GEMINI_API_KEY"))


settings = Settings()
