from __future__ import annotations

import json

import pytest

from app.services.rule_engine import (
    DEFAULT_WHO_RULES,
    WhoRule,
    determine_who,
    heuristic_category,
    normalize_category,
    parse_who_rules,
    validate_category_configuration,
)


def test_default_who_rules_preserve_current_detection() -> None:
    assert determine_who("Purchase from PAS543") == "Roman"
    assert determine_who("Kaartnummer: **5006 payment") == "Oksana"
    assert determine_who("Unknown card") == "General"
    assert parse_who_rules(None) == DEFAULT_WHO_RULES


def test_custom_who_rules_use_case_insensitive_literal_first_match() -> None:
    rules = parse_who_rules(
        json.dumps(
            [
                {"contains": "card: 1234", "who": "Alex"},
                {"contains": "member 5678", "who": "Sam"},
            ]
        )
    )

    assert rules == (
        WhoRule(contains="card: 1234", who="Alex"),
        WhoRule(contains="member 5678", who="Sam"),
    )
    assert determine_who("Payment from CARD: 1234", rules) == "Alex"
    assert determine_who("MEMBER 5678", rules) == "Sam"
    assert determine_who("unmatched", (), "Household") == "Household"


@pytest.mark.parametrize(
    "raw_rules",
    [
        "not-json",
        "{}",
        '[{"contains":"x", "who":"Alex", "regex":".*"}]',
        '[{"contains":"", "who":"Alex"}]',
        '[{"contains":"x", "who":" "}]',
        '[{"contains":"x", "who":"Alex"}, {"contains":"X", "who":"Sam"}]',
        "[{}]",
    ],
)
def test_invalid_who_rule_formats_are_rejected(raw_rules: str) -> None:
    with pytest.raises(ValueError, match="WHO_RULES"):
        parse_who_rules(raw_rules)


def test_who_rule_input_is_bounded() -> None:
    too_many_rules = json.dumps(
        [{"contains": f"marker-{index}", "who": "Alex"} for index in range(101)]
    )
    with pytest.raises(ValueError, match="at most"):
        parse_who_rules(too_many_rules)

    long_marker = json.dumps([{"contains": "x" * 257, "who": "Alex"}])
    with pytest.raises(ValueError, match="marker exceeds"):
        parse_who_rules(long_marker)


def test_category_normalization_uses_configured_categories_and_fallback() -> None:
    configured_categories = ("Meals", "Unsorted")
    assert normalize_category("Meals", configured_categories, "Unsorted") == "Meals"
    assert (
        normalize_category("Shopping", configured_categories, "Unsorted") == "Unsorted"
    )
    assert normalize_category(None, configured_categories, "Unsorted") == "Unsorted"


def test_heuristic_only_returns_configured_category_or_fallback() -> None:
    assert (
        heuristic_category("Coffee at a cafe", ("Food", "Unknown"), "Unknown") == "Food"
    )
    assert (
        heuristic_category("Coffee at a cafe", ("Meals", "Unknown"), "Unknown")
        == "Unknown"
    )


@pytest.mark.parametrize(
    ("categories", "fallback"),
    [
        ((), "Other"),
        (("Food", "Food"), "Food"),
        (("Food",), "Other"),
        (("Food", ""), "Food"),
    ],
)
def test_invalid_category_configuration_is_rejected(
    categories: tuple[str, ...], fallback: str
) -> None:
    with pytest.raises(ValueError):
        validate_category_configuration(categories, fallback)
