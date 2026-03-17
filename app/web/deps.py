from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.db import RecordQueryService


def get_query_service(request: Request) -> RecordQueryService:
    return request.app.state.query_service


def get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates
