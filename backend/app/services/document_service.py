import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import UploadFile
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.session import SessionLocal
from app.models import Document, DocumentChunk, DocumentPage, User
from app.models.document import (
    COMPLETED,
    FAILED,
    INDEX_FAILED,
    INDEX_INDEXED,
    INDEX_INDEXING,
    INDEX_PENDING,
    PENDING,
    PROCESSING,
)
from app.rag.embeddings import Embedder
from app.services.extraction import ExtractionError, extract_pages
from app.services.indexing_service import index_document
from app.services.storage import FileStorage, StorageError

logger = logging.getLogger(__name__)

PDF_SIGNATURE = b"%PDF-"
UPLOAD_CHUNK_BYTES = 1024 * 1024
FILENAME_MAX_LENGTH = 255
ERROR_MESSAGE_MAX_LENGTH = 255
STUCK_AFTER = timedelta(minutes=15)
GENERIC_FAILURE_MESSAGE = "Something went wrong while reading this document. Please try again."
INTERRUPTED_MESSAGE = "Processing was interrupted. Please upload again."
INDEX_INTERRUPTED_MESSAGE = "Indexing was interrupted. Please try again."


class DocumentNotFound(Exception):
    pass


class ReindexRejected(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UploadRejected(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def sanitize_filename(raw: str | None) -> str:
    # Keep only the final path segment, drop control characters, and cap the length.
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(char for char in name if char.isprintable()).strip()
    return name[:FILENAME_MAX_LENGTH] or "document.pdf"


def build_public_id(user_id: uuid.UUID, document_id: uuid.UUID) -> str:
    return f"documind/{user_id}/{document_id}"


def _read_upload(upload: UploadFile, max_mb: int) -> bytes:
    head = upload.file.read(len(PDF_SIGNATURE))
    if head != PDF_SIGNATURE:
        raise UploadRejected(415, "Only PDF files can be uploaded.")

    max_bytes = max_mb * 1024 * 1024
    data = bytearray(head)
    while chunk := upload.file.read(UPLOAD_CHUNK_BYTES):
        if len(data) + len(chunk) > max_bytes:
            raise UploadRejected(413, f"Files must be {max_mb} MB or smaller.")
        data.extend(chunk)
    return bytes(data)


def _delete_remote(storage: FileStorage, public_id: str) -> None:
    try:
        storage.delete(public_id)
    except StorageError:
        logger.exception("Could not delete stored file %s", public_id)


def store_upload(
    db: Session, settings: Settings, storage: FileStorage, user: User, upload: UploadFile
) -> Document:
    data = _read_upload(upload, settings.max_upload_mb)
    document_id = uuid.uuid4()
    public_id = build_public_id(user.id, document_id)

    # The file goes to storage first. If that fails, nothing is stored.
    storage.save(public_id, data)
    try:
        document = Document(
            id=document_id,
            user_id=user.id,
            filename=sanitize_filename(upload.filename),
            storage_path=public_id,
            size_bytes=len(data),
            status=PENDING,
        )
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        _delete_remote(storage, public_id)
        raise
    return document


def process_document(
    session_factory: sessionmaker[Session],
    settings: Settings,
    storage: FileStorage,
    embedder: Embedder,
    document_id: uuid.UUID,
) -> None:
    # Runs after the upload response is sent. Indexing starts only after extraction completes.
    if _extract(session_factory, settings, storage, document_id):
        index_document(session_factory, settings, embedder, document_id)


def _extract(
    session_factory: sessionmaker[Session],
    settings: Settings,
    storage: FileStorage,
    document_id: uuid.UUID,
) -> bool:
    # Opens its own session, because the request session closes when the response is sent.
    with session_factory() as db:
        document = db.get(Document, document_id)
        if document is None:
            return False
        document.status = PROCESSING
        db.commit()

        try:
            data = storage.download(document.storage_path)
            pages = extract_pages(data, settings.max_pages)
            db.add_all(
                DocumentPage(
                    document_id=document_id, page_number=number, text=text.replace("\x00", "")
                )
                for number, text in enumerate(pages, start=1)
            )
            document.page_count = len(pages)
            document.status = COMPLETED
            document.error_message = None
            document.index_status = INDEX_PENDING
            document.index_error = None
            db.commit()
            return True
        except StorageError as exc:
            _mark_failed(db, document_id, exc.message)
        except ExtractionError as exc:
            _mark_failed(db, document_id, exc.message)
        except Exception:
            logger.exception("Extraction failed for document %s", document_id)
            _mark_failed(db, document_id, GENERIC_FAILURE_MESSAGE)
        return False


def _mark_failed(db: Session, document_id: uuid.UUID, message: str) -> None:
    db.rollback()
    document = db.get(Document, document_id)
    if document is None:
        return
    document.status = FAILED
    document.error_message = message[:ERROR_MESSAGE_MAX_LENGTH]
    db.commit()


def list_documents(db: Session, user: User) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.user_id == user.id)
            .order_by(Document.created_at.desc(), Document.id)
        )
    )


def get_user_document(db: Session, user: User, document_id: uuid.UUID) -> Document:
    # Filtering by owner means another user's document looks the same as a missing one.
    document = db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise DocumentNotFound
    return document


def request_reindex(
    db: Session, settings: Settings, user: User, document_id: uuid.UUID
) -> Document:
    document = get_user_document(db, user, document_id)
    if document.status != COMPLETED:
        raise ReindexRejected("This document can't be indexed until its text is extracted.")
    if document.index_status in (INDEX_PENDING, INDEX_INDEXING):
        raise ReindexRejected("Indexing is already running for this document.")
    up_to_date = (
        document.index_status == INDEX_INDEXED
        and document.embedding_model == settings.embedding_model
        and document.chunk_target_chars == settings.chunk_target_chars
        and document.chunk_overlap_chars == settings.chunk_overlap_chars
    )
    if up_to_date:
        raise ReindexRejected("This document is already indexed with the current settings.")
    document.index_status = INDEX_PENDING
    document.index_error = None
    db.commit()
    return document


def delete_document(db: Session, storage: FileStorage, user: User, document_id: uuid.UUID) -> None:
    document = get_user_document(db, user, document_id)
    _delete_remote(storage, document.storage_path)
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
    db.delete(document)
    db.commit()


def recover_stuck_documents(db: Session, now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(UTC)) - STUCK_AFTER
    result = db.execute(
        update(Document)
        .where(
            Document.status.in_([PENDING, PROCESSING]),
            Document.updated_at < cutoff,
        )
        .values(status=FAILED, error_message=INTERRUPTED_MESSAGE)
    )
    index_result = db.execute(
        update(Document)
        .where(
            Document.index_status.in_([INDEX_PENDING, INDEX_INDEXING]),
            Document.updated_at < cutoff,
        )
        .values(index_status=INDEX_FAILED, index_error=INDEX_INTERRUPTED_MESSAGE)
    )
    db.commit()
    return result.rowcount + index_result.rowcount


def recover_stuck_documents_on_startup() -> None:
    try:
        with SessionLocal() as db:
            count = recover_stuck_documents(db)
    except SQLAlchemyError:
        logger.exception("Could not check for stuck documents on startup")
        return
    if count:
        logger.warning("Marked %d stuck document(s) as failed", count)
