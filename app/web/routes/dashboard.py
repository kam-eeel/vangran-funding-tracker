from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.db import RecordQueryService
from app.web.deps import get_query_service, get_templates

router = APIRouter()


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
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "kpis": kpis}
    )


@router.get("/api/charts/department")
def chart_department(qs: RecordQueryService = Depends(get_query_service)):
    data = qs.get_funding_by_department()
    return {
        "labels": [d["short_name"] for d in data],
        "data": [d["total"] for d in data],
        "counts": [d["count"] for d in data],
        "full_names": [d["name"] for d in data],
    }


@router.get("/api/charts/program")
def chart_program(qs: RecordQueryService = Depends(get_query_service)):
    data = qs.get_funding_by_program()
    return {
        "labels": [d["name"] for d in data],
        "data": [d["total"] for d in data],
        "counts": [d["count"] for d in data],
    }


@router.get("/api/charts/postal")
def chart_postal(qs: RecordQueryService = Depends(get_query_service)):
    data = qs.get_funding_by_postal_code()
    return {
        "labels": [d["fsa"] for d in data],
        "data": [d["total"] for d in data],
        "counts": [d["count"] for d in data],
    }


@router.get("/api/charts/timeline")
def chart_timeline(qs: RecordQueryService = Depends(get_query_service)):
    data = qs.get_funding_timeline()
    return {
        "labels": [d["year"] for d in data],
        "amounts": [d["total"] for d in data],
        "counts": [d["count"] for d in data],
    }
