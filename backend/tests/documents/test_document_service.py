import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Document
from app.models.document import COMPLETED, FAILED, PENDING, PROCESSING
from app.services.document_service import (
    INTERRUPTED_MESSAGE,
    delete_document,
    recover_stuck_documents,
    sanitize_filename,
)
from app.services.extraction import (
    NO_TEXT_MESSAGE,
    TOO_MANY_PAGES_MESSAGE,
    ExtractionError,
    extract_pages,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("report.pdf", "report.pdf"),
        ("C:\\Users\\me\\Downloads\\report.pdf", "report.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("bad\x00name\x07.pdf", "badname.pdf"),
        ("", "document.pdf"),
        (None, "document.pdf"),
        ("a" * 300 + ".pdf", "a" * 255),
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


def test_extract_pages_returns_text_per_page(tmp_path, make_pdf):
    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf(["alpha", "beta", "gamma"]))

    pages = extract_pages(path, max_pages=500)

    assert len(pages) == 3
    assert "alpha" in pages[0]
    assert "gamma" in pages[2]


def test_extract_pages_rejects_too_many_pages(tmp_path, make_pdf):
    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf(["one", "two", "three"]))

    with pytest.raises(ExtractionError) as excinfo:
        extract_pages(path, max_pages=2)

    assert excinfo.value.message == TOO_MANY_PAGES_MESSAGE.format(max_pages=2)


def test_extract_pages_rejects_image_only_or_blank_pdf(tmp_path, make_pdf):
    path = tmp_path / "blank.pdf"
    path.write_bytes(make_pdf(["", ""]))

    with pytest.raises(ExtractionError) as excinfo:
        extract_pages(path, max_pages=500)

    assert excinfo.value.message == NO_TEXT_MESSAGE


def add_document(db, user, status, updated_at):
    document = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        filename="doc.pdf",
        storage_path=f"uploads/{user.id}/doc.pdf",
        size_bytes=10,
        status=status,
        updated_at=updated_at,
    )
    db.add(document)
    db.commit()
    return document


def test_recovery_fails_only_old_unfinished_documents(db, make_user):
    user = make_user()
    now = datetime.now(UTC)
    old = now - timedelta(hours=1)
    stale_pending = add_document(db, user, PENDING, old)
    stale_processing = add_document(db, user, PROCESSING, old)
    fresh_processing = add_document(db, user, PROCESSING, now)
    old_completed = add_document(db, user, COMPLETED, old)

    count = recover_stuck_documents(db, now=now)

    assert count == 2
    db.refresh(stale_pending)
    db.refresh(stale_processing)
    db.refresh(fresh_processing)
    db.refresh(old_completed)
    assert stale_pending.status == FAILED
    assert stale_pending.error_message == INTERRUPTED_MESSAGE
    assert stale_processing.status == FAILED
    assert fresh_processing.status == PROCESSING
    assert old_completed.status == COMPLETED


def test_deleting_document_whose_file_is_already_gone(db, make_user, storage_settings):
    user = make_user()
    document = add_document(db, user, COMPLETED, datetime.now(UTC))
    document_id = document.id

    delete_document(db, storage_settings, user, document_id)

    assert db.get(Document, document_id) is None
