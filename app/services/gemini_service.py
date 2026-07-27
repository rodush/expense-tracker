from __future__ import annotations

import json
import os
from typing import Any, Iterable, Mapping, cast

try:
    import google.generativeai as genai  # type: ignore[reportMissingImports]
except ImportError:
    genai = None

try:
    from google.generativeai import types as genai_types  # type: ignore[reportMissingImports]
except ImportError:
    genai_types = None

from app.config import settings

GEMINI_MODEL = "gemini-2.5-flash"
BATCH_SIZE = 50


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
    )

    cleaned_text = str(getattr(response, "text", "") or "").strip()
    if not cleaned_text:
        return None

    try:
        parsed_payload: list[dict[str, Any]] = json.loads(cleaned_text)
    except json.JSONDecodeError:
        return None

    # if not isinstance(parsed_payload, list):
    #     return None

    category_by_index: dict[int, str] = {}
    for item in parsed_payload:
        # if not isinstance(item, dict):
        #     continue
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

    categorized_by_index = _call_gemini_batch(batch_payload)
    if categorized_by_index:
        return categorized_by_index

    return fallback_map


def classify_description(description: str) -> str:
    if not description or not str(description).strip():
        return "Other"

    return normalize_category(_heuristic_category(description))


def categorize_dataframe(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    records = list(rows)
    categorized_rows: list[dict[str, Any]] = []

    for start_index in range(0, len(records), BATCH_SIZE):
        chunk = records[start_index : start_index + BATCH_SIZE]
        category_by_index = _classify_batch(chunk, start_index)

        for offset, row in enumerate(chunk):
            record_index = start_index + offset
            normalized_row = dict(row)
            normalized_row["category"] = category_by_index.get(
                record_index,
                normalize_category(
                    _heuristic_category(str(row.get("description", "") or "").strip())
                ),
            )
            categorized_rows.append(normalized_row)

    return categorized_rows
