from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app import config


def test_settings_reject_empty_category_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CATEGORIES", "   ,  ")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    config.load_environment()

    with pytest.raises(ValueError, match="CATEGORIES"):
        config.Settings()
