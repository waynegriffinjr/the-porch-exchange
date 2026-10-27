# frontend/api_client.py
import json
import os

import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000")  # FastAPI backend


def login(username: str, password: str):
    """Authenticate and return a JWT token."""
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"An error occurred: {e}")
        raise Exception("Unable to connect to the server. Is the backend running?") from None


def get_needs(token: str):
    """Fetch all needs for the authenticated user."""
    try:
        response = requests.get(
            f"{API_URL}/needs/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if response.status_code == 401:
            return "unauthorized"  # Signal that the token expired
        if response.ok:
            return response.json()
    except requests.exceptions.ConnectionError as e:
        print(f"An error occurred: {e}")
        raise Exception("Unable to complete your request. Is the backend running?") from None


def create_need(token: str, title: str, description: str = "", is_public: bool = False, contact: str = ""):
    """Create a new need, optionally shared on the public board."""
    try:
        response = requests.post(
            f"{API_URL}/needs/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": title,
                "description": description,
                "is_public": is_public,
                "contact": contact.strip() or None,
            },
            timeout=10,
        )
        return response.ok
    except requests.exceptions.ConnectionError as e:
        print(f"An error occurred: {e}")
        raise Exception("Unable to connect to the server. Is the backend running?") from None


def update_need_met(token: str, need_id: int, completed: bool):
    """Mark a need as met or not met."""
    try:
        response = requests.patch(
            f"{API_URL}/needs/{need_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"completed": completed},
            timeout=10,
        )
        return response.ok
    except requests.exceptions.ConnectionError as e:
        print(f"An error occurred: {e}")
        raise Exception("Unable to connect to the server. Is the backend running?") from None


def get_health():
    """Return backend/Ollama/index status, or None if the API is unreachable."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=3)
        return response.json() if response.ok else None
    except requests.exceptions.RequestException:
        return None


def reindex_documents(token: str):
    """Re-index the community documents. Returns the JSON result or None."""
    try:
        response = requests.post(
            f"{API_URL}/ingest",
            headers={"Authorization": f"Bearer {token}"},
            timeout=300,
        )
        return response.json() if response.ok else None
    except requests.exceptions.RequestException:
        return None


def ask_documents(token: str, question: str):
    """Ask the RAG endpoint a question. Raises Exception with a readable message on failure."""
    try:
        response = requests.post(
            f"{API_URL}/ask",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": question},
            timeout=300,
        )
    except requests.exceptions.RequestException as error:
        raise Exception(f"Unable to reach the document assistant: {error}") from None
    if response.status_code == 401:
        raise PermissionError("Session expired. Please log in again.")
    if not response.ok:
        raise Exception(response.json().get("detail", response.text))
    return response.json()


def ask_documents_stream(token: str, question: str):
    """Yield (event_type, payload) tuples: ("meta", dict) first, then ("token", str)."""
    try:
        response = requests.post(
            f"{API_URL}/ask/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": question},
            stream=True,
            timeout=300,
        )
    except requests.exceptions.RequestException as error:
        raise Exception(f"Unable to reach the document assistant: {error}") from None
    if response.status_code == 401:
        raise PermissionError("Session expired. Please log in again.")
    if not response.ok:
        raise Exception(response.text)
    for line in response.iter_lines():
        if not line:
            continue
        event = json.loads(line)
        if event["type"] == "meta":
            yield "meta", event
        elif event["type"] == "token":
            yield "token", event["text"]
        else:
            raise Exception(event.get("detail", "Streaming failed"))


def get_skills(token: str):
    """Fetch the skills the user can offer, 'unauthorized' on 401."""
    try:
        response = requests.get(f"{API_URL}/skills/", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if response.status_code == 401:
            return "unauthorized"
        return response.json() if response.ok else []
    except requests.exceptions.ConnectionError:
        raise Exception("Unable to connect to the server. Is the backend running?") from None


def create_skill(token: str, name: str, description: str = ""):
    """Add a skill the user can offer."""
    try:
        response = requests.post(
            f"{API_URL}/skills/",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": name, "description": description},
            timeout=10,
        )
        return response.ok
    except requests.exceptions.ConnectionError:
        raise Exception("Unable to connect to the server. Is the backend running?") from None


def delete_skill(token: str, skill_id: int):
    """Delete a skill by id."""
    try:
        response = requests.delete(
            f"{API_URL}/skills/{skill_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return response.ok
    except requests.exceptions.ConnectionError:
        raise Exception("Unable to connect to the server. Is the backend running?") from None


def _get_json(token: str, path: str, params: dict | None = None):
    """GET an authenticated JSON endpoint; returns 'unauthorized' on 401 and [] on other errors."""
    try:
        response = requests.get(
            f"{API_URL}{path}", headers={"Authorization": f"Bearer {token}"}, params=params, timeout=10
        )
    except requests.exceptions.RequestException:
        raise Exception("Unable to connect to the server. Is the backend running?") from None
    if response.status_code == 401:
        return "unauthorized"
    return response.json() if response.ok else []


def get_board(token: str, search: str = ""):
    """Fetch open needs shared on the public board."""
    return _get_json(token, "/board/", {"search": search} if search.strip() else None)


def get_my_matches(token: str):
    """Fetch public needs that fit the user's skills."""
    return _get_json(token, "/board/matches")


def get_need_matches(token: str, need_id: int):
    """Fetch neighbors whose skills fit one of the user's needs."""
    return _get_json(token, f"/needs/{need_id}/matches")


def update_need_public(token: str, need_id: int, is_public: bool, contact: str | None = None):
    """Share or unshare a need on the public board."""
    payload = {"is_public": is_public}
    if contact is not None:
        payload["contact"] = contact.strip() or None
    try:
        response = requests.patch(
            f"{API_URL}/needs/{need_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=10,
        )
        return response.ok
    except requests.exceptions.RequestException:
        raise Exception("Unable to connect to the server. Is the backend running?") from None
