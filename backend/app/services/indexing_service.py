import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.chunk_queries import replace_document_chunks
from app.models import Document, DocumentChunk, DocumentPage
from app.models.document import COMPLETED, INDEX_FAILED, INDEX_INDEXED, INDEX_INDEXING
from app.rag.chunking import chunk_pages
from app.rag.embeddings import Embedder, EmbeddingError

logger = logging.getLogger(__name__)

ERROR_MESSAGE_MAX_LENGTH = 255
GENERIC_INDEX_FAILURE_MESSAGE = "Indexing failed. Please try again."
NO_CHUNKS_MESSAGE = "No text could be indexed."


def index_document(
    session_factory: sessionmaker[Session],
    settings: Settings,
    embedder: Embedder,
    document_id: uuid.UUID,
) -> None:
    # Runs in the background task, so it opens its own session.
    with session_factory() as db:
        document = db.get(Document, document_id)
        if document is None or document.status != COMPLETED:
            return
        document.index_status = INDEX_INDEXING
        document.index_error = None
        db.commit()

        try:
            rows = db.execute(
                select(DocumentPage.page_number, DocumentPage.text)
                .where(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_number)
            ).all()
            # End the read transaction so none is open during the API calls.
            db.commit()

            chunks = chunk_pages(
                [(row.page_number, row.text) for row in rows],
                settings.chunk_target_chars,
                settings.chunk_overlap_chars,
            )
            if not chunks:
                _mark_failed(db, document_id, NO_CHUNKS_MESSAGE)
                return

            embeddings = embedder.embed_documents([chunk.text for chunk in chunks])

            replace_document_chunks(db, document_id, chunks, embeddings)
            document = db.get(Document, document_id)
            document.index_status = INDEX_INDEXED
            document.index_error = None
            document.chunk_count = len(chunks)
            document.embedding_model = settings.embedding_model
            document.chunk_target_chars = settings.chunk_target_chars
            document.chunk_overlap_chars = settings.chunk_overlap_chars
            document.indexed_at = datetime.now(UTC)
            db.commit()
        except EmbeddingError as exc:
            _mark_failed(db, document_id, exc.message)
        except Exception:
            logger.exception("Indexing failed for document %s", document_id)
            _mark_failed(db, document_id, GENERIC_INDEX_FAILURE_MESSAGE)


def _mark_failed(db: Session, document_id: uuid.UUID, message: str) -> None:
    db.rollback()
    # A failed document has no chunks, so a stale index can't be searched.
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    document = db.get(Document, document_id)
    if document is None:
        db.commit()
        return
    document.index_status = INDEX_FAILED
    document.index_error = message[:ERROR_MESSAGE_MAX_LENGTH]
    document.chunk_count = None
    db.commit()
