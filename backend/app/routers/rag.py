"""Community document RAG endpoints: /ask, /ingest, /stats and /health."""

import functools

import chromadb
import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import rag
from app.auth import get_current_user
from app.config import settings
from app.models.user import User

router = APIRouter()


class AskRequest(BaseModel):
    """Request body for /ask."""

    question: str = Field(min_length=1, max_length=2000)


@functools.lru_cache(maxsize=1)
def get_collection():
    """Open (once) the persistent Chroma collection."""
    client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    return client.get_or_create_collection(settings.COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


@router.get("/health", tags=["health"])
def health():
    """Report backend status, Ollama connectivity, and chunk count."""
    try:
        r = requests.get(f"{settings.OLLAMA_URL}/api/tags", timeout=3)
        ollama_ok = r.status_code == 200
    except requests.RequestException:
        ollama_ok = False
    try:
        documents = get_collection().count()
    except Exception:
        documents = 0
    return {
        "status": "healthy",
        "ollama": "connected" if ollama_ok else "unavailable",
        "ollama_url": settings.OLLAMA_URL,
        "documents": documents,
    }


@router.post("/ingest")
def ingest(_: User = Depends(get_current_user)):
    """Re-index all documents (idempotent)."""
    collection = get_collection()
    return {"ingested": rag.ingest_docs(collection), "documents": collection.count()}


@router.get("/stats")
def stats(_: User = Depends(get_current_user)):
    """Return the number of indexed chunks."""
    return {"document_count": get_collection().count()}


@router.post("/ask")
def ask(req: AskRequest, _: User = Depends(get_current_user)):
    """Answer a question from the indexed community documents."""
    try:
        return rag.answer_question(get_collection(), req.question)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e}") from e


@router.post("/ask/stream")
def ask_stream(req: AskRequest, _: User = Depends(get_current_user)):
    """Stream an answer as NDJSON events (meta, token..., optional error)."""
    return StreamingResponse(
        rag.answer_question_stream(get_collection(), req.question),
        media_type="application/x-ndjson",
    )
