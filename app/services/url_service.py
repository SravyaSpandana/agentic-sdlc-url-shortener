import secrets
import string
from datetime import datetime, timezone

from app.models import (
    AnalyticsResponse,
    CreateUrlRequest,
    CreateUrlResponse,
)
from app.repository.url_repository import UrlRepository


class UrlService:

    def __init__(self):
        self.repository = UrlRepository()

    def create_short_url(
        self,
        request: CreateUrlRequest,
        base_url: str,
    ) -> CreateUrlResponse:

        short_code = (
            request.custom_alias
            or self._generate_short_code()
        )

        if self.repository.exists(short_code):
            raise ValueError(
                f"Short code '{short_code}' already exists"
            )

        created_at = datetime.now(timezone.utc)

        self.repository.create(
            short_code=short_code,
            original_url=str(request.url),
            created_at=created_at,
            expires_at=request.expires_at,
        )

        return CreateUrlResponse(
            short_code=short_code,
            short_url=f"{base_url}/{short_code}",
            original_url=str(request.url),
            expires_at=request.expires_at,
        )

    def get_url(self, short_code: str):

        row = self.repository.find_by_short_code(
            short_code
        )

        if not row:
            return None

        if row["expires_at"]:
            expires_at = datetime.fromisoformat(
                row["expires_at"]
            )

            if expires_at <= datetime.now(timezone.utc):
                return None

        self.repository.increment_click_count(
            short_code
        )

        return row["original_url"]

    def get_analytics(
        self,
        short_code: str,
    ) -> AnalyticsResponse | None:

        row = self.repository.find_by_short_code(
            short_code
        )

        if not row:
            return None

        return AnalyticsResponse(
            short_code=row["short_code"],
            original_url=row["original_url"],
            click_count=row["click_count"],
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
            expires_at=(
                datetime.fromisoformat(row["expires_at"])
                if row["expires_at"]
                else None
            ),
        )

    def delete_url(self, short_code: str) -> bool:
        return self.repository.delete(short_code)

    @staticmethod
    def _generate_short_code(length: int = 7) -> str:

        characters = (
            string.ascii_letters +
            string.digits
        )

        return "".join(
            secrets.choice(characters)
            for _ in range(length)
        )