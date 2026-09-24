from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)

_SAFE_CONTEXT_FIELDS = {
    "method",
    "path",
    "status_code",
    "duration_ms",
    "file_name",
    "extension",
    "rows",
    "dataset_id",
    "download_id",
    "missing_columns",
    "operation",
    "record_count",
}


class StructuredFormatter(logging.Formatter):
    """Render stable JSON logs without serializing arbitrary record fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
        }
        for field_name in _SAFE_CONTEXT_FIELDS:
            if hasattr(record, field_name):
                payload[field_name] = getattr(record, field_name)
        if record.exc_info:
            exception_type = record.exc_info[0]
            if exception_type is not None:
                payload["exception_type"] = exception_type.__name__
        return json.dumps(payload, default=str, ensure_ascii=True)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_context.get()
        return True


def configure_logging(level: str = "INFO", output_format: str = "json") -> None:
    """Configure application logs for local and deployed environments."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if any(
        isinstance(handler.formatter, StructuredFormatter)
        for handler in root_logger.handlers
    ):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestContextFilter())
    if output_format == "json":
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    root_logger.addHandler(handler)
