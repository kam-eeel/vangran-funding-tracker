from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.db import RecordQueryService
from app.web.deps import get_query_service, get_templates

router = APIRouter()


def _build_filters(
    department: str | None = None,
    program: str | None = None,
    postal_code: str | None = None,
    start_date_from: str | None = None,
    start_date_to: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    search: str | None = None,
) -> dict:
    """Build a filter dict from query params, omitting empty values."""
    filters: dict = {}
    if department:
        filters["department"] = department
    if program:
        filters["program"] = program
    if postal_code:
        filters["postal_code"] = postal_code
    if start_date_from:
        filters["start_date_from"] = start_date_from
    if start_date_to:
        filters["start_date_to"] = start_date_to
    if amount_min:
        filters["amount_min"] = amount_min
    if amount_max:
        filters["amount_max"] = amount_max
    if search:
        filters["search"] = search
    return filters


def _format_currency(value: float) -> str:
    """Format a number as currency."""
    if value < 0:
        return f"-${abs(value):,.0f}"
    return f"${value:,.0f}"


def _short_department(name: str) -> str:
    if "|" in name:
        return name.split("|")[0].strip()
    if " - " in name:
        return name.rsplit(" - ", 1)[0].strip()
    return name


@router.get("/explore", response_class=HTMLResponse)
def explore_page(
    request: Request,
    qs: RecordQueryService = Depends(get_query_service),
    templates: Jinja2Templates = Depends(get_templates),
    department: str | None = None,
    program: str | None = None,
    postal_code: str | None = None,
    start_date_from: str | None = None,
    start_date_to: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    search: str | None = None,
    sort: str = "amount",
    dir: str = "desc",
    page: int = 1,
):
    filters = _build_filters(
        department, program, postal_code,
        start_date_from, start_date_to,
        amount_min, amount_max, search,
    )
    filter_options = qs.get_filter_options()
    result = qs.search_records(filters=filters, sort=sort, direction=dir, page=page)

    ctx = {
        "request": request,
        "records": result["records"],
        "total": result["total"],
        "page": result["page"],
        "pages": result["pages"],
        "per_page": result["per_page"],
        "filter_options": filter_options,
        "filters": filters,
        "sort": sort,
        "dir": dir,
        "format_currency": _format_currency,
        "short_department": _short_department,
    }
    return templates.TemplateResponse("explore.html", ctx)


@router.get("/explore/partials/table", response_class=HTMLResponse)
def explore_table_partial(
    request: Request,
    qs: RecordQueryService = Depends(get_query_service),
    templates: Jinja2Templates = Depends(get_templates),
    department: str | None = None,
    program: str | None = None,
    postal_code: str | None = None,
    start_date_from: str | None = None,
    start_date_to: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    search: str | None = None,
    sort: str = "amount",
    dir: str = "desc",
    page: int = 1,
):
    filters = _build_filters(
        department, program, postal_code,
        start_date_from, start_date_to,
        amount_min, amount_max, search,
    )
    result = qs.search_records(filters=filters, sort=sort, direction=dir, page=page)

    ctx = {
        "request": request,
        "records": result["records"],
        "total": result["total"],
        "page": result["page"],
        "pages": result["pages"],
        "per_page": result["per_page"],
        "filters": filters,
        "sort": sort,
        "dir": dir,
        "format_currency": _format_currency,
        "short_department": _short_department,
    }
    return templates.TemplateResponse("partials/records_table.html", ctx)
