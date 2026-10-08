from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl

class CreateUrlRequest(BaseModel):
    url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None 

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