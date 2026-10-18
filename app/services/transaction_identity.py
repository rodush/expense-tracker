from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from numbers import Real
from typing import Any

import pandas as pd

from app.services.dataset_store import parse_amount


def normalize_transaction_date(value: Any, date_format: str = "%Y%m%d") -> str:
    """Return the bank's calendar date as ISO-8601 for storage and identity."""
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return (
            value.date().isoformat()
            if isinstance(value, datetime)
            else value.isoformat()
        )

    if isinstance(value, bool) or value is None or pd.isna(value):
        raise ValueError("date must be a valid transaction date")

    is_numeric_date = isinstance(value, (Real, Decimal))
    if isinstance(value, str):
        text = value.strip()
        is_numeric_date = text.isdecimal()
    else:
        text = str(value).strip()
        if is_numeric_date:
            try:
                numeric_value = Decimal(text)
            except InvalidOperation:
                raise ValueError("date must be a valid transaction date") from None
            if (
                not numeric_value.is_finite()
                or numeric_value != numeric_value.to_integral_value()
            ):
                raise ValueError("date must be a valid transaction date")
            text = str(int(numeric_value))

    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass

    try:
        return date.strptime(text, date_format).isoformat()
    except ValueError:
        if is_numeric_date:
            raise ValueError("date must be a valid transaction date") from None

    if isinstance(value, str):
        try:
            parsed = pd.to_datetime(text, dayfirst=True, errors="coerce")
        except TypeError, ValueError:
            parsed = pd.NaT
    else:
        parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError("date must be a valid transaction date")
    return parsed.date().isoformat()


def _stable_value(value: Any) -> Any:
    if value is None:
        return None
    missing = pd.isna(value)
    if not hasattr(missing, "__len__") and bool(missing):
        return None
    if isinstance(value, (date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        try:
            return format(Decimal(str(value)).normalize(), "f")
        except InvalidOperation, ValueError:
            return str(value)
    normalized = unicodedata.normalize("NFKC", str(value))
    return " ".join(normalized.casefold().split())


def record_keys(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Fingerprint source transaction fields, preserving duplicate occurrences.

    The bank export currently has no declared stable transaction identifier in
    the application contract. All source fields therefore contribute to the
    fingerprint; category and who are derived values and do not. An occurrence
    ordinal preserves repeated identical rows within a single export.
    """
    occurrences: defaultdict[str, int] = defaultdict(int)
    keys: list[str] = []
    for row in rows:
        source_fields = {
            str(name).strip().casefold(): _stable_value(value)
            for name, value in row.items()
            if str(name).strip().casefold() not in {"category", "who"}
        }
        source_fields["date"] = normalize_transaction_date(row.get("date"))
        source_fields["amount"] = format(parse_amount(row.get("amount")), ".2f")
        canonical = json.dumps(
            source_fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        base_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        ordinal = occurrences[base_key]
        occurrences[base_key] += 1
        keys.append(hashlib.sha256(f"{base_key}:{ordinal}".encode()).hexdigest())
    return keys
