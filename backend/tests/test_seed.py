"""Demo seed data tests."""

from app.seed import DEMO_PASSWORD, DEMO_PEOPLE, seed_demo_data
from conftest import TestingSession


def test_demo_data_shape():
    assert len(DEMO_PEOPLE) == 15
    for skills, needs in DEMO_PEOPLE.values():
        assert len(skills) == 5 and len(needs) == 2


def test_seed_is_idempotent_and_populates_board(client):
    with TestingSession() as db:
        assert seed_demo_data(db) == 15
        assert seed_demo_data(db) == 0

    login = client.post("/auth/login", data={"username": "tom_becker", "password": DEMO_PASSWORD})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert len(client.get("/board/?limit=100", headers=headers).json()) == 30
    assert len(client.get("/skills/", headers=headers).json()) == 5
    assert client.get("/board/matches", headers=headers).json()
