from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

from dotenv import load_dotenv

from app.services.rule_engine import (
    WhoRule,
    parse_who_rules,
    validate_category_configuration,
)


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
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "sqlite:///./expense-tracker.db"
        )
    )
    transaction_date_format: str = field(
        default_factory=lambda: os.getenv("TRANSACTION_DATE_FORMAT", "%Y%m%d").strip()
    )
    allowed_categories: tuple[str, ...] = field(
        default_factory=lambda: _parse_categories(
            os.getenv("CATEGORIES", "Food,Transport,Utilities,Shopping,Other")
        )
    )
    fallback_category: str = field(
        default_factory=lambda: os.getenv("FALLBACK_CATEGORY", "Other").strip()
    )
    who_rules: tuple[WhoRule, ...] = field(
        default_factory=lambda: parse_who_rules(os.getenv("WHO_RULES"))
    )
    unmatched_who: str = field(
        default_factory=lambda: os.getenv("WHO_UNMATCHED_LABEL", "General").strip()
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
        if not self.database_url.strip():
            raise ValueError("DATABASE_URL must not be empty")
        sample_date = date(2000, 2, 3)
        try:
            formatted_sample = sample_date.strftime(self.transaction_date_format)
            parsed_sample = date.strptime(
                formatted_sample, self.transaction_date_format
            )
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "TRANSACTION_DATE_FORMAT must be a valid date format including year, month, and day"
            ) from exc
        if parsed_sample != sample_date:
            raise ValueError(
                "TRANSACTION_DATE_FORMAT must include year, month, and day"
            )
        validate_category_configuration(self.allowed_categories, self.fallback_category)
        if not self.unmatched_who:
            raise ValueError("WHO_UNMATCHED_LABEL must not be empty")


settings = Settings()
