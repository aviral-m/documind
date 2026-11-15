import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.models import Document, DocumentPage
from app.services.document_service import GENERIC_FAILURE_MESSAGE

BASE = "/api/v1/documents"


def upload(client, headers, content: bytes, filename: str = "report.pdf"):
    return client.post(
        BASE,
        headers=headers,
        files={"file": (filename, content, "application/pdf")},
    )


def test_upload_is_extracted_into_pages(client, make_user, auth_headers, make_pdf, db):
    user = make_user()
    headers = auth_headers(user)

    response = upload(client, headers, make_pdf(["First page text", "Second page text"]))

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    document_id = response.json()["id"]

    response = client.get(f"{BASE}/{document_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["page_count"] == 2
    assert body["error_message"] is None
    assert body["filename"] == "report.pdf"

    pages = db.scalars(
        select(DocumentPage)
        .where(DocumentPage.document_id == uuid.UUID(document_id))
        .order_by(DocumentPage.page_number)
    ).all()
    assert [page.page_number for page in pages] == [1, 2]
    assert "First page text" in pages[0].text
    assert "Second page text" in pages[1].text


def test_non_pdf_content_is_rejected_even_with_pdf_name(client, make_user, auth_headers, db):
    user = make_user()

    response = upload(client, auth_headers(user), b"just some text", filename="notes.pdf")

    assert response.status_code == 415
    assert db.scalars(select(Document)).all() == []


def test_oversized_upload_is_rejected_and_not_kept(
    client, make_user, auth_headers, storage_settings, tmp_path
):
    user = make_user()
    client.app.dependency_overrides[get_settings] = lambda: storage_settings.model_copy(
        update={"max_upload_mb": 1}
    )
    too_big = b"%PDF-" + b"0" * (1024 * 1024)

    response = upload(client, auth_headers(user), too_big)

    assert response.status_code == 413
    assert list(tmp_path.rglob("*.pdf")) == []


def test_blank_pdf_is_marked_failed_without_text(client, make_user, auth_headers, make_pdf):
    user = make_user()
    headers = auth_headers(user)

    document_id = upload(client, headers, make_pdf([""])).json()["id"]

    body = client.get(f"{BASE}/{document_id}", headers=headers).json()
    assert body["status"] == "failed"
    assert body["error_message"] == "No extractable text. OCR isn't supported yet."


def test_damaged_pdf_is_marked_failed(client, make_user, auth_headers):
    user = make_user()
    headers = auth_headers(user)

    document_id = upload(client, headers, b"%PDF-1.4 not really a pdf").json()["id"]

    body = client.get(f"{BASE}/{document_id}", headers=headers).json()
    assert body["status"] == "failed"
    assert body["error_message"]


def test_library_lists_only_the_current_users_documents(client, make_user, auth_headers, make_pdf):
    alice = make_user()
    bob = make_user()
    upload(client, auth_headers(alice), make_pdf(["Alice text"]), filename="alice.pdf")
    upload(client, auth_headers(bob), make_pdf(["Bob text"]), filename="bob.pdf")

    response = client.get(BASE, headers=auth_headers(alice))

    assert response.status_code == 200
    assert [item["filename"] for item in response.json()] == ["alice.pdf"]


def test_other_users_document_looks_missing(client, make_user, auth_headers, make_pdf):
    alice = make_user()
    bob = make_user()
    document_id = upload(client, auth_headers(alice), make_pdf(["Alice text"])).json()["id"]

    assert client.get(f"{BASE}/{document_id}", headers=auth_headers(bob)).status_code == 404
    assert client.delete(f"{BASE}/{document_id}", headers=auth_headers(bob)).status_code == 404
    assert client.get(f"{BASE}/{uuid.uuid4()}", headers=auth_headers(alice)).status_code == 404


def test_delete_removes_rows_and_file(
    client, make_user, auth_headers, make_pdf, db, storage_settings
):
    user = make_user()
    headers = auth_headers(user)
    document_id = upload(client, headers, make_pdf(["Some text"])).json()["id"]
    stored = db.get(Document, uuid.UUID(document_id)).storage_path
    file_path = storage_settings.storage_path / stored
    assert file_path.exists()

    response = client.delete(f"{BASE}/{document_id}", headers=headers)

    assert response.status_code == 204
    assert not file_path.exists()
    assert db.get(Document, uuid.UUID(document_id)) is None
    assert db.scalars(select(DocumentPage)).all() == []
    assert client.get(f"{BASE}/{document_id}", headers=headers).status_code == 404


def test_unverified_user_is_forbidden(client, make_user, auth_headers):
    user = make_user(verified=False)

    response = client.get(BASE, headers=auth_headers(user))

    assert response.status_code == 403


def test_signed_out_request_is_unauthorized(client):
    assert client.get(BASE).status_code == 401
    assert (
        client.post(BASE, files={"file": ("a.pdf", b"%PDF-", "application/pdf")}).status_code == 401
    )


def test_failure_message_is_generic_when_extraction_crashes(
    client, make_user, auth_headers, make_pdf, monkeypatch
):
    import app.services.document_service as document_service

    def explode(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(document_service, "extract_pages", explode)
    user = make_user()
    headers = auth_headers(user)

    document_id = upload(client, headers, make_pdf(["text"])).json()["id"]

    body = client.get(f"{BASE}/{document_id}", headers=headers).json()
    assert body["status"] == "failed"
    assert body["error_message"] == GENERIC_FAILURE_MESSAGE
    assert "secret" not in body["error_message"]
