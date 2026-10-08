from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.models import (
    AnalyticsResponse,
    CreateUrlRequest,
    CreateUrlResponse,
)
from app.services.url_service import UrlService


router = APIRouter()
url_service = UrlService()


@router.get("/health")
async def health_check():
    return {
        "status": "UP",
        "service": "agentic-url-shortener",
    }


@router.post(
    "/api/v1/urls",
    response_model=CreateUrlResponse,
)
async def create_url(
    request: Request,
    payload: CreateUrlRequest,
):
    base_url = str(request.base_url).rstrip("/")

    try:
        return url_service.create_short_url(
            payload,
            base_url,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )


@router.get(
    "/api/v1/urls/{short_code}/analytics",
    response_model=AnalyticsResponse,
)
async def get_analytics(short_code: str):

    analytics = url_service.get_analytics(short_code)

    if not analytics:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found",
        )

    return analytics


@router.delete(
    "/api/v1/urls/{short_code}",
)
async def delete_url(short_code: str):

    deleted = url_service.delete_url(short_code)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found",
        )

    return {
        "message": "URL deleted successfully",
        "short_code": short_code,
    }


@router.get(
    "/{short_code}",
)
async def redirect_url(short_code: str):

    original_url = url_service.get_url(short_code)

    if not original_url:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found or expired",
        )

    return RedirectResponse(
        url=original_url,
        status_code=307,
    )