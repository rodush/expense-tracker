from __future__ import annotations

from fastapi import Request

from app.services.dataset_service import DatasetService
from app.services.upload_service import UploadService


def get_upload_service(request: Request) -> UploadService:
    return request.app.state.upload_service


def get_dataset_service(request: Request) -> DatasetService:
    return request.app.state.dataset_service
