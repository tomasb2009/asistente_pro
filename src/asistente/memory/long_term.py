"""
Memoria persistente con Chroma + embeddings OpenAI (RAG).
"""

from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from asistente.config import get_settings

_store: Chroma | None = None


def get_vector_store() -> Chroma:
    global _store
    if _store is not None:
        return _store

    s = get_settings()
    path = Path(s.memory_dir) / "chroma"
    path.mkdir(parents=True, exist_ok=True)

    emb = OpenAIEmbeddings(
        api_key=s.openai_api_key,
        model=s.embedding_model,
    )
    _store = Chroma(
        collection_name="user_memory",
        embedding_function=emb,
        persist_directory=str(path),
    )
    return _store


def retrieve_context(query: str, k: int | None = None) -> str:
    """Texto listo para inyectar en el system prompt (vacío si no hay hits)."""
    s = get_settings()
    k = k if k is not None else s.rag_top_k
    if not query.strip():
        return ""

    vs = get_vector_store()
    docs = vs.similarity_search(query, k=k)
    if not docs:
        return ""
    lines = [d.page_content.strip() for d in docs if d.page_content.strip()]
    if not lines:
        return ""
    return "\n".join(f"- {line}" for line in lines)


def add_fact(text: str) -> None:
    """Añade un hecho a la memoria larga (id estable por contenido)."""
    import hashlib

    t = text.strip()
    if len(t) < 3:
        return

    try:
        vs = get_vector_store()
        doc_id = hashlib.sha256(t.encode("utf-8")).hexdigest()[:48]
        vs.add_texts([t], ids=[doc_id], metadatas=[{"source": "user"}])
    except Exception:
        # No tumbar el pipeline si Chroma/embeddings fallan
        return
