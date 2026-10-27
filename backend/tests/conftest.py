import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Must be set before the app is imported.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ["INGEST_ON_STARTUP"] = "false"
os.environ["SEED_DEMO_DATA"] = "false"

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test.db"  # Use a separate test database
# Tests use their own database so they do not modify needs.db.
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    # Replace the app's normal database dependency with the test database.
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the database before each test."""
    # A clean database keeps tests independent from one another.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Remove test data after the test finishes.
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app."""
    # TestClient sends requests to the app without starting a real web server.
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    # This fixture creates a user and returns the Bearer header used by protected routes.
    username = "testuser"
    password = "testpassword"

    register_response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": "testuser@example.com",
            "password": password,
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password,
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_user(client, auth_headers):
    """Unused placeholder for future tests involving a second user."""
    response = client.post(
        "/users",
        headers=auth_headers,
        json={
            "username": "sampleuser",
            "password": "samplepassword",
        },
    )
    return response.json()
