import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.rag.types import Chunk, SearchHit


def replace_document_chunks(
    db: Session,
    document_id: uuid.UUID,
    chunks: Sequence[Chunk],
    embeddings: Sequence[list[float]],
) -> None:
    # The caller owns the transaction, so the delete and inserts commit together.
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    db.add_all(
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=document_id,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            embedding=embedding,
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    )
    db.flush()


def search_chunks(
    db: Session,
    user_id: uuid.UUID,
    document_ids: Sequence[uuid.UUID],
    query_embedding: list[float],
    top_k: int,
) -> list[SearchHit]:
    # Joining documents and filtering on user_id enforces ownership in the query itself.
    distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
    rows = db.execute(
        select(
            DocumentChunk.text,
            DocumentChunk.document_id,
            Document.filename,
            DocumentChunk.page_number,
            DocumentChunk.chunk_index,
            distance,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.user_id == user_id, DocumentChunk.document_id.in_(document_ids))
        .order_by(distance, DocumentChunk.document_id, DocumentChunk.chunk_index)
        .limit(top_k)
    ).all()
    return [
        SearchHit(
            text=row.text,
            document_id=row.document_id,
            filename=row.filename,
            page_number=row.page_number,
            chunk_index=row.chunk_index,
            distance=float(row.distance),
        )
        for row in rows
    ]
