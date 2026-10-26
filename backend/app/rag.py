"""RAG pipeline: chunking, ingestion, retrieval, and answer generation."""

import json
import os

import requests

from app.config import settings

SYSTEM_PROMPT = (
    "You are a helpful assistant for questions about the Blanchester, Ohio community. "
    "Answer ONLY from the provided context. If the context does not contain the answer, "
    'reply exactly: "I don\'t know based on the provided documents." '
    "Be concise and do not invent phone numbers, addresses, or hours."
)
NO_CONTEXT_ANSWER = (
    "I don't know based on the provided documents. No sufficiently relevant context was found for that question."
)
SUPPORTED_EXTENSIONS = (".txt", ".md")


def chunk_text(text, chunk_size=None, overlap=None):
    """Split text into chunks of at most chunk_size characters.

    Strategy: pack whole paragraphs into a chunk until the size limit is reached;
    a single paragraph longer than the limit is split with a character overlap.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP if overlap is None else overlap
    overlap = min(overlap, chunk_size // 2)
    chunks, current = [], ""
    for para in (p.strip() for p in text.split("\n\n")):
        if not para:
            continue
        if len(para) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            step = chunk_size - overlap
            chunks.extend(para[i : i + chunk_size] for i in range(0, len(para), step))
        elif len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def ingest_docs(collection, docs_dir=None):
    """Chunk every .txt/.md file in docs_dir and upsert into the collection.

    Returns the number of files ingested. Existing chunks for a file are removed
    first so re-ingesting never leaves stale chunks behind.
    """
    docs_dir = docs_dir or settings.DOCS_DIRECTORY
    files = 0
    for name in sorted(os.listdir(docs_dir)):
        if not name.lower().endswith(SUPPORTED_EXTENSIONS):
            continue
        with open(os.path.join(docs_dir, name), encoding="utf-8") as f:
            chunks = chunk_text(f.read().strip())
        collection.delete(where={"source": name})
        # Legacy whole-file records used the bare filename as their id.
        collection.delete(ids=[name])
        if not chunks:
            continue
        collection.upsert(
            ids=[f"{name}::{i}" for i in range(len(chunks))],
            documents=chunks,
            metadatas=[{"source": name, "chunk_index": i} for i in range(len(chunks))],
        )
        files += 1
    return files


def retrieve(collection, question, n_results=None, threshold=None):
    """Return chunks within the distance threshold, best match first."""
    n_results = n_results or settings.MAX_RESULTS
    threshold = settings.CONFIDENCE_THRESHOLD if threshold is None else threshold
    results = collection.query(query_texts=[question], n_results=max(1, n_results))
    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results["metadatas"] else []
    dists = results["distances"][0] if results["distances"] else []
    return [
        {
            "source": m.get("source", "unknown"),
            "chunk_index": m.get("chunk_index", 0),
            "distance": d,
            "text": t,
        }
        for t, m, d in zip(docs, metas, dists, strict=True)
        if d <= threshold
    ]


def build_prompt(question, sources):
    """Combine system instructions, retrieved context, and the question."""
    context = "\n\n".join(f"[{s['source']} #{s['chunk_index']}]\n{s['text']}" for s in sources)
    return f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}\nAnswer:"


def generate(prompt):
    """Generate an answer with Ollama. Raises requests.RequestException on failure."""
    r = requests.post(
        f"{settings.OLLAMA_URL}/api/generate",
        json={"model": settings.MODEL_NAME, "prompt": prompt, "stream": False},
        timeout=300,
    )
    r.raise_for_status()
    return r.json().get("response", "").strip()


def generate_stream(prompt):
    """Yield answer text pieces from Ollama as they are produced."""
    with requests.post(
        f"{settings.OLLAMA_URL}/api/generate",
        json={"model": settings.MODEL_NAME, "prompt": prompt, "stream": True},
        stream=True,
        timeout=300,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                yield json.loads(line).get("response", "")


def confidence_level(sources):
    """Map the best retrieval distance to none / medium / high."""
    if not sources:
        return "none"
    return "high" if sources[0]["distance"] < 0.5 else "medium"


def answer_question(collection, question):
    """Full RAG flow. Guardrail: with no relevant context, skip the LLM entirely."""
    sources = retrieve(collection, question)
    if not sources:
        return {"answer": NO_CONTEXT_ANSWER, "sources": [], "confidence": "none"}
    answer = generate(build_prompt(question, sources))
    return {"answer": answer, "sources": sources, "confidence": confidence_level(sources)}


def answer_question_stream(collection, question):
    """Yield NDJSON lines: a "meta" event (sources, confidence), then "token" events.

    The same guardrail applies: with no relevant context the LLM is never called.
    """
    sources = retrieve(collection, question)
    meta = {"type": "meta", "sources": sources, "confidence": confidence_level(sources)}
    yield json.dumps(meta) + "\n"
    if not sources:
        yield json.dumps({"type": "token", "text": NO_CONTEXT_ANSWER}) + "\n"
        return
    try:
        for piece in generate_stream(build_prompt(question, sources)):
            yield json.dumps({"type": "token", "text": piece}) + "\n"
    except requests.RequestException as e:
        yield json.dumps({"type": "error", "detail": f"Ollama error: {e}"}) + "\n"
