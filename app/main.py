from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI(title="Expense Categorizer", version="0.1.0")

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
REQUIRED_COLUMNS = {"date", "amount", "description", "purchaser"}


@app.get("/health")
def healthcheck() -> dict[str, Any]:
    """Return a small readiness payload for local verification."""
    return {
        "status": "ok",
        "service": "expense-categorizer",
        "gemini_api_key_configured": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Expense categorizer backend is running."}


@app.post("/upload")
async def upload_expense_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accept an expense spreadsheet, normalize its columns, and return metadata."""
    if file.filename is None:
        raise HTTPException(status_code=400, detail="A file name is required.")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension or 'unknown'}. Use CSV, XLS, or XLSX.",
        )

    raw_content = await file.read()

    try:
        if file_extension == ".csv":
            dataframe = pd.read_csv(BytesIO(raw_content))
        else:
            dataframe = pd.read_excel(BytesIO(raw_content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse file content: {exc}") from exc

    dataframe = dataframe.rename(columns=lambda column: str(column).strip().lower())

    missing_columns = sorted(REQUIRED_COLUMNS.difference(dataframe.columns))
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing_columns)}",
        )

    category_column_added = "category" not in dataframe.columns
    if category_column_added:
        dataframe["category"] = "Other"

    return {
        "row_count": int(len(dataframe)),
        "category_column_added": category_column_added,
        "columns": list(dataframe.columns),
    }
