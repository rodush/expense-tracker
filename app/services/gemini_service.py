from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import Iterable, Mapping
from typing import Any, cast

from google.api_core.exceptions import GoogleAPICallError

try:
    import google.generativeai as genai  # type: ignore[reportMissingImports]
except ImportError:
    genai = None

try:
    from google.generativeai import (
        types as genai_types,  # type: ignore[reportMissingImports]
    )
except ImportError:
    genai_types = None

from app.config import settings

logger = logging.getLogger("expense_tracker.categorization")
GEMINI_MODEL = "gemini-2.5-flash"
BATCH_SIZE = 50
GEMINI_TIMEOUT_SECONDS = 15
GEMINI_MAX_RETRIES = 2
GEMINI_RETRY_DELAY_SECONDS = 0.1


def normalize_category(raw_category: str) -> str:
    candidate = str(raw_category or "").strip()
    if candidate in settings.allowed_categories:
        return candidate
    return "Other"


def determine_who_from_description(description: str) -> str:
    description_text = str(description or "").strip()
    description_lower = description_text.lower()

    if "pas543" in description_lower:
        return "Roman"
    if "kaartnummer: **5006" in description_lower:
        return "Oksana"
    return "General"


def _heuristic_category(description: str) -> str:
    description_lower = description.lower()

    category_keywords = {
        "Food": [
            "coffee",
            "restaurant",
            "cafe",
            "food",
            "lunch",
            "dinner",
            "grocer",
            "grocery",
            "bakery",
        ],
        "Transport": [
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
        ],
        "Utilities": [
            "electricity",
            "water",
            "gas",
            "internet",
            "phone",
            "utility",
            "mobile",
            "bill",
        ],
        "Shopping": [
            "amazon",
            "shop",
            "store",
            "market",
            "retail",
            "purchase",
            "clothes",
            "electronics",
        ],
    }

    for category, keywords in category_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            return category

    return "Other"


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


def _batch_system_instruction() -> str:
    return (
        "You are a deterministic expense categorization assistant. "
        "Use the system categories exactly as provided. "
        "Do not invent extra categories. "
        "Return only valid JSON matching the required schema. "
        f"Supported categories: {', '.join(settings.allowed_categories)}"
    )


def _call_gemini_batch(batch: list[dict[str, Any]]) -> dict[int, str] | None:
    if genai is None or genai_types is None:
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    gemini_module = cast(Any, genai)
    gemini_module.configure(api_key=api_key)
    model = gemini_module.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=_batch_system_instruction(),
    )

    generation_config = genai_types.GenerationConfig(
        temperature=0.0,
        response_mime_type="application/json",
        response_schema=_batch_response_schema(),
    )

    prompt_payload = json.dumps(batch, ensure_ascii=False)
    response = model.generate_content(
        prompt_payload,
        generation_config=generation_config,
        request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
    )

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
            category_by_index[record_index] = normalize_category(category)

    return category_by_index or None


def _classify_batch(
    records: list[Mapping[str, Any]], start_index: int
) -> dict[int, str]:
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
            _heuristic_category(description)
        )

    if not batch_payload:
        return {}

    categorized_by_index = None
    for attempt in range(GEMINI_MAX_RETRIES + 1):
        try:
            categorized_by_index = _call_gemini_batch(batch_payload)
            break
        except (
            ConnectionError,
            GoogleAPICallError,
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


def classify_description(description: str) -> str:
    if not description or not str(description).strip():
        return "Other"

    return normalize_category(_heuristic_category(description))


def _merge_categorized_batches(
    records: list[Mapping[str, Any]],
    batch_results: list[dict[int, str]],
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
                    _heuristic_category(str(row.get("description", "") or "").strip())
                ),
            )
            categorized_rows.append(normalized_row)

    return categorized_rows


def _fallback_batch(
    records: list[Mapping[str, Any]], start_index: int
) -> dict[int, str]:
    return {
        start_index + offset: normalize_category(
            _heuristic_category(str(record.get("description", "") or "").strip())
        )
        for offset, record in enumerate(records)
    }


async def categorize_dataframe_async(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
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
                asyncio.to_thread(_classify_batch, chunk, start_index),
                timeout=GEMINI_TIMEOUT_SECONDS * (GEMINI_MAX_RETRIES + 1),
            )
        except TimeoutError:
            return _fallback_batch(chunk, start_index)

    batch_results = await asyncio.gather(
        *(classify_with_timeout(chunk, start_index) for chunk, start_index in batches)
    )
    return _merge_categorized_batches(records, list(batch_results))


def categorize_dataframe(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return asyncio.run(categorize_dataframe_async(rows))
