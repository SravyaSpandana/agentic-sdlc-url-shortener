import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator



class CreateUrlRequest(BaseModel):
    url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in ("http", "https"):
            raise ValueError("Only http and https URLs are allowed")
        return value

    @field_validator("custom_alias")
    @classmethod
    def validate_custom_alias(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        if not 3 <= len(value) <= 30:
            raise ValueError(
                "Custom alias must be between 3 and 30 characters"
            )

        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError(
                "Custom alias may contain only letters, digits, "
                "hyphens, and underscores"
            )

        return value


class CreateUrlResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    expires_at: Optional[datetime] = None


class AnalyticsResponse(BaseModel):
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None