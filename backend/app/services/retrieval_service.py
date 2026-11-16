import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.chunk_queries import search_chunks
from app.models import Document, User
from app.models.document import INDEX_INDEXED
from app.rag.embeddings import Embedder
from app.rag.retrieval import retrieve
from app.rag.types import RetrievedChunk
from app.services.document_service import DocumentNotFound


class DocumentNotReady(Exception):
    pass


def search_documents(
    db: Session,
    embedder: Embedder,
    user: User,
    query: str,
    document_ids: list[uuid.UUID],
    top_k: int,
) -> list[RetrievedChunk]:
    unique_ids = list(dict.fromkeys(document_ids))
    # Ownership is checked here, and the chunk search filters on the owner again.
    documents = db.scalars(
        select(Document).where(Document.id.in_(unique_ids), Document.user_id == user.id)
    ).all()
    if len(documents) != len(unique_ids):
        raise DocumentNotFound
    if any(document.index_status != INDEX_INDEXED for document in documents):
        raise DocumentNotReady

    return retrieve(
        query,
        unique_ids,
        top_k,
        embed_query=embedder.embed_query,
        search=lambda ids, vector, k: search_chunks(db, user.id, ids, vector, k),
    )
