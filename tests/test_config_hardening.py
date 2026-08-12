from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app import config

def test_settings_reject_empty_category_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CATEGORIES", "   ,  ")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    load_dotenv()
    
    with pytest.raises(ValueError, match="CATEGORIES"):
        config.Settings()
