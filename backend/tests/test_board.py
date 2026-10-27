"""Public needs board and skill matching tests."""

from fastapi.testclient import TestClient


def make_user(client: TestClient, name: str) -> dict:
    """Register a user and return auth headers."""
    r = client.post(
        "/auth/register", json={"username": name, "email": f"{name}@example.com", "password": "password123"}
    )
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_board_requires_auth(client: TestClient):
    assert client.get("/board/").status_code == 401
    assert client.get("/board/matches").status_code == 401


def test_only_public_open_needs_appear_and_email_is_hidden(client: TestClient):
    alice = make_user(client, "alice")
    bob = make_user(client, "bobby")
    client.post("/needs/", headers=alice, json={"title": "Private", "is_public": False})
    client.post("/needs/", headers=alice, json={"title": "Ride to clinic", "is_public": True, "contact": "555-0100"})
    done = client.post("/needs/", headers=alice, json={"title": "Old", "is_public": True}).json()
    client.patch(f"/needs/{done['id']}", headers=alice, json={"completed": True})

    board = client.get("/board/", headers=bob).json()
    assert [n["title"] for n in board] == ["Ride to clinic"]
    assert board[0]["poster"] == "alice" and board[0]["contact"] == "555-0100"
    assert board[0]["is_mine"] is False
    assert "email" not in board[0]


def test_board_search_filters_results(client: TestClient):
    alice = make_user(client, "alice")
    client.post("/needs/", headers=alice, json={"title": "Lawn mowing", "is_public": True})
    client.post("/needs/", headers=alice, json={"title": "Grocery pickup", "is_public": True})
    titles = [n["title"] for n in client.get("/board/?search=grocery", headers=alice).json()]
    assert titles == ["Grocery pickup"]


def test_public_flag_can_be_toggled_with_patch(client: TestClient):
    alice = make_user(client, "alice")
    need = client.post("/needs/", headers=alice, json={"title": "Fix fence"}).json()
    assert need["is_public"] is False
    client.patch(f"/needs/{need['id']}", headers=alice, json={"is_public": True})
    assert len(client.get("/board/", headers=alice).json()) == 1


def test_my_matches_ranks_needs_by_my_skills_and_skips_my_own(client: TestClient):
    alice = make_user(client, "alice")
    bob = make_user(client, "bobby")
    client.post("/needs/", headers=alice, json={"title": "Need help with lawn mowing", "is_public": True})
    client.post("/needs/", headers=alice, json={"title": "Piano lessons", "is_public": True})
    client.post("/skills/", headers=bob, json={"name": "Lawn care", "description": "mowing and trimming"})
    client.post("/needs/", headers=bob, json={"title": "Lawn help for me", "is_public": True})

    matches = client.get("/board/matches", headers=bob).json()
    assert [m["title"] for m in matches] == ["Need help with lawn mowing"]
    assert matches[0]["matched_skills"] == ["Lawn care"]


def test_need_matches_lists_neighbors_with_fitting_skills(client: TestClient):
    alice = make_user(client, "alice")
    bob = make_user(client, "bobby")
    carol = make_user(client, "carol")
    client.post("/skills/", headers=bob, json={"name": "Gardening"})
    client.post("/skills/", headers=carol, json={"name": "Tax preparation"})
    need = client.post("/needs/", headers=alice, json={"title": "Help with garden weeding"}).json()

    matches = client.get(f"/needs/{need['id']}/matches", headers=alice).json()
    assert [m["username"] for m in matches] == ["bobby"]
    assert client.get(f"/needs/{need['id']}/matches", headers=bob).status_code == 403
    assert client.get("/needs/9999/matches", headers=alice).status_code == 404
