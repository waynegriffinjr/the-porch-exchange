import json

import chromadb
import pytest
from app import rag
from app.routers import rag as rag_router
from fastapi.testclient import TestClient


@pytest.fixture
def fake_collection(monkeypatch):
    col = chromadb.EphemeralClient().get_or_create_collection("t_router")
    monkeypatch.setattr(rag_router, "get_collection", lambda: col)
    return col


def test_root_returns_status_and_model(client: TestClient):
    data = client.get("/").json()
    assert data["status"] == "ok"
    assert "model" in data


def test_health_is_public_and_reports_fields(client: TestClient, fake_collection):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert {"status", "ollama", "documents"} <= data.keys()


@pytest.mark.parametrize("method,path", [("post", "/ask"), ("post", "/ingest"), ("get", "/stats")])
def test_document_routes_require_auth(client: TestClient, method, path):
    kwargs = {"json": {"question": "hi"}} if path == "/ask" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


def test_chunk_text_respects_size_and_splits_long_text():
    text = "\n\n".join(["word " * 60] * 6)
    chunks = rag.chunk_text(text, chunk_size=400, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 400 for c in chunks)


def test_ingest_stores_chunk_metadata(tmp_path):
    (tmp_path / "a.md").write_text("alpha\n\n" + "beta " * 300)
    (tmp_path / "skip.pdf").write_text("ignored")
    col = chromadb.EphemeralClient().get_or_create_collection("t_ingest")
    assert rag.ingest_docs(col, str(tmp_path)) == 1
    metas = col.get()["metadatas"]
    assert len(metas) > 1
    assert all(m["source"] == "a.md" and "chunk_index" in m for m in metas)


def test_ask_without_context_skips_llm(client: TestClient, auth_headers, fake_collection, monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda *a, **k: [])

    def fail(prompt):
        raise AssertionError("LLM should not be called")

    monkeypatch.setattr(rag, "generate", fail)
    data = client.post("/ask", json={"question": "anything"}, headers=auth_headers).json()
    assert data["confidence"] == "none"
    assert data["sources"] == []


def test_ask_with_context_returns_structured_answer(client: TestClient, auth_headers, fake_collection, monkeypatch):
    src = [{"source": "a.md", "chunk_index": 0, "distance": 0.3, "text": "hello"}]
    monkeypatch.setattr(rag, "retrieve", lambda *a, **k: src)
    monkeypatch.setattr(rag, "generate", lambda prompt: "an answer")
    data = client.post("/ask", json={"question": "hi"}, headers=auth_headers).json()
    assert data == {"answer": "an answer", "sources": src, "confidence": "high"}


def test_stats_returns_document_count(client: TestClient, auth_headers, fake_collection):
    data = client.get("/stats", headers=auth_headers).json()
    assert isinstance(data["document_count"], int)


def test_ask_stream_guardrail_skips_llm_and_streams_idk(client: TestClient, auth_headers, fake_collection, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("LLM must not be called without relevant context")

    monkeypatch.setattr(rag, "generate_stream", boom)
    response = client.post("/ask/stream", json={"question": "anything"}, headers=auth_headers)
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0]["type"] == "meta" and events[0]["confidence"] == "none"
    assert "I don't know" in events[1]["text"]


def test_ask_stream_yields_tokens_with_sources(client: TestClient, auth_headers, monkeypatch):
    source = {"source": "a.md", "chunk_index": 0, "text": "Food pantry.", "distance": 0.2}
    monkeypatch.setattr(rag, "retrieve", lambda *a, **k: [source])
    monkeypatch.setattr(rag_router, "get_collection", lambda: None)
    monkeypatch.setattr(rag, "generate_stream", lambda prompt: iter(["Hel", "lo"]))
    response = client.post("/ask/stream", json={"question": "food?"}, headers=auth_headers)
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0]["sources"][0]["source"] == "a.md"
    assert events[0]["confidence"] == "high"
    assert "".join(e["text"] for e in events if e["type"] == "token") == "Hello"
