import pytest
from fastapi.testclient import TestClient

import app.db as db
from app.db import initialize_database
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_url_shortener.db"

    monkeypatch.setattr(db, "DB_PATH", test_db_path)

    initialize_database()

    with TestClient(app) as test_client:
        yield test_client