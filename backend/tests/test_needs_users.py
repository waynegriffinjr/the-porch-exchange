from fastapi.testclient import TestClient


def test_unauthenticated_need_request_returns_401(client: TestClient):
    # Protected need routes should reject requests without a JWT.
    response = client.get("/needs/")

    # 401 means the request is missing valid authentication credentials.
    assert response.status_code == 401


def test_authenticated_user_can_create_a_need(client: TestClient, auth_headers):
    # Send a valid need request with the Bearer token from the auth_headers fixture.
    response = client.post(
        "/needs/",
        headers=auth_headers,
        json={
            "title": "Write tests",
            "description": "Cover the need endpoints",
            "priority": "high",
            "completed": False,
        },
    )

    # 201 means the API created a new resource successfully.
    assert response.status_code == 201
    body = response.json()
    # Check that the API returned the values submitted by the client.
    assert body["title"] == "Write tests"
    assert body["priority"] == "high"
    assert body["completed"] is False


def test_authenticated_user_can_list_only_their_needs(
    client: TestClient,
    auth_headers,
):
    # Create one need, then request the authenticated user's need collection.
    create_response = client.post(
        "/needs/",
        headers=auth_headers,
        json={"title": "User one need"},
    )
    assert create_response.status_code == 201

    list_response = client.get("/needs/", headers=auth_headers)

    # The list endpoint should return only this user's need.
    assert list_response.status_code == 200
    needs = list_response.json()
    assert len(needs) == 1
    assert needs[0]["title"] == "User one need"


def test_authenticated_user_can_retrieve_a_need(
    client: TestClient,
    auth_headers,
):
    # Create a need first so the test has a real database ID to retrieve.
    create_response = client.post(
        "/needs/",
        headers=auth_headers,
        json={"title": "Retrieve this need"},
    )
    need_id = create_response.json()["id"]

    # Fetch the need by ID using the same user's authentication header.
    response = client.get(f"/needs/{need_id}", headers=auth_headers)

    # Confirm both the status and the identity of the returned need.
    assert response.status_code == 200
    assert response.json()["id"] == need_id
    assert response.json()["title"] == "Retrieve this need"


def test_missing_need_returns_404(client: TestClient, auth_headers):
    # 99999 should not exist in the fresh test database.
    response = client.get("/needs/99999", headers=auth_headers)

    # The API should report a missing need instead of returning a server error.
    assert response.status_code == 404
    assert response.json()["detail"] == "Need not found"


def test_user_cannot_access_another_users_need(client: TestClient):
    first_user = client.post(
        "/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"},
    )
    assert first_user.status_code == 201
    first_token = client.post(
        "/auth/login",
        data={"username": "alice", "password": "password123"},
    ).json()["access_token"]

    second_user = client.post(
        "/auth/register",
        json={"username": "bob", "email": "bob@example.com", "password": "password123"},
    )
    assert second_user.status_code == 201
    second_token = client.post(
        "/auth/login",
        data={"username": "bob", "password": "password123"},
    ).json()["access_token"]

    created = client.post(
        "/needs/",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"title": "Alice's private need"},
    )
    assert created.status_code == 201

    response = client.get(
        f"/needs/{created.json()['id']}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to access this need"


def test_needs_can_be_filtered_and_paginated(client: TestClient, auth_headers):
    client.post("/needs/", headers=auth_headers, json={"title": "Open", "priority": "high"})
    client.post("/needs/", headers=auth_headers, json={"title": "Done", "priority": "high", "completed": True})

    response = client.get("/needs/?completed=true&priority=high&limit=1", headers=auth_headers)

    assert response.status_code == 200
    assert [need["title"] for need in response.json()] == ["Done"]


def test_partial_update_preserves_omitted_fields(client: TestClient, auth_headers):
    created = client.post(
        "/needs/",
        headers=auth_headers,
        json={"title": "Keep complete", "completed": True, "priority": "high"},
    ).json()

    response = client.patch(
        f"/needs/{created['id']}",
        headers=auth_headers,
        json={"title": "Renamed"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"
    assert response.json()["completed"] is True
    assert response.json()["priority"] == "high"


def test_profile_and_suggestion_routes_work(client: TestClient, auth_headers):
    profile = client.get("/users/me", headers=auth_headers)
    assert profile.status_code == 200
    assert "hashed_password" not in profile.json()

    created = client.post("/needs/", headers=auth_headers, json={"title": "Suggest this"}).json()
    suggestion = client.post(f"/needs/{created['id']}/suggest", headers=auth_headers)
    assert suggestion.status_code == 200
    assert "suggestion" in suggestion.json()


def test_skills_crud_is_user_scoped(client):
    client.post("/auth/register", json={"username": "skiller", "email": "s@example.com", "password": "password123"})
    token = client.post("/auth/login", data={"username": "skiller", "password": "password123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/skills/", json={"name": "Plumbing"}, headers=headers)
    assert created.status_code == 201
    assert [s["name"] for s in client.get("/skills/", headers=headers).json()] == ["Plumbing"]
    assert client.get("/skills/").status_code == 401
    assert client.delete(f"/skills/{created.json()['id']}", headers=headers).status_code == 204
    assert client.get("/skills/", headers=headers).json() == []
