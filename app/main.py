from __future__ import annotations

import csv
import logging
import time
import uuid
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from app.config import settings
from app.logging_config import configure_logging, request_id_context
from app.services.dataset_store import (
    DatasetNotFoundError,
    dataset_store,
    normalize_rows,
    parse_amount,
)
from app.services.gemini_service import (
    categorize_dataframe_async,
    determine_who_from_description,
)

from .routers import websocket

configure_logging(settings.log_level, settings.log_format)
logger = logging.getLogger("expense_tracker")

app = FastAPI(title="Expense Categorizer", version="0.1.0")
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next: Any) -> Any:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_context.set(request_id)
    started_at = time.perf_counter()
    logger.info(
        "request.started",
        extra={"method": request.method, "path": request.url.path},
    )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request.failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
            },
        )
        raise
    else:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "request.completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_context.reset(token)


app.include_router(websocket.router)

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
REQUIRED_COLUMNS = {"date", "amount", "description"}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
UI_TEMPLATE_FILE = Path(__file__).parent / "templates" / "index.html"
DOWNLOADS_DIR = Path.cwd() / ".tmp"


def _is_safe_filename(filename: str | None) -> bool:
    if not filename:
        return False
    candidate = Path(filename).name
    return candidate == filename and candidate not in {"", ".", ".."}


def _load_spreadsheet(raw_content: bytes, file_extension: str) -> pd.DataFrame:
    if file_extension == ".csv":
        return pd.read_csv(BytesIO(raw_content))

    excel_file = pd.ExcelFile(BytesIO(raw_content))
    return excel_file.parse(sheet_name=0)  # ty: ignore[invalid-return-type]


@app.get("/health")
def healthcheck() -> dict[str, Any]:
    """Return a liveness payload for process monitoring."""
    logger.info("Health check requested")
    return {
        "status": "ok",
        "service": "expense-categorizer",
        "gemini_api_key_configured": bool(settings.gemini_api_key),
        "allowed_categories": list(settings.allowed_categories),
    }


@app.get("/ready")
def readiness_check() -> dict[str, str]:
    """Confirm that the application loaded its required runtime configuration."""
    return {"status": "ready", "service": settings.app_name}


@app.get("/")
def root() -> FileResponse:
    return FileResponse(UI_TEMPLATE_FILE)


@app.get("/ui")
def get_ui() -> FileResponse:
    return FileResponse(UI_TEMPLATE_FILE)


@app.post("/upload")
async def upload_expense_file(
    file: Annotated[UploadFile, File(...)],
) -> dict[str, Any]:
    """Accept an expense spreadsheet, normalize its columns, and return metadata."""
    logger.info("Upload requested", extra={"file_name": file.filename})
    if file.filename is None:
        raise HTTPException(status_code=400, detail="A file name is required.")

    if not _is_safe_filename(file.filename):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        logger.warning(
            "Rejected unsupported upload",
            extra={"file_name": file.filename, "extension": file_extension},
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension or 'unknown'}."
            "Use CSV, XLS, or XLSX.",
        )

    raw_content = await file.read()
    if len(raw_content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Uploaded file is too large.",
        )

    try:
        dataframe = _load_spreadsheet(raw_content, file_extension)
    except Exception as exc:
        logger.exception(
            "Failed to parse uploaded spreadsheet", extra={"file_name": file.filename}
        )
        raise HTTPException(
            status_code=400, detail="Unable to parse file content."
        ) from exc

    dataframe = dataframe.rename(columns=lambda column: str(column).strip().lower())

    missing_columns = sorted(REQUIRED_COLUMNS.difference(dataframe.columns))
    if missing_columns:
        logger.warning(
            "Upload missing required columns",
            extra={"file_name": file.filename, "missing_columns": missing_columns},
        )
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing_columns)}",
        )

    dataframe["who"] = (
        dataframe["description"]
        .fillna("")
        .astype(str)
        .apply(determine_who_from_description)
    )

    category_column_added = "category" not in dataframe.columns
    if category_column_added:
        dataframe["category"] = "Other"

    normalized_rows: list[dict[str, Any]] = [
        {str(key): value for key, value in row.items()}
        for row in dataframe.to_dict(orient="records")
    ]
    categorized_rows = await categorize_dataframe_async(normalized_rows)
    dataframe = dataframe.assign(category=[row["category"] for row in categorized_rows])
    try:
        normalized_dataset_rows = normalize_rows(dataframe.to_dict(orient="records"))
    except ValueError as exc:
        logger.warning(
            "Upload contains an invalid amount", extra={"file_name": file.filename}
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    download_id = str(uuid.uuid4())
    output_path = DOWNLOADS_DIR / f"categorized_{download_id}.csv"
    try:
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(output_path, index=False)
        dataset_id = dataset_store.create(normalized_dataset_rows)
    except OSError as exc:
        logger.exception(
            "Failed to persist categorized upload",
            extra={"file_name": file.filename, "download_id": download_id},
        )
        raise HTTPException(
            status_code=503,
            detail="The categorized file could not be saved. Please retry the upload.",
        ) from exc
    except (RuntimeError, ValueError) as exc:
        logger.exception(
            "Failed to store categorized upload",
            extra={"file_name": file.filename, "download_id": download_id},
        )
        raise HTTPException(
            status_code=503,
            detail="The categorized data could not be stored. Please retry the upload.",
        ) from exc

    logger.info(
        "Upload processed successfully",
        extra={
            "file_name": file.filename,
            "rows": len(dataframe),
            "download_id": download_id,
            "dataset_id": dataset_id,
        },
    )

    return {
        "row_count": len(dataframe),
        "category_column_added": category_column_added,
        "columns": list(dataframe.columns),
        "preview": dataframe.to_dict(orient="records"),
        "download_id": download_id,
        "dataset_id": dataset_id,
    }


@app.get("/datasets/{dataset_id}/summary")
def dataset_summary(
    dataset_id: str,
    category: Annotated[list[str] | None, Query()] = None,
    who: Annotated[list[str] | None, Query()] = None,
) -> dict[str, Any]:
    """Return signed net totals for a reusable, short-lived dataset."""
    selected_categories = category or []
    selected_who = who or []
    filtered_rows = _get_filtered_dataset_rows(
        dataset_id, selected_categories, selected_who
    )
    rows = dataset_store.get(dataset_id)

    try:
        amounts = [parse_amount(row.get("amount")) for row in filtered_rows]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def aggregate(
        field: str, include_zero_values: bool = False
    ) -> list[dict[str, Any]]:
        names = (
            list(settings.allowed_categories)
            if field == "category"
            else sorted(
                {str(row.get(field, "")) for row in rows if row.get(field) is not None}
            )
        )
        if not include_zero_values:
            names = [
                name
                for name in names
                if any(row.get(field) == name for row in filtered_rows)
            ]
        result = []
        for name in names:
            matching_amounts = [
                amount
                for row, amount in zip(filtered_rows, amounts)
                if row.get(field) == name
            ]
            result.append(
                {
                    "name": name,
                    "amount": float(sum(matching_amounts, Decimal("0.00"))),
                    "count": len(matching_amounts),
                }
            )
        return result

    total_amount_decimal = sum(amounts, Decimal("0.00"))
    total_amount = float(total_amount_decimal)
    categories = aggregate("category", include_zero_values=True)
    for item in categories:
        item["percentage"] = (
            round(item["amount"] / total_amount * 100, 2) if total_amount else 0.0
        )

    logger.info(
        "summary.completed",
        extra={
            "operation": "summary",
            "dataset_id": dataset_id,
            "record_count": len(filtered_rows),
        },
    )
    return {
        "dataset_id": dataset_id,
        "total_amount": total_amount,
        "expense_count": len(filtered_rows),
        "categories": categories,
        "who": aggregate("who"),
        "applied_filters": {"category": selected_categories, "who": selected_who},
    }


def _get_filtered_dataset_rows(
    dataset_id: str,
    categories: list[str] | None,
    people: list[str] | None,
) -> list[dict[str, Any]]:
    try:
        rows = dataset_store.get(dataset_id)
    except DatasetNotFoundError as exc:
        logger.warning(
            "dataset.not_found",
            extra={"operation": "export", "dataset_id": dataset_id},
        )
        raise HTTPException(status_code=404, detail="Dataset not found.") from exc

    selected_categories = categories or []
    selected_who = people or []
    unknown_categories = sorted(
        set(selected_categories).difference(settings.allowed_categories)
    )
    if unknown_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category filter: {', '.join(unknown_categories)}",
        )

    available_who = {str(row.get("who", "")) for row in rows}
    unknown_who = sorted(set(selected_who).difference(available_who))
    if unknown_who:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid who filter: {', '.join(unknown_who)}",
        )

    return [
        row
        for row in rows
        if (not selected_categories or row.get("category") in selected_categories)
        and (not selected_who or row.get("who") in selected_who)
    ]


@app.get("/datasets/{dataset_id}/export")
def export_dataset(
    dataset_id: str,
    category: Annotated[list[str] | None, Query()] = None,
    who: Annotated[list[str] | None, Query()] = None,
) -> StreamingResponse:
    """Export the normalized dataset, optionally filtered by category and person."""
    rows = _get_filtered_dataset_rows(dataset_id, category, who)
    output = StringIO(newline="")
    fieldnames = (
        list(rows[0]) if rows else ["date", "amount", "description", "who", "category"]
    )
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    filtered = bool(category or who)
    suffix = "filtered" if filtered else "full"
    logger.info(
        "dataset.exported",
        extra={
            "operation": "export",
            "dataset_id": dataset_id,
            "record_count": len(rows),
            "filtered": filtered,
        },
    )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="dataset_{dataset_id}-{suffix}.csv"'
            )
        },
    )


@app.get("/download/{download_id}")
def download_categorized_file(download_id: str) -> FileResponse:
    output_path = DOWNLOADS_DIR / f"categorized_{download_id}.csv"
    if not output_path.exists():
        logger.warning(
            "download.not_found",
            extra={"operation": "download", "download_id": download_id},
        )
        raise HTTPException(status_code=404, detail="Categorized file not found.")
    logger.info(
        "download.started",
        extra={"operation": "download", "download_id": download_id},
    )
    return FileResponse(output_path, filename=f"categorized_{download_id}.csv")
