"""Local hybrid retriever for the curated policy corpus.

This is intentionally dependency-light. It gives local/dev runs real RAG context
without requiring an embedding service; the deterministic vectors can later be
swapped behind the same functions for pgvector-backed semantic retrieval.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import VectorEmbedding

_CORPUS_PATH = Path(__file__).with_name("corpus.json")
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)?")
_VECTOR_DIMENSIONS = 64
_SOURCE_TYPE = "knowledge_chunk"


def _token_list(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _tokens(text: str) -> set[str]:
    return set(_token_list(text))


def _chunk_text(chunk: dict[str, Any], source_title: str = "") -> str:
    return " ".join(
        [
            source_title,
            chunk.get("title", ""),
            chunk.get("section", ""),
            chunk.get("content", ""),
            " ".join(chunk.get("keywords", [])),
        ]
    )


def embed_text(text: str) -> list[float]:
    """Build a stable feature-hashing vector from text tokens.

    The output is deterministic and normalized. It is not a substitute for a
    production embedding model, but it gives retrieval a useful semantic-ish
    signal locally and keeps tests/development offline.
    """
    vector = [0.0] * _VECTOR_DIMENSIONS
    for token in _token_list(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % _VECTOR_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    return sum(a * b for a, b in zip(left, right))


@lru_cache(maxsize=1)
def load_corpus() -> dict[str, Any]:
    with _CORPUS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def knowledge_chunks() -> list[dict[str, Any]]:
    source_lookup = {source["id"]: source for source in load_corpus().get("sources", [])}
    chunks = []
    for chunk in load_corpus().get("chunks", []):
        source = source_lookup.get(chunk.get("source_id"), {})
        text = _chunk_text(chunk, source.get("title", ""))
        chunks.append(
            {
                **chunk,
                "source_title": source.get("title", ""),
                "embedding": embed_text(text),
                "token_count": len(_token_list(text)),
            }
        )
    return chunks


def knowledge_sources() -> list[dict[str, Any]]:
    corpus = load_corpus()
    chunks = knowledge_chunks()
    by_source: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        by_source.setdefault(chunk["source_id"], []).append(chunk)

    sources = []
    for source in corpus.get("sources", []):
        source_chunks = by_source.get(source["id"], [])
        citation_ids = [chunk["id"] for chunk in source_chunks]
        first_chunk = source_chunks[0] if source_chunks else {}
        sources.append(
            {
                **source,
                "count": f"{len(source_chunks)} chunks",
                "clause_preview": first_chunk.get("content", ""),
                "citation_ids": citation_ids,
            }
        )
    return sources


def _rank_chunks(query: str, chunks: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    query_terms = _tokens(query)
    query_vector = embed_text(query)
    if not query_terms:
        return chunks[:limit]

    ranked: list[tuple[float, float, float, dict[str, Any]]] = []
    for chunk in chunks:
        searchable = _chunk_text(chunk, chunk.get("source_title", ""))
        chunk_terms = _tokens(searchable)
        overlap = len(query_terms & chunk_terms)
        keyword_hits = sum(
            1 for keyword in chunk.get("keywords", []) if keyword.lower() in query.lower()
        )
        lexical_score = float(overlap + (keyword_hits * 2))
        vector_score = max(_cosine(query_vector, chunk.get("embedding", [])), 0.0)
        score = lexical_score + (vector_score * 3.0)
        if score <= 0:
            continue
        ranked.append((score, lexical_score, vector_score, chunk))

    ranked.sort(key=lambda item: (-item[0], item[3]["id"]))
    return [
        {
            **{key: value for key, value in chunk.items() if key != "embedding"},
            "score": round(score, 4),
            "lexical_score": round(lexical_score, 4),
            "vector_score": round(vector_score, 4),
        }
        for score, lexical_score, vector_score, chunk in ranked[:limit]
    ]


def retrieve_knowledge_context(query: str, limit: int = 5) -> list[dict[str, Any]]:
    return _rank_chunks(query, knowledge_chunks(), limit)


def sync_knowledge_embeddings(db: Session) -> dict[str, Any]:
    """Upsert corpus chunks into the vector_embeddings table."""
    synced = 0
    for chunk in knowledge_chunks():
        row = (
            db.query(VectorEmbedding)
            .filter(
                VectorEmbedding.source_type == _SOURCE_TYPE,
                VectorEmbedding.source_id == chunk["id"],
            )
            .first()
        )
        if row is None:
            row = VectorEmbedding(source_type=_SOURCE_TYPE, source_id=chunk["id"])
            db.add(row)

        row.content = chunk["content"]
        row.embedding = chunk["embedding"]
        row.meta = {
            "source_id": chunk["source_id"],
            "source_title": chunk.get("source_title", ""),
            "section": chunk.get("section", ""),
            "title": chunk.get("title", ""),
            "keywords": chunk.get("keywords", []),
            "token_count": chunk.get("token_count", 0),
        }
        synced += 1
    db.commit()
    return {"status": "success", "synced_chunks": synced}


def db_knowledge_chunks(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(VectorEmbedding)
        .filter(VectorEmbedding.source_type == _SOURCE_TYPE)
        .order_by(VectorEmbedding.source_id.asc())
        .all()
    )
    return [
        {
            "id": row.source_id,
            "source_id": (row.meta or {}).get("source_id", ""),
            "source_title": (row.meta or {}).get("source_title", ""),
            "section": (row.meta or {}).get("section", ""),
            "title": (row.meta or {}).get("title", row.source_id),
            "content": row.content,
            "keywords": (row.meta or {}).get("keywords", []),
            "token_count": (row.meta or {}).get("token_count", 0),
            "embedding": row.embedding or [],
        }
        for row in rows
    ]


def retrieve_knowledge_context_from_db(
    db: Session,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    chunks = db_knowledge_chunks(db)
    if not chunks:
        sync_knowledge_embeddings(db)
        chunks = db_knowledge_chunks(db)
    return _rank_chunks(query, chunks, limit)


def format_context(chunks: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"[{chunk['id']}] {chunk.get('source_title') or chunk.get('source_id')} "
        f"{chunk.get('section', '')}: {chunk.get('content', '')}"
        for chunk in chunks
    )
