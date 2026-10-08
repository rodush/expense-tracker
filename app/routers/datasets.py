from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.dependencies import get_dataset_service
from app.services.dataset_service import DatasetService

router = APIRouter()


@router.get("/datasets/{dataset_id}/summary")
def dataset_summary(
    dataset_id: str,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    category: Annotated[list[str] | None, Query()] = None,
    who: Annotated[list[str] | None, Query()] = None,
) -> dict[str, Any]:
    return service.summarize(dataset_id, category, who)


@router.get("/datasets/{dataset_id}/export")
def export_dataset(
    dataset_id: str,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    category: Annotated[list[str] | None, Query()] = None,
    who: Annotated[list[str] | None, Query()] = None,
) -> StreamingResponse:
    content, filtered = service.export_csv(dataset_id, category, who)
    suffix = "filtered" if filtered else "full"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="dataset_{dataset_id}-{suffix}.csv"'
            )
        },
    )
