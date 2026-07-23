from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    allowed_categories: tuple[str, ...] = tuple(
        category.strip()
        for category in os.getenv("CATEGORIES", "Grocery,Transport,Utilities,Shopping,Other").split(",")
        if category.strip()
    )


settings = Settings()
