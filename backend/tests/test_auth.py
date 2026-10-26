"""Authentication tests: register, login, and protected routes."""

from fastapi.testclient import TestClient

USER = {"username": "alice", "email": "alice@example.com", "password": "password123"}


def test_register_returns_token(client: TestClient):
    response = client.post("/auth/register", json=USER)
    assert response.status_code == 201
    assert "access_token" in response.json()


def test_duplicate_registration_is_rejected(client: TestClient):
    client.post("/auth/register", json=USER)
    assert client.post("/auth/register", json=USER).status_code == 409


def test_invalid_registration_payload_returns_422(client: TestClient):
    bad = {"username": "x", "email": "not-an-email", "password": "1"}
    assert client.post("/auth/register", json=bad).status_code == 422


def test_login_with_valid_credentials_returns_token(client: TestClient):
    client.post("/auth/register", json=USER)
    response = client.post("/auth/login", data={"username": "alice", "password": "password123"})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_wrong_password_returns_401(client: TestClient):
    client.post("/auth/register", json=USER)
    response = client.post("/auth/login", data={"username": "alice", "password": "wrong"})
    assert response.status_code == 401


def test_protected_route_rejects_missing_and_garbage_tokens(client: TestClient):
    assert client.get("/users/me").status_code == 401
    headers = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/users/me", headers=headers).status_code == 401


def test_protected_route_accepts_valid_token(client: TestClient, auth_headers):
    response = client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
