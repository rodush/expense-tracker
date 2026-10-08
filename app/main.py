from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from app.config import Settings, settings
from app.logging_config import configure_logging, request_id_context
from app.routers import datasets, uploads, websocket
from app.services import upload_service
from app.services.dataset_service import DatasetService
from app.services.dataset_store import DatasetStore, dataset_store
from app.services.errors import ServiceError
from app.services.gemini_service import (
    categorize_dataframe_async,
    determine_who_from_description,
)
from app.services.upload_cache import ProcessedUploadCache, processed_upload_cache
from app.services.upload_service import (
    Categorizer,
    UploadService,
    WhoResolver,
)

logger = logging.getLogger("expense_tracker")
MAX_UPLOAD_SIZE_BYTES = upload_service.MAX_UPLOAD_SIZE_BYTES
DOWNLOADS_DIR = Path.cwd() / ".tmp"
UI_TEMPLATE_FILE = Path(__file__).parent / "templates" / "index.html"


def create_app(
    app_settings: Settings = settings,
    data_store: DatasetStore = dataset_store,
    upload_cache: ProcessedUploadCache = processed_upload_cache,
    categorizer: Categorizer = categorize_dataframe_async,
    who_resolver: WhoResolver = determine_who_from_description,
    downloads_dir: Path = DOWNLOADS_DIR,
) -> FastAPI:
    """Build the API and its injectable application services."""
    configure_logging(app_settings.log_level, app_settings.log_format)
    application = FastAPI(title="Expense Categorizer", version="0.1.0")
    application.state.settings = app_settings
    application.state.upload_service = UploadService(
        dataset_store=data_store,
        upload_cache=upload_cache,
        categorize=categorizer,
        determine_who=who_resolver,
        downloads_dir=downloads_dir,
    )
    application.state.dataset_service = DatasetService(
        dataset_store=data_store,
        allowed_categories=app_settings.allowed_categories,
    )
    application.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
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

    @application.exception_handler(ServiceError)
    async def handle_service_error(
        _request: Request, exc: ServiceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @application.get("/health")
    def healthcheck() -> dict[str, Any]:
        """Return a liveness payload for process monitoring."""
        configured_settings: Settings = application.state.settings
        logger.info("Health check requested")
        return {
            "status": "ok",
            "service": "expense-categorizer",
            "gemini_api_key_configured": bool(configured_settings.gemini_api_key),
            "allowed_categories": list(configured_settings.allowed_categories),
        }

    @application.get("/ready")
    def readiness_check() -> dict[str, str]:
        """Confirm that the application loaded its required runtime configuration."""
        configured_settings: Settings = application.state.settings
        return {"status": "ready", "service": configured_settings.app_name}

    @application.get("/")
    @application.get("/ui")
    def get_ui() -> FileResponse:
        return FileResponse(UI_TEMPLATE_FILE)

    application.include_router(uploads.router)
    application.include_router(datasets.router)
    application.include_router(websocket.router)
    return application


app = create_app()
