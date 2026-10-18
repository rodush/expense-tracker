from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from pytest import MonkeyPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import local_heuristics


def test_uses_specific_categories_when_configured(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        local_heuristics,
        "settings",
        SimpleNamespace(
            allowed_categories=(
                "Grocery",
                "Restaurants",
                "Public transport",
                "Utilities",
                "Other",
            )
        ),
    )

    assert local_heuristics.classify_description("Albert Heijn 1516") == "Grocery"
    assert local_heuristics.classify_description("Barista Cafe") == "Restaurants"
    assert local_heuristics.classify_description("OV-chipkaart opladen") == (
        "Public transport"
    )


def test_maps_to_starter_vocabulary_when_specific_category_is_unavailable(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        local_heuristics,
        "settings",
        SimpleNamespace(allowed_categories=("Food", "Transport", "Utilities", "Other")),
    )

    assert local_heuristics.classify_description("Albert Heijn 1516") == "Food"
    assert local_heuristics.classify_description("OV-chipkaart opladen") == "Transport"
    assert local_heuristics.classify_description("PWN Waterleidingbedrijf") == (
        "Utilities"
    )
