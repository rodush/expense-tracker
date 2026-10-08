from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Awaitable, Callable
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.dataset_store import DatasetStore, normalize_rows, parse_amount
from app.services.errors import ServiceError
from app.services.upload_cache import ProcessedUploadCache

logger = logging.getLogger("expense_tracker")

ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
REQUIRED_COLUMNS = {"date", "amount", "description"}
COLUMN_ALIASES = {
    "transactiebedrag": "amount",
    "omschrijving": "description",
    "transactiedatum": "date",
}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024

Categorizer = Callable[[list[dict[str, Any]]], Awaitable[list[dict[str, Any]]]]
WhoResolver = Callable[[str], str]


def _is_safe_filename(filename: str | None) -> bool:
    if not filename:
        return False
    candidate = Path(filename).name
    return candidate == filename and candidate not in {"", ".", ".."}


def _is_savings_transfer(description: Any) -> bool:
    normalized_description = " ".join(str(description).casefold().split())
    return (
        "sepa overboeking" in normalized_description
        and "naam: savings account" in normalized_description
    )


def _normalize_column_name(column: Any) -> str:
    normalized_column = str(column).strip().lower()
    return COLUMN_ALIASES.get(normalized_column, normalized_column)


def _load_spreadsheet(raw_content: bytes, file_extension: str) -> pd.DataFrame:
    if file_extension == ".csv":
        return pd.read_csv(BytesIO(raw_content))

    excel_file = pd.ExcelFile(BytesIO(raw_content))
    return excel_file.parse(sheet_name=0)  # ty: ignore[invalid-return-type]


class UploadService:
    def __init__(
        self,
        dataset_store: DatasetStore,
        upload_cache: ProcessedUploadCache,
        categorize: Categorizer,
        determine_who: WhoResolver,
        downloads_dir: Path,
    ) -> None:
        self.dataset_store = dataset_store
        self.upload_cache = upload_cache
        self.categorize = categorize
        self.determine_who = determine_who
        self.downloads_dir = downloads_dir

    async def process_upload(
        self, filename: str | None, raw_content: bytes
    ) -> dict[str, Any]:
        if filename is None:
            raise ServiceError(400, "A file name is required.")
        if not _is_safe_filename(filename):
            raise ServiceError(400, "Invalid filename.")

        file_extension = Path(filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            logger.warning(
                "Rejected unsupported upload",
                extra={"file_name": filename, "extension": file_extension},
            )
            raise ServiceError(
                400,
                f"Unsupported file type: {file_extension or 'unknown'}."
                "Use CSV, XLS, or XLSX.",
            )
        if len(raw_content) > MAX_UPLOAD_SIZE_BYTES:
            raise ServiceError(413, "Uploaded file is too large.")

        cache_key = hashlib.sha256(
            file_extension.encode("ascii") + b"\0" + raw_content
        ).hexdigest()
        cached_upload = self.upload_cache.get(cache_key)
        if cached_upload is not None:
            dataframe = pd.DataFrame(
                cached_upload.rows, columns=list(cached_upload.columns)
            )
            category_column_added = cached_upload.category_column_added
            normalized_dataset_rows = normalize_rows(cached_upload.rows)
            logger.info("upload.cache_hit", extra={"operation": "upload_cache"})
        else:
            (
                dataframe,
                category_column_added,
                normalized_dataset_rows,
            ) = await self._process_new_upload(filename, raw_content, file_extension)

        download_id = str(uuid.uuid4())
        output_path = self.downloads_dir / f"categorized_{download_id}.csv"
        try:
            self.downloads_dir.mkdir(parents=True, exist_ok=True)
            dataframe.to_csv(output_path, index=False)
            dataset_id = self.dataset_store.create(normalized_dataset_rows)
            if cached_upload is None:
                self.upload_cache.put(
                    cache_key,
                    dataframe.to_dict(orient="records"),
                    dataframe.columns,
                    category_column_added,
                )
        except OSError as exc:
            logger.exception(
                "Failed to persist categorized upload",
                extra={"file_name": filename, "download_id": download_id},
            )
            raise ServiceError(
                503,
                "The categorized file could not be saved. Please retry the upload.",
            ) from exc
        except (RuntimeError, ValueError) as exc:
            logger.exception(
                "Failed to store categorized upload",
                extra={"file_name": filename, "download_id": download_id},
            )
            raise ServiceError(
                503,
                "The categorized data could not be stored. Please retry the upload.",
            ) from exc

        logger.info(
            "Upload processed successfully",
            extra={
                "file_name": filename,
                "rows": len(dataframe),
                "download_id": download_id,
                "dataset_id": dataset_id,
            },
        )
        preview = dataframe.sort_values(
            "amount", ascending=True, kind="stable"
        ).to_dict(orient="records")
        return {
            "row_count": len(dataframe),
            "category_column_added": category_column_added,
            "columns": list(dataframe.columns),
            "preview": preview,
            "download_id": download_id,
            "dataset_id": dataset_id,
        }

    async def _process_new_upload(
        self, filename: str, raw_content: bytes, file_extension: str
    ) -> tuple[pd.DataFrame, bool, list[dict[str, Any]]]:
        try:
            dataframe = _load_spreadsheet(raw_content, file_extension)
        except Exception as exc:
            logger.exception(
                "Failed to parse uploaded spreadsheet",
                extra={"file_name": filename},
            )
            raise ServiceError(400, "Unable to parse file content.") from exc

        dataframe = dataframe.rename(columns=_normalize_column_name)
        missing_columns = sorted(REQUIRED_COLUMNS.difference(dataframe.columns))
        if missing_columns:
            logger.warning(
                "Upload missing required columns",
                extra={"file_name": filename, "missing_columns": missing_columns},
            )
            raise ServiceError(
                400, f"Missing required columns: {', '.join(missing_columns)}"
            )

        try:
            parsed_amounts = dataframe["amount"].map(parse_amount)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Upload contains an invalid amount", extra={"file_name": filename}
            )
            raise ServiceError(400, str(exc)) from exc

        credit_rows = dataframe["amount"].map(
            lambda amount: Decimal(str(amount).strip()) > Decimal("0.00")
        )
        savings_transfer_rows = dataframe["description"].map(_is_savings_transfer)
        expense_rows = ~(credit_rows | savings_transfer_rows)
        dataframe = dataframe.loc[expense_rows].copy()
        dataframe["amount"] = parsed_amounts.loc[expense_rows].abs().astype(float)
        dataframe["who"] = (
            dataframe["description"].fillna("").astype(str).apply(self.determine_who)
        )

        category_column_added = "category" not in dataframe.columns
        if category_column_added:
            dataframe["category"] = "Other"

        normalized_rows = [
            {str(key): value for key, value in row.items()}
            for row in dataframe.to_dict(orient="records")
        ]
        categorized_rows = await self.categorize(normalized_rows)
        dataframe = dataframe.assign(
            category=[row["category"] for row in categorized_rows]
        )
        try:
            normalized_dataset_rows = normalize_rows(
                dataframe.to_dict(orient="records")
            )
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Upload contains an invalid amount", extra={"file_name": filename}
            )
            raise ServiceError(400, str(exc)) from exc
        return dataframe, category_column_added, normalized_dataset_rows

    def download_path(self, download_id: str) -> Path:
        output_path = self.downloads_dir / f"categorized_{download_id}.csv"
        if not output_path.exists():
            logger.warning(
                "download.not_found",
                extra={"operation": "download", "download_id": download_id},
            )
            raise ServiceError(404, "Categorized file not found.")
        return output_path
