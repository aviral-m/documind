import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.session import SessionLocal
from app.models import Document, DocumentPage, User
from app.models.document import COMPLETED, FAILED, PENDING, PROCESSING
from app.services.extraction import ExtractionError, extract_pages

logger = logging.getLogger(__name__)

PDF_SIGNATURE = b"%PDF-"
UPLOAD_CHUNK_BYTES = 1024 * 1024
FILENAME_MAX_LENGTH = 255
ERROR_MESSAGE_MAX_LENGTH = 255
STUCK_AFTER = timedelta(minutes=15)
GENERIC_FAILURE_MESSAGE = "Something went wrong while reading this document. Please try again."
INTERRUPTED_MESSAGE = "Processing was interrupted. Please upload again."


class DocumentNotFound(Exception):
    pass


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


def _write_upload(upload: UploadFile, destination: Path, max_mb: int) -> int:
    head = upload.file.read(len(PDF_SIGNATURE))
    if head != PDF_SIGNATURE:
        raise UploadRejected(415, "Only PDF files can be uploaded.")

    max_bytes = max_mb * 1024 * 1024
    size = len(head)
    with destination.open("wb") as out:
        out.write(head)
        while chunk := upload.file.read(UPLOAD_CHUNK_BYTES):
            size += len(chunk)
            if size > max_bytes:
                raise UploadRejected(413, f"Files must be {max_mb} MB or smaller.")
            out.write(chunk)
    return size


def store_upload(db: Session, settings: Settings, user: User, upload: UploadFile) -> Document:
    document_id = uuid.uuid4()
    relative = Path("uploads") / str(user.id) / f"{document_id}.pdf"
    destination = settings.storage_path / relative
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        size = _write_upload(upload, destination, settings.max_upload_mb)
        document = Document(
            id=document_id,
            user_id=user.id,
            filename=sanitize_filename(upload.filename),
            storage_path=relative.as_posix(),
            size_bytes=size,
            status=PENDING,
        )
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    return document


def process_document(
    session_factory: sessionmaker[Session], settings: Settings, document_id: uuid.UUID
) -> None:
    # Runs after the upload response is sent, so it opens its own session.
    with session_factory() as db:
        document = db.get(Document, document_id)
        if document is None:
            return
        document.status = PROCESSING
        db.commit()

        path = settings.storage_path / document.storage_path
        try:
            pages = extract_pages(path, settings.max_pages)
            db.add_all(
                DocumentPage(
                    document_id=document_id, page_number=number, text=text.replace("\x00", "")
                )
                for number, text in enumerate(pages, start=1)
            )
            document.page_count = len(pages)
            document.status = COMPLETED
            document.error_message = None
            db.commit()
        except ExtractionError as exc:
            _mark_failed(db, document_id, exc.message)
        except Exception:
            logger.exception("Extraction failed for document %s", document_id)
            _mark_failed(db, document_id, GENERIC_FAILURE_MESSAGE)


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


def delete_document(db: Session, settings: Settings, user: User, document_id: uuid.UUID) -> None:
    document = get_user_document(db, user, document_id)
    path = settings.storage_path / document.storage_path
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Could not delete stored file %s", path)
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
    db.commit()
    return result.rowcount


def recover_stuck_documents_on_startup() -> None:
    try:
        with SessionLocal() as db:
            count = recover_stuck_documents(db)
    except SQLAlchemyError:
        logger.exception("Could not check for stuck documents on startup")
        return
    if count:
        logger.warning("Marked %d stuck document(s) as failed", count)
