from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.dependencies import get_dataset_service, get_expense_history_service
from app.services.dataset_service import DatasetService
from app.services.expense_history_service import ExpenseHistoryService

router = APIRouter()


@router.get("/expenses")
def list_expenses(
    service: Annotated[ExpenseHistoryService, Depends(get_expense_history_service)],
    category: Annotated[list[str] | None, Query()] = None,
    who: Annotated[list[str] | None, Query()] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    year: int | None = None,
    month: int | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    return service.list_expenses(
        category, who, date_from, date_to, year, month, offset, limit
    )


@router.get("/expenses/summary")
def expenses_summary(
    service: Annotated[ExpenseHistoryService, Depends(get_expense_history_service)],
    category: Annotated[list[str] | None, Query()] = None,
    who: Annotated[list[str] | None, Query()] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    return service.summary(category, who, date_from, date_to, year, month)


@router.get("/expenses/filter-options")
def expense_filter_options(
    service: Annotated[ExpenseHistoryService, Depends(get_expense_history_service)],
) -> dict[str, Any]:
    return service.filter_options()


@router.get("/expenses/export")
def export_expenses(
    service: Annotated[ExpenseHistoryService, Depends(get_expense_history_service)],
    category: Annotated[list[str] | None, Query()] = None,
    who: Annotated[list[str] | None, Query()] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> StreamingResponse:
    content, filtered = service.export_csv(
        categories=category,
        people=who,
        date_from=date_from,
        date_to=date_to,
        year=year,
        month=month,
    )
    suffix = "filtered" if filtered else "all"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="expenses-{suffix}.csv"'
        },
    )


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
