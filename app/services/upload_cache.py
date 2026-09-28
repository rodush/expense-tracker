from __future__ import annotations

import threading
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from app.services.dataset_store import DATASET_TTL_SECONDS


@dataclass(frozen=True)
class CachedUpload:
    rows: tuple[dict[str, Any], ...]
    columns: tuple[str, ...]
    category_column_added: bool


@dataclass
class _StoredUpload:
    upload: CachedUpload
    expires_at: float


class ProcessedUploadCache:
    def __init__(self, ttl_seconds: int = DATASET_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._uploads: dict[str, _StoredUpload] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> CachedUpload | None:
        with self._lock:
            self._purge_expired()
            stored = self._uploads.get(key)
            if stored is None:
                return None
            return CachedUpload(
                rows=tuple(row.copy() for row in stored.upload.rows),
                columns=stored.upload.columns,
                category_column_added=stored.upload.category_column_added,
            )

    def put(
        self,
        key: str,
        rows: Iterable[Mapping[str, Any]],
        columns: Iterable[str],
        category_column_added: bool,
    ) -> None:
        upload = CachedUpload(
            rows=tuple(dict(row) for row in rows),
            columns=tuple(columns),
            category_column_added=category_column_added,
        )
        with self._lock:
            self._purge_expired()
            self._uploads[key] = _StoredUpload(
                upload=upload,
                expires_at=time.monotonic() + self._ttl_seconds,
            )

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired_keys = [
            key for key, upload in self._uploads.items() if upload.expires_at <= now
        ]
        for key in expired_keys:
            del self._uploads[key]


processed_upload_cache = ProcessedUploadCache()
