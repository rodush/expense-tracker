from __future__ import annotations

import hashlib
import logging
from collections.abc import Awaitable, Callable
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from app.services.dataset_store import (
    DatasetNotFoundError,
    LedgerStoreBackend,
    normalize_rows,
    parse_amount,
)
from app.services.errors import ServiceError
from app.services.transaction_identity import normalize_transaction_date, record_keys

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
        dataset_store: LedgerStoreBackend,
        categorize: Categorizer,
        determine_who: WhoResolver,
        downloads_dir: Path,
    ) -> None:
        self.dataset_store = dataset_store
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

        (
            dataframe,
            category_column_added,
            normalized_rows,
        ) = await self._process_new_upload(filename, raw_content, file_extension)
        source_hash = hashlib.sha256(raw_content).hexdigest()
        try:
            existing_import = self.dataset_store.find_import(source_hash)
        except SQLAlchemyError as exc:
            raise ServiceError(
                503, "The expense ledger is temporarily unavailable."
            ) from exc
        if existing_import is not None:
            rows = existing_import["rows"]
            return {
                "row_count": existing_import["row_count"],
                "new_transaction_count": 0,
                "duplicate_count": existing_import["row_count"],
                "category_column_added": existing_import["category_column_added"],
                "columns": existing_import["columns"],
                "preview": rows,
                "download_id": existing_import["dataset_id"],
                "dataset_id": existing_import["dataset_id"],
            }

        keys = record_keys(normalized_rows)
        try:
            known_keys = self.dataset_store.existing_record_keys(keys)
        except SQLAlchemyError as exc:
            raise ServiceError(
                503, "The expense ledger is temporarily unavailable."
            ) from exc
        new_rows = [
            (key, row)
            for key, row in zip(keys, normalized_rows, strict=True)
            if key not in known_keys
        ]
        new_rows = [
            (
                key,
                {
                    **row,
                    "who": self.determine_who(str(row.get("description", "") or "")),
                },
            )
            for key, row in new_rows
        ]
        categorized_rows = (
            await self.categorize([row for _, row in new_rows]) if new_rows else []
        )
        if len(categorized_rows) != len(new_rows):
            raise ServiceError(
                502, "Expense categorization returned an invalid result."
            )
        rows_to_import = [
            (key, {**row, **categorized})
            for (key, row), categorized in zip(new_rows, categorized_rows, strict=True)
        ]

        download_id = ""
        output_path = self.downloads_dir / "categorized.csv"
        try:
            dataset_id, inserted_rows, duplicate_count = self.dataset_store.import_rows(
                source_hash=source_hash,
                row_count=len(normalized_rows),
                rows=rows_to_import,
                columns=list(dataframe.columns),
                category_column_added=category_column_added,
            )
            download_id = dataset_id
            output_path = self.downloads_dir / f"categorized_{download_id}.csv"
            if not getattr(self.dataset_store, "supports_download_regeneration", False):
                self.downloads_dir.mkdir(parents=True, exist_ok=True)
                pd.DataFrame(inserted_rows, columns=list(dataframe.columns)).to_csv(
                    output_path, index=False
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
        except (RuntimeError, ValueError, SQLAlchemyError) as exc:
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
                "rows": len(normalized_rows),
                "new_transaction_count": len(inserted_rows),
                "duplicate_count": duplicate_count,
                "download_id": download_id,
                "dataset_id": dataset_id,
            },
        )
        preview = sorted(inserted_rows, key=lambda row: float(row.get("amount", 0)))
        return {
            "row_count": len(normalized_rows),
            "new_transaction_count": len(inserted_rows),
            "duplicate_count": duplicate_count,
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
            dataframe["date"] = dataframe["date"].map(normalize_transaction_date)
            parsed_amounts = dataframe["amount"].map(parse_amount)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Upload contains an invalid transaction field",
                extra={"file_name": filename},
            )
            raise ServiceError(400, str(exc)) from exc

        credit_rows = dataframe["amount"].map(
            lambda amount: Decimal(str(amount).strip()) > Decimal("0.00")
        )
        savings_transfer_rows = dataframe["description"].map(_is_savings_transfer)
        expense_rows = ~(credit_rows | savings_transfer_rows)
        dataframe = dataframe.loc[expense_rows].copy()
        dataframe["amount"] = parsed_amounts.loc[expense_rows].abs().astype(float)
        dataframe["who"] = ""
        category_column_added = "category" not in dataframe.columns
        if category_column_added:
            dataframe["category"] = "Other"

        normalized_rows = [
            {str(key): value for key, value in row.items()}
            for row in dataframe.to_dict(orient="records")
        ]
        try:
            normalized_dataset_rows = normalize_rows(normalized_rows)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Upload contains an invalid amount", extra={"file_name": filename}
            )
            raise ServiceError(400, str(exc)) from exc
        return dataframe, category_column_added, normalized_dataset_rows

    def download_path(self, download_id: str) -> Path:
        output_path = self.downloads_dir / f"categorized_{download_id}.csv"
        rows = None
        can_regenerate = getattr(
            self.dataset_store, "supports_download_regeneration", False
        )
        if can_regenerate:
            try:
                rows = self.dataset_store.get(download_id)
            except DatasetNotFoundError as exc:
                logger.warning(
                    "download.not_found",
                    extra={"operation": "download", "download_id": download_id},
                )
                raise ServiceError(404, "Categorized file not found.") from exc
        if not output_path.exists():
            if not can_regenerate:
                logger.warning(
                    "download.not_found",
                    extra={"operation": "download", "download_id": download_id},
                )
                raise ServiceError(404, "Categorized file not found.")
            try:
                self.downloads_dir.mkdir(parents=True, exist_ok=True)
                pd.DataFrame(rows or []).to_csv(output_path, index=False)
            except OSError as exc:
                raise ServiceError(
                    503, "The categorized file could not be regenerated."
                ) from exc
        return output_path
