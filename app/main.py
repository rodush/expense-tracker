from __future__ import annotations

import logging
import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.services.gemini_service import (
    categorize_dataframe,
    determine_who_from_description,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("expense_tracker")

app = FastAPI(title="Expense Categorizer", version="0.1.0")
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)

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
    return excel_file.parse(sheet_name=0)


@app.get("/health")
def healthcheck() -> dict[str, Any]:
    """Return a small readiness payload for local verification."""
    logger.info("Health check requested")
    return {
        "status": "ok",
        "service": "expense-categorizer",
        "gemini_api_key_configured": bool(os.getenv("GEMINI_API_KEY")),
        "allowed_categories": list(settings.allowed_categories),
    }


@app.get("/")
def root() -> FileResponse:
    return FileResponse(UI_TEMPLATE_FILE)


@app.get("/ui")
def get_ui() -> FileResponse:
    return FileResponse(UI_TEMPLATE_FILE)


@app.post("/upload")
async def upload_expense_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accept an expense spreadsheet, normalize its columns, and return metadata."""
    logger.info("Upload requested", extra={"file_name": file.filename})
    if file.filename is None:
        raise HTTPException(status_code=400, detail="A file name is required.")

    if not _is_safe_filename(file.filename):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        logger.warning("Rejected unsupported upload", extra={"file_name": file.filename, "extension": file_extension})
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension or 'unknown'}. Use CSV, XLS, or XLSX.",
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
        logger.exception("Failed to parse uploaded spreadsheet", extra={"file_name": file.filename})
        raise HTTPException(
            status_code=400, detail=f"Unable to parse file content: {exc}"
        ) from exc

    dataframe = dataframe.rename(columns=lambda column: str(column).strip().lower())

    missing_columns = sorted(REQUIRED_COLUMNS.difference(dataframe.columns))
    if missing_columns:
        logger.warning("Upload missing required columns", extra={"file_name": file.filename, "missing_columns": missing_columns})
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
    categorized_rows = categorize_dataframe(normalized_rows)
    dataframe = dataframe.assign(category=[row["category"] for row in categorized_rows])

    download_id = str(uuid.uuid4())
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Upload processed successfully", extra={"file_name": file.filename, "rows": len(dataframe), "download_id": download_id})
    output_path = DOWNLOADS_DIR / f"categorized_{download_id}.csv"
    dataframe.to_csv(output_path, index=False)

    return {
        "row_count": len(dataframe),
        "category_column_added": category_column_added,
        "columns": list(dataframe.columns),
        "preview": dataframe.to_dict(orient="records"),
        "download_id": download_id,
    }


@app.get("/download/{download_id}")
def download_categorized_file(download_id: str) -> FileResponse:
    output_path = DOWNLOADS_DIR / f"categorized_{download_id}.csv"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Categorized file not found.")
    return FileResponse(output_path, filename=f"categorized_{download_id}.csv")
