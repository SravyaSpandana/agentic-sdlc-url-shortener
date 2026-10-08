from datetime import datetime
from typing import Optional

from app.db import get_connection


class UrlRepository:

    def create(
        self,
        short_code: str,
        original_url: str,
        created_at: datetime,
        expires_at: Optional[datetime],
    ) -> None:

        connection = get_connection()

        try:
            connection.execute(
                """
                INSERT INTO urls (
                    short_code,
                    original_url,
                    created_at,
                    expires_at,
                    click_count
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    short_code,
                    original_url,
                    created_at.isoformat(),
                    expires_at.isoformat()
                    if expires_at
                    else None,
                    0,
                ),
            )

            connection.commit()

        finally:
            connection.close()

    def find_by_short_code(self, short_code: str):
        connection = get_connection()

        try:
            return connection.execute(
                """
                SELECT *
                FROM urls
                WHERE short_code = ?
                """,
                (short_code,),
            ).fetchone()

        finally:
            connection.close()

    def exists(self, short_code: str) -> bool:
        connection = get_connection()

        try:
            row = connection.execute(
                """
                SELECT 1
                FROM urls
                WHERE short_code = ?
                """,
                (short_code,),
            ).fetchone()

            return row is not None

        finally:
            connection.close()

    def increment_click_count(
        self,
        short_code: str,
    ) -> None:

        connection = get_connection()

        try:
            connection.execute(
                """
                UPDATE urls
                SET click_count = click_count + 1
                WHERE short_code = ?
                """,
                (short_code,),
            )

            connection.commit()

        finally:
            connection.close()

    def delete(self, short_code: str) -> bool:
        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                DELETE FROM urls
                WHERE short_code = ?
                """,
                (short_code,),
            )

            connection.commit()

            return cursor.rowcount > 0

        finally:
            connection.close()