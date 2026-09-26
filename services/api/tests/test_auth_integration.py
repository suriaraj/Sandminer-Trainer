"""End-to-end auth smoke against an isolated, migrated test database."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="Requires migrated test PostgreSQL")
def test_register_login_rotate_logout_all():
    client = TestClient(app)
    email = f"session-{uuid4().hex}@example.test"
    password = f"LocalOnly{uuid4().hex}!"

    registration = client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "Test Account",
    })
    assert registration.status_code == 201, registration.text
    assert registration.json()["access_token"]

    logged_in = client.post("/api/v1/auth/login", json={
        "email": email, "password": password,
    })
    assert logged_in.status_code == 200, logged_in.text
    access = logged_in.json()["access_token"]
    refresh = logged_in.json()["refresh_token"]
    sessions = client.get("/api/v1/auth/sessions", headers={
        "Authorization": f"Bearer {access}",
    })
    assert sessions.status_code == 200
    assert len(sessions.json()) == 2

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != refresh
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401

    logout = client.post("/api/v1/auth/logout-all", headers={
        "Authorization": f"Bearer {rotated.json()['access_token']}",
    })
    assert logout.status_code == 200
    after = client.get("/api/v1/auth/sessions", headers={
        "Authorization": f"Bearer {rotated.json()['access_token']}",
    })
    assert after.status_code == 401
