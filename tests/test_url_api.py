from datetime import datetime, timedelta, timezone


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "UP"
    assert body["service"] == "agentic-url-shortener"


def test_create_url(client):
    response = client.post(
        "/api/v1/urls",
        json={
            "url": "https://www.google.com",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "short_code" in body
    assert "short_url" in body
    assert body["original_url"] == "https://www.google.com/"
    assert body["expires_at"] is None


def test_create_url_with_custom_alias(client):
    response = client.post(
        "/api/v1/urls",
        json={
            "url": "https://www.google.com",
            "custom_alias": "google",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["short_code"] == "google"
    assert body["short_url"].endswith("/google")


def test_duplicate_custom_alias_returns_conflict(client):
    first_response = client.post(
        "/api/v1/urls",
        json={
            "url": "https://www.google.com",
            "custom_alias": "google",
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/api/v1/urls",
        json={
            "url": "https://www.example.com",
            "custom_alias": "google",
        },
    )

    assert second_response.status_code == 409

    assert "already exists" in second_response.json()["detail"]


def test_redirect_url(client):
    create_response = client.post(
        "/api/v1/urls",
        json={
            "url": "https://www.google.com",
        },
    )

    short_code = create_response.json()["short_code"]

    response = client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "https://www.google.com/"


def test_click_count_increases_after_redirect(client):
    create_response = client.post(
        "/api/v1/urls",
        json={
            "url": "https://www.google.com",
        },
    )

    short_code = create_response.json()["short_code"]

    analytics_before = client.get(
        f"/api/v1/urls/{short_code}/analytics"
    )

    assert analytics_before.status_code == 200
    assert analytics_before.json()["click_count"] == 0

    redirect_response = client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert redirect_response.status_code == 307

    analytics_after = client.get(
        f"/api/v1/urls/{short_code}/analytics"
    )

    assert analytics_after.status_code == 200
    assert analytics_after.json()["click_count"] == 1


def test_analytics_returns_url_information(client):
    create_response = client.post(
        "/api/v1/urls",
        json={
            "url": "https://www.google.com",
        },
    )

    short_code = create_response.json()["short_code"]

    response = client.get(
        f"/api/v1/urls/{short_code}/analytics"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["short_code"] == short_code
    assert body["original_url"] == "https://www.google.com/"
    assert body["click_count"] == 0
    assert body["created_at"] is not None


def test_expired_url_cannot_be_redirected(client):
    expired_time = (
        datetime.now(timezone.utc) - timedelta(minutes=5)
    ).isoformat()

    create_response = client.post(
        "/api/v1/urls",
        json={
            "url": "https://www.google.com",
            "expires_at": expired_time,
        },
    )

    assert create_response.status_code == 200

    short_code = create_response.json()["short_code"]

    response = client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert "expired" in response.json()["detail"]


def test_delete_url(client):
    create_response = client.post(
        "/api/v1/urls",
        json={
            "url": "https://www.google.com",
        },
    )

    short_code = create_response.json()["short_code"]

    delete_response = client.delete(
        f"/api/v1/urls/{short_code}"
    )

    assert delete_response.status_code == 200

    body = delete_response.json()

    assert body["short_code"] == short_code

    analytics_response = client.get(
        f"/api/v1/urls/{short_code}/analytics"
    )

    assert analytics_response.status_code == 404


def test_nonexistent_url_returns_404(client):
    response = client.get(
        "/does-not-exist",
        follow_redirects=False,
    )

    assert response.status_code == 404


def test_invalid_url_is_rejected(client):
    response = client.post(
        "/api/v1/urls",
        json={
            "url": "not-a-valid-url",
        },
    )

    assert response.status_code == 422