from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request as StarletteRequest

from app.db import RecordQueryService
from app.web.deps import get_query_service, get_templates
from app.web.limiter import limiter

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
    """Format a number as full currency string."""
    if value < 0:
        return f"-${abs(value):,.0f}"
    return f"${value:,.0f}"


@router.get("/", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    qs: RecordQueryService = Depends(get_query_service),
    templates: Jinja2Templates = Depends(get_templates),
):
    kpis = qs.get_kpis()
    kpis["total_funding_fmt"] = _format_currency(kpis["total_funding"])
    kpis["avg_amount_fmt"] = _format_currency(kpis["avg_amount"])
    kpis["funding_delivered_fmt"] = _format_currency(kpis["funding_delivered"])
    kpis["funding_committed_fmt"] = _format_currency(kpis["funding_committed"])
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "kpis": kpis}
    )


@limiter.limit("30/minute")
@router.get("/api/charts/department")
def chart_department(
    request: Request,
    qs: RecordQueryService = Depends(get_query_service),
    department: str | None = None,
    program: str | None = None,
    postal_code: str | None = None,
    start_date_from: str | None = None,
    start_date_to: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    search: str | None = None,
    limit: int = Query(default=10, ge=1, le=100),
):
    filters = _build_filters(department, program, postal_code, start_date_from, start_date_to, amount_min, amount_max, search)
    data = qs.get_funding_by_department(limit=limit, filters=filters)
    return {
        "labels": [d["short_name"] for d in data],
        "data": [d["total"] for d in data],
        "counts": [d["count"] for d in data],
        "full_names": [d["name"] for d in data],
    }


@limiter.limit("30/minute")
@router.get("/api/charts/program")
def chart_program(
    request: Request,
    qs: RecordQueryService = Depends(get_query_service),
    department: str | None = None,
    program: str | None = None,
    postal_code: str | None = None,
    start_date_from: str | None = None,
    start_date_to: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    search: str | None = None,
    limit: int = Query(default=10, ge=1, le=100),
):
    filters = _build_filters(department, program, postal_code, start_date_from, start_date_to, amount_min, amount_max, search)
    data = qs.get_funding_by_program(limit=limit, filters=filters)
    return {
        "labels": [d["name"] for d in data],
        "data": [d["total"] for d in data],
        "counts": [d["count"] for d in data],
    }


@limiter.limit("30/minute")
@router.get("/api/charts/postal")
def chart_postal(
    request: Request,
    qs: RecordQueryService = Depends(get_query_service),
    department: str | None = None,
    program: str | None = None,
    postal_code: str | None = None,
    start_date_from: str | None = None,
    start_date_to: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    search: str | None = None,
):
    filters = _build_filters(department, program, postal_code, start_date_from, start_date_to, amount_min, amount_max, search)
    data = qs.get_funding_by_postal_code(filters=filters)
    return {
        "labels": [d["fsa"] for d in data],
        "data": [d["total"] for d in data],
        "counts": [d["count"] for d in data],
    }


@limiter.limit("30/minute")
@router.get("/api/charts/timeline")
def chart_timeline(
    request: Request,
    qs: RecordQueryService = Depends(get_query_service),
    department: str | None = None,
    program: str | None = None,
    postal_code: str | None = None,
    start_date_from: str | None = None,
    start_date_to: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    search: str | None = None,
):
    filters = _build_filters(department, program, postal_code, start_date_from, start_date_to, amount_min, amount_max, search)
    data = qs.get_funding_timeline(filters=filters)
    return {
        "labels": [d["year"] for d in data],
        "amounts": [d["total"] for d in data],
        "counts": [d["count"] for d in data],
    }


@router.get("/chart/{chart_type}", response_class=HTMLResponse)
def chart_expand_page(
    chart_type: str,
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
):
    valid = {"department", "program", "postal", "timeline"}
    if chart_type not in valid:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    filters = _build_filters(department, program, postal_code, start_date_from, start_date_to, amount_min, amount_max, search)
    filter_options = qs.get_filter_options()
    titles = {
        "department": "Funding by Department",
        "program": "Funding by Program",
        "postal": "Funding by Postal Code",
        "timeline": "Funding Timeline",
    }
    return templates.TemplateResponse("chart_view.html", {
        "request": request,
        "chart_type": chart_type,
        "title": titles[chart_type],
        "filter_options": filter_options,
        "filters": filters,
        "per_page": 50,  # needed by filter_panel partial
        "sort": "amount",
        "dir": "desc",
    })


@limiter.limit("20/minute")
@router.get("/api/map-points")
def map_points(
    request: Request,
    qs: RecordQueryService = Depends(get_query_service),
    department: str | None = None,
    program: str | None = None,
    postal_code: str | None = None,
    start_date_from: str | None = None,
    start_date_to: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    search: str | None = None,
):
    filters = _build_filters(department, program, postal_code, start_date_from, start_date_to, amount_min, amount_max, search)
    return qs.get_map_points(filters=filters)


@router.get("/map", response_class=HTMLResponse)
def map_page(
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
):
    filters = _build_filters(department, program, postal_code, start_date_from, start_date_to, amount_min, amount_max, search)
    filter_options = qs.get_filter_options()
    return templates.TemplateResponse("map_view.html", {
        "request": request,
        "filter_options": filter_options,
        "filters": filters,
    })
