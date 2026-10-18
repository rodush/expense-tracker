"""Validated, deterministic rules used while processing expense descriptions.

Who rules intentionally support literal substring matching only. Keeping the
format constrained avoids executable expressions and makes configured rules
portable to a future database-backed configuration store.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WhoRule:
    """Match a literal marker in a description to a configured person label."""

    contains: str
    who: str


DEFAULT_WHO_RULES = (
    WhoRule(contains="pas543", who="Roman"),
    WhoRule(contains="kaartnummer: **5006", who="Oksana"),
)

MAX_WHO_RULES = 100
MAX_RULE_MARKER_LENGTH = 256
MAX_WHO_LABEL_LENGTH = 100

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Food",
        (
            "coffee",
            "restaurant",
            "cafe",
            "food",
            "lunch",
            "dinner",
            "grocer",
            "grocery",
            "bakery",
        ),
    ),
    (
        "Transport",
        (
            "uber",
            "lyft",
            "taxi",
            "train",
            "metro",
            "fuel",
            "petrol",
            "parking",
            "bus",
            "rail",
        ),
    ),
    (
        "Utilities",
        (
            "electricity",
            "water",
            "gas",
            "internet",
            "phone",
            "utility",
            "mobile",
            "bill",
        ),
    ),
    (
        "Shopping",
        (
            "amazon",
            "shop",
            "store",
            "market",
            "retail",
            "purchase",
            "clothes",
            "electronics",
        ),
    ),
)


def validate_category_configuration(
    allowed_categories: tuple[str, ...], fallback_category: str
) -> None:
    """Raise ``ValueError`` if categories or their fallback are inconsistent."""
    if not allowed_categories or any(
        not category.strip() for category in allowed_categories
    ):
        raise ValueError("At least one non-empty category must be configured")
    if len(set(allowed_categories)) != len(allowed_categories):
        raise ValueError("Configured category names must be unique")
    if fallback_category not in allowed_categories:
        raise ValueError("Fallback category must be included in configured categories")


def normalize_category(
    raw_category: Any,
    allowed_categories: tuple[str, ...],
    fallback_category: str,
) -> str:
    """Return a configured category, or the configured fallback for unknown input."""
    validate_category_configuration(allowed_categories, fallback_category)
    candidate = str(raw_category or "").strip()
    return candidate if candidate in allowed_categories else fallback_category


def heuristic_category(
    description: str,
    allowed_categories: tuple[str, ...],
    fallback_category: str,
) -> str:
    """Apply existing keyword rules, constrained to caller-provided categories."""
    validate_category_configuration(allowed_categories, fallback_category)
    description_lower = str(description or "").casefold()
    for category, keywords in _CATEGORY_KEYWORDS:
        if category in allowed_categories and any(
            keyword in description_lower for keyword in keywords
        ):
            return category
    return fallback_category


def parse_who_rules(raw_value: str | None) -> tuple[WhoRule, ...]:
    """Parse a JSON array of literal ``contains``/``who`` rules.

    ``None`` preserves the current Roman/Oksana rules. An empty JSON array
    disables marker matching. Rules are evaluated in listed order; the first
    matching marker wins.
    """
    if raw_value is None:
        return DEFAULT_WHO_RULES
    try:
        entries = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError("WHO_RULES must be a JSON array") from exc
    if not isinstance(entries, list):
        raise ValueError("WHO_RULES must be a JSON array")  # noqa: TRY004
    if len(entries) > MAX_WHO_RULES:
        raise ValueError(f"WHO_RULES must contain at most {MAX_WHO_RULES} rules")

    rules: list[WhoRule] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"contains", "who"}:
            raise ValueError(
                f"WHO_RULES entry {index} must contain only 'contains' and 'who'"
            )
        marker = _validated_text(entry["contains"], "contains", index)
        who = _validated_text(entry["who"], "who", index)
        if len(marker) > MAX_RULE_MARKER_LENGTH:
            raise ValueError(
                f"WHO_RULES entry {index} marker exceeds {MAX_RULE_MARKER_LENGTH} characters"
            )
        if len(who) > MAX_WHO_LABEL_LENGTH:
            raise ValueError(
                f"WHO_RULES entry {index} label exceeds {MAX_WHO_LABEL_LENGTH} characters"
            )
        rules.append(WhoRule(contains=marker, who=who))

    markers = [rule.contains.casefold() for rule in rules]
    if len(markers) != len(set(markers)):
        raise ValueError("WHO_RULES markers must be unique, ignoring case")
    return tuple(rules)


def _validated_text(value: Any, field_name: str, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"WHO_RULES entry {index} '{field_name}' must be a non-empty string"
        )
    return value.strip()


def determine_who(
    description: str,
    rules: tuple[WhoRule, ...] = DEFAULT_WHO_RULES,
    unmatched_who: str = "General",
) -> str:
    """Return the label for the first literal marker match, or the fallback."""
    normalized_description = str(description or "").casefold()
    for rule in rules:
        if rule.contains.casefold() in normalized_description:
            return rule.who
    if not unmatched_who.strip():
        raise ValueError("Unmatched who label must not be empty")
    return unmatched_who
