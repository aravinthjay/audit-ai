"""Knowledge-base routes - policy sources backing the Evidence agent's RAG."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db_session
from app.knowledge.retriever import (
    db_knowledge_chunks,
    knowledge_chunks,
    knowledge_sources as load_knowledge_sources,
    retrieve_knowledge_context,
    retrieve_knowledge_context_from_db,
    sync_knowledge_embeddings,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _public_chunks(chunks: list[dict]) -> list[dict]:
    return [{key: value for key, value in chunk.items() if key != "embedding"} for chunk in chunks]


@router.get("/sources")
async def knowledge_sources(
    user=Depends(get_current_user),
):
    """The policy/knowledge sources available to the Evidence agent."""
    return load_knowledge_sources()


@router.get("/chunks")
async def chunks(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Return indexed policy/data chunks used by local RAG retrieval."""
    rows = db_knowledge_chunks(db)
    return _public_chunks(rows or knowledge_chunks())


@router.get("/search")
async def search(
    q: str,
    limit: int = 5,
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Hybrid lexical/vector search over local RAG chunks."""
    bounded_limit = max(1, min(limit, 20))
    try:
        return retrieve_knowledge_context_from_db(db, q, limit=bounded_limit)
    except Exception:  # noqa: BLE001
        return retrieve_knowledge_context(q, limit=bounded_limit)


@router.post("/reindex")
async def reindex(
    db: Session = Depends(get_db_session),
    user=Depends(get_current_user),
):
    """Sync curated policy/data chunks into the vector embedding table."""
    return sync_knowledge_embeddings(db)
