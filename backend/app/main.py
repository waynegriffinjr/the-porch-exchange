# /app/main.py
# Module 5 Project — AI-Ready Task Manager API
#

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import rag
from app.config import settings
from app.database import Base, engine

log_dir = Path(__file__).resolve().parent.parent
log_file = log_dir / "task_activity.log"

logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


from app.exceptions import APIException
from app.models import skill as _skill_model  # noqa: F401  (registers table)
from app.routers import auth, skills, tasks
from app.routers import rag as rag_router

tags_metadata = [
    {
        "name": "Authentication",
        "description": "User registration and login. All protected endpoints require a Bearer token.",
    },
    {
        "name": "Documents",
        "description": "Ask questions about indexed community documents (RAG). Requires authentication.",
    },
    {"name": "Tasks", "description": "CRUD operations for tasks. Most endpoints require authentication."},
]

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Index the community documents when the server starts."""
    if settings.INGEST_ON_STARTUP:
        try:
            rag.ingest_docs(rag_router.get_collection())
        except Exception:
            logger.exception("Document ingestion on startup failed")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Needs Manager Dashboard API",
    description="""
    A needs management API with JWT authentication, Pydantic validation,
    SQLAlchemy persistence, and a RAG question-answering endpoint over
    community documents (ChromaDB + Ollama).

    ## Quick Start
    1. Register at `POST /auth/register`
    2. Copy the `access_token` from the response
    3. Click **Authorize** above and paste the token
    4. Start creating and managing needs!
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
)


@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error": {"code": exc.code, "message": exc.message}},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(auth.users_router, prefix="/users", tags=["users"])

app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(skills.router, prefix="/skills", tags=["skills"])
app.include_router(rag_router.router, tags=["Documents"])


@app.get("/", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Task Manager API is running",
        "model": settings.MODEL_NAME,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
