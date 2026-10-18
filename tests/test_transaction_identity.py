from __future__ import annotations

from app.services.transaction_identity import normalize_transaction_date, record_keys


def test_normalizes_iso_and_dutch_dates_without_swapping_day_and_month() -> None:
    assert normalize_transaction_date("2026-07-01") == "2026-07-01"
    assert normalize_transaction_date("01-07-2026") == "2026-07-01"


def test_normalizes_numeric_yyyymmdd_values() -> None:
    assert normalize_transaction_date(20260701) == "2026-07-01"
    assert normalize_transaction_date(20260701.0) == "2026-07-01"
    assert normalize_transaction_date("20260701") == "2026-07-01"


def test_normalizes_dates_with_a_configured_format() -> None:
    assert normalize_transaction_date("01/07/2026", "%d/%m/%Y") == "2026-07-01"


def test_record_keys_ignore_derived_fields_and_preserve_repeated_rows() -> None:
    row = {
        "date": "2026-07-01",
        "amount": -10.0,
        "description": "  Coffee Shop ",
        "category": "Food",
        "who": "Roman",
    }
    repeated_with_reclassification = {
        **row,
        "description": "coffee shop",
        "category": "Shopping",
        "who": "Oksana",
    }

    keys = record_keys([row, repeated_with_reclassification, row])

    assert len(set(keys)) == 3
    assert keys == record_keys([row, repeated_with_reclassification, row])
    assert keys[0] != keys[1]


def test_record_key_changes_when_a_source_field_changes() -> None:
    first = {"date": "2026-07-01", "amount": -10, "description": "Coffee"}
    second = {**first, "description": "Coffee with milk"}

    assert record_keys([first, second])[0] != record_keys([first, second])[1]
