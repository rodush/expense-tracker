from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import Iterable, Mapping
from typing import Any

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from app.config import settings
from app.services import rule_engine
from app.services.local_heuristics import (
    classify_description as _local_heuristic_category,
)

logger = logging.getLogger("expense_tracker.categorization")
GEMINI_MODEL = "gemini-2.5-flash"
BATCH_SIZE = 50
GEMINI_TIMEOUT_SECONDS = 15
GEMINI_MAX_RETRIES = 2
GEMINI_RETRY_DELAY_SECONDS = 0.1


def normalize_category(
    raw_category: str,
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
) -> str:
    return rule_engine.normalize_category(
        raw_category,
        allowed_categories or settings.allowed_categories,
        fallback_category or settings.fallback_category,
    )


def determine_who_from_description(description: str) -> str:
    return rule_engine.determine_who(
        description, settings.who_rules, settings.unmatched_who
    )


def _heuristic_category(
    description: str,
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
) -> str:
    return _local_heuristic_category(
        description,
        allowed_categories=allowed_categories or settings.allowed_categories,
        fallback_category=fallback_category or settings.fallback_category,
    )


def _batch_response_schema() -> dict[str, Any]:
    return {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "record_index": {"type": "INTEGER"},
                "category": {"type": "STRING"},
            },
            "required": ["record_index", "category"],
        },
    }


def _batch_system_instruction(
    allowed_categories: tuple[str, ...] | None = None,
) -> str:
    return (
        "You are a deterministic expense categorization assistant. "
        "Use the system categories exactly as provided. "
        "Do not invent extra categories. "
        "Return only valid JSON matching the required schema. "
        "Supported categories: "
        f"{', '.join(allowed_categories or settings.allowed_categories)}"
    )


def _call_gemini_batch(
    batch: list[dict[str, Any]],
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
    api_key: str | None = None,
) -> dict[int, str] | None:
    api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(
            timeout=GEMINI_TIMEOUT_SECONDS * 1000,
        ),
    )
    generation_config = genai_types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
        response_schema=_batch_response_schema(),
        system_instruction=_batch_system_instruction(allowed_categories),
    )

    prompt_payload = json.dumps(batch, ensure_ascii=False)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt_payload,
            config=generation_config,
        )
    finally:
        client.close()

    cleaned_text = str(getattr(response, "text", "") or "").strip()
    if not cleaned_text:
        return None

    try:
        parsed_payload = json.loads(cleaned_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed_payload, list):
        return None

    category_by_index: dict[int, str] = {}
    for item in parsed_payload:
        if not isinstance(item, dict):
            continue
        record_index = item.get("record_index")
        category = item.get("category")
        if isinstance(record_index, int) and isinstance(category, str):
            category_by_index[record_index] = normalize_category(
                category, allowed_categories, fallback_category
            )

    return category_by_index or None


def _classify_batch(
    records: list[Mapping[str, Any]],
    start_index: int,
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
    api_key: str | None = None,
) -> dict[int, str]:
    active_categories = allowed_categories or settings.allowed_categories
    active_fallback = fallback_category or settings.fallback_category
    batch_payload: list[dict[str, Any]] = [
        {
            "record_index": start_index + offset,
            "description": str(record.get("description", "") or "").strip(),
        }
        for offset, record in enumerate(records)
    ]

    fallback_map: dict[int, str] = {}
    for offset, record in enumerate(records):
        description = str(record.get("description", "") or "").strip()
        fallback_map[start_index + offset] = normalize_category(
            _heuristic_category(description, active_categories, active_fallback),
            active_categories,
            active_fallback,
        )

    if not batch_payload:
        return {}

    categorized_by_index = None
    for attempt in range(GEMINI_MAX_RETRIES + 1):
        try:
            categorized_by_index = _call_gemini_batch(
                batch_payload, active_categories, active_fallback, api_key
            )
            break
        except (
            ConnectionError,
            genai_errors.APIError,
            httpx.HTTPError,
            OSError,
            TimeoutError,
            RuntimeError,
        ):
            if attempt == GEMINI_MAX_RETRIES:
                break
            time.sleep(GEMINI_RETRY_DELAY_SECONDS * (2**attempt))
        except AttributeError, TypeError, ValueError:
            break

    if categorized_by_index:
        logger.info(
            "categorization.completed",
            extra={"operation": "gemini_batch", "record_count": len(batch_payload)},
        )
        return categorized_by_index

    logger.warning(
        "categorization.fallback_used",
        extra={"operation": "heuristic_batch", "record_count": len(batch_payload)},
    )
    return fallback_map


def classify_description(
    description: str,
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
) -> str:
    if not description or not str(description).strip():
        return fallback_category or settings.fallback_category

    return normalize_category(
        _heuristic_category(description, allowed_categories, fallback_category),
        allowed_categories,
        fallback_category,
    )


def _merge_categorized_batches(
    records: list[Mapping[str, Any]],
    batch_results: list[dict[int, str]],
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
) -> list[dict[str, Any]]:
    categorized_rows: list[dict[str, Any]] = []

    for start_index, chunk_start in enumerate(range(0, len(records), BATCH_SIZE)):
        chunk = records[chunk_start : chunk_start + BATCH_SIZE]
        category_by_index = batch_results[start_index]

        for offset, row in enumerate(chunk):
            record_index = chunk_start + offset
            normalized_row = dict(row)
            normalized_row["category"] = category_by_index.get(
                record_index,
                normalize_category(
                    _heuristic_category(
                        str(row.get("description", "") or "").strip(),
                        allowed_categories,
                        fallback_category,
                    ),
                    allowed_categories,
                    fallback_category,
                ),
            )
            categorized_rows.append(normalized_row)

    return categorized_rows


def _fallback_batch(
    records: list[Mapping[str, Any]],
    start_index: int,
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
) -> dict[int, str]:
    return {
        start_index + offset: normalize_category(
            _heuristic_category(
                str(record.get("description", "") or "").strip(),
                allowed_categories,
                fallback_category,
            ),
            allowed_categories,
            fallback_category,
        )
        for offset, record in enumerate(records)
    }


async def categorize_dataframe_async(
    rows: Iterable[Mapping[str, Any]],
    *,
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    active_categories = allowed_categories or settings.allowed_categories
    active_fallback = fallback_category or settings.fallback_category
    records = list(rows)
    batches = [
        (records[start_index : start_index + BATCH_SIZE], start_index)
        for start_index in range(0, len(records), BATCH_SIZE)
    ]

    async def classify_with_timeout(
        chunk: list[Mapping[str, Any]], start_index: int
    ) -> dict[int, str]:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _classify_batch,
                    chunk,
                    start_index,
                    active_categories,
                    active_fallback,
                    api_key,
                ),
                timeout=GEMINI_TIMEOUT_SECONDS * (GEMINI_MAX_RETRIES + 1),
            )
        except TimeoutError:
            return _fallback_batch(
                chunk, start_index, active_categories, active_fallback
            )

    batch_results = await asyncio.gather(
        *(classify_with_timeout(chunk, start_index) for chunk, start_index in batches)
    )
    return _merge_categorized_batches(
        records, list(batch_results), active_categories, active_fallback
    )


def categorize_dataframe(
    rows: Iterable[Mapping[str, Any]],
    *,
    allowed_categories: tuple[str, ...] | None = None,
    fallback_category: str | None = None,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    return asyncio.run(
        categorize_dataframe_async(
            rows,
            allowed_categories=allowed_categories,
            fallback_category=fallback_category,
            api_key=api_key,
        )
    )
