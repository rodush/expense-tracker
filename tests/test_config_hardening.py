from __future__ import annotations

import pytest
from dotenv import load_dotenv

from app import config
from app.services.rule_engine import WhoRule


def test_settings_reject_empty_category_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CATEGORIES", "   ,  ")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    load_dotenv()

    with pytest.raises(ValueError, match="CATEGORIES"):
        config.Settings()


def test_settings_loads_validated_category_and_who_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CATEGORIES", "Meals,Unsorted")
    monkeypatch.setenv("FALLBACK_CATEGORY", "Unsorted")
    monkeypatch.setenv("WHO_RULES", '[{"contains":"card ending 1234","who":"Alex"}]')
    monkeypatch.setenv("WHO_UNMATCHED_LABEL", "Household")

    settings = config.Settings()

    assert settings.allowed_categories == ("Meals", "Unsorted")
    assert settings.fallback_category == "Unsorted"
    assert settings.who_rules == (WhoRule("card ending 1234", "Alex"),)
    assert settings.unmatched_who == "Household"


def test_settings_rejects_fallback_missing_from_category_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CATEGORIES", "Meals,Transport")
    monkeypatch.setenv("FALLBACK_CATEGORY", "Other")

    with pytest.raises(ValueError, match="Fallback category"):
        config.Settings()
