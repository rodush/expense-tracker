from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.dependencies import get_upload_service
from app.services.upload_service import UploadService

router = APIRouter()
logger = logging.getLogger("expense_tracker")


@router.post("/upload")
async def upload_expense_file(
    file: Annotated[UploadFile, File(...)],
    service: Annotated[UploadService, Depends(get_upload_service)],
) -> dict[str, Any]:
    logger.info("Upload requested", extra={"file_name": file.filename})
    return await service.process_upload(file.filename, await file.read())


@router.get("/download/{download_id}")
def download_categorized_file(
    download_id: str,
    service: Annotated[UploadService, Depends(get_upload_service)],
) -> FileResponse:
    logger.info(
        "download.started",
        extra={"operation": "download", "download_id": download_id},
    )
    return FileResponse(
        service.download_path(download_id),
        filename=f"categorized_{download_id}.csv",
    )
