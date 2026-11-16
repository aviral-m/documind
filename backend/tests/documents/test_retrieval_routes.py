import uuid

import pytest

from app.models import Document
from app.models.document import INDEX_FAILED, INDEX_INDEXED
from app.rag.embeddings import EMBEDDING_FAILED_MESSAGE, EmbeddingError
from app.rag.types import SearchHit
from app.services import retrieval_service

BASE = "/api/v1/documents"
SEARCH = "/api/v1/retrieval/search"


def upload(client, headers, content: bytes, filename: str = "policy.pdf"):
    return client.post(
        BASE,
        headers=headers,
        files={"file": (filename, content, "application/pdf")},
    )


@pytest.fixture
def fake_search(monkeypatch):
    calls = []

    def search(db, user_id, document_ids, query_embedding, top_k):
        calls.append({"user_id": user_id, "document_ids": list(document_ids), "top_k": top_k})
        return [
            SearchHit(
                text="Refunds take fourteen days.",
                document_id=document_ids[0],
                filename="policy.pdf",
                page_number=2,
                chunk_index=5,
                distance=0.12,
            ),
            SearchHit(
                text="Other text.",
                document_id=document_ids[0],
                filename="policy.pdf",
                page_number=1,
                chunk_index=0,
                distance=0.4,
            ),
        ][:top_k]

    monkeypatch.setattr(retrieval_service, "search_chunks", search)
    return calls


def indexed_document(client, headers, make_pdf):
    document_id = upload(client, headers, make_pdf(["Refunds take fourteen days."])).json()["id"]
    return document_id


def test_search_returns_ranked_chunks_with_document_and_page(
    client, make_user, auth_headers, make_pdf, fake_search
):
    user = make_user()
    headers = auth_headers(user)
    document_id = indexed_document(client, headers, make_pdf)

    response = client.post(
        SEARCH,
        headers=headers,
        json={"query": "  how long do refunds take  ", "document_ids": [document_id], "top_k": 2},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["rank"] for item in results] == [1, 2]
    assert results[0] == {
        "rank": 1,
        "text": "Refunds take fourteen days.",
        "document_id": document_id,
        "filename": "policy.pdf",
        "page_number": 2,
        "chunk_index": 5,
        "distance": 0.12,
    }
    assert fake_search[0]["user_id"] == user.id
    assert fake_search[0]["top_k"] == 2


def test_duplicate_document_ids_are_searched_once(
    client, make_user, auth_headers, make_pdf, fake_search
):
    user = make_user()
    headers = auth_headers(user)
    document_id = indexed_document(client, headers, make_pdf)

    response = client.post(
        SEARCH, headers=headers, json={"query": "refunds", "document_ids": [document_id] * 3}
    )

    assert response.status_code == 200
    assert fake_search[0]["document_ids"] == [uuid.UUID(document_id)]


def test_another_users_document_looks_missing(
    client, make_user, auth_headers, make_pdf, fake_search
):
    alice = make_user()
    bob = make_user()
    document_id = indexed_document(client, auth_headers(alice), make_pdf)

    response = client.post(
        SEARCH,
        headers=auth_headers(bob),
        json={"query": "refunds", "document_ids": [document_id]},
    )

    assert response.status_code == 404
    assert fake_search == []


def test_document_that_is_not_indexed_is_not_ready(
    client, make_user, auth_headers, make_pdf, embedder, fake_search
):
    user = make_user()
    headers = auth_headers(user)
    embedder.fail_with = EmbeddingError(EMBEDDING_FAILED_MESSAGE)
    document_id = indexed_document(client, headers, make_pdf)

    response = client.post(
        SEARCH, headers=headers, json={"query": "refunds", "document_ids": [document_id]}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "This document isn't ready for search yet."
    assert fake_search == []


def test_embedding_outage_on_search_returns_503(
    client, make_user, auth_headers, make_pdf, embedder, fake_search
):
    user = make_user()
    headers = auth_headers(user)
    document_id = indexed_document(client, headers, make_pdf)
    embedder.fail_with = EmbeddingError(EMBEDDING_FAILED_MESSAGE)

    response = client.post(
        SEARCH, headers=headers, json={"query": "refunds", "document_ids": [document_id]}
    )

    assert response.status_code == 503
    assert response.json()["detail"] == EMBEDDING_FAILED_MESSAGE


@pytest.mark.parametrize(
    "body",
    [
        {"query": "   ", "document_ids": ["{id}"]},
        {"query": "x" * 1001, "document_ids": ["{id}"]},
        {"query": "refunds", "document_ids": []},
        {"query": "refunds", "document_ids": ["{id}"] * 21},
        {"query": "refunds", "document_ids": ["{id}"], "top_k": 0},
        {"query": "refunds", "document_ids": ["{id}"], "top_k": 21},
    ],
)
def test_request_limits_are_enforced(client, make_user, auth_headers, body, fake_search):
    user = make_user()
    document_id = str(uuid.uuid4())
    body = {
        key: [document_id if item == "{id}" else item for item in value]
        if isinstance(value, list)
        else value
        for key, value in body.items()
    }

    response = client.post(SEARCH, headers=auth_headers(user), json=body)

    assert response.status_code == 422
    assert fake_search == []


def test_search_requires_a_verified_user(client, make_user, auth_headers):
    unverified = make_user(verified=False)
    body = {"query": "refunds", "document_ids": [str(uuid.uuid4())]}

    assert client.post(SEARCH, json=body).status_code == 401
    assert client.post(SEARCH, headers=auth_headers(unverified), json=body).status_code == 403


def test_reindex_runs_in_the_background_and_completes(
    client, make_user, auth_headers, make_pdf, db, embedder
):
    user = make_user()
    headers = auth_headers(user)
    document_id = indexed_document(client, headers, make_pdf)
    document = db.get(Document, uuid.UUID(document_id))
    document.index_status = INDEX_FAILED
    db.commit()

    response = client.post(f"{BASE}/{document_id}/reindex", headers=headers)

    assert response.status_code == 202
    # The background task writes through its own session, so drop this session's stale copy.
    db.expire_all()
    body = client.get(f"{BASE}/{document_id}", headers=headers).json()
    assert body["index_status"] == INDEX_INDEXED
    assert body["chunk_count"] == 1


def test_reindex_of_an_up_to_date_document_is_a_conflict(client, make_user, auth_headers, make_pdf):
    user = make_user()
    headers = auth_headers(user)
    document_id = indexed_document(client, headers, make_pdf)

    response = client.post(f"{BASE}/{document_id}/reindex", headers=headers)

    assert response.status_code == 409


def test_reindex_by_another_user_looks_missing(client, make_user, auth_headers, make_pdf):
    alice = make_user()
    bob = make_user()
    document_id = indexed_document(client, auth_headers(alice), make_pdf)

    response = client.post(f"{BASE}/{document_id}/reindex", headers=auth_headers(bob))

    assert response.status_code == 404


def test_upload_reports_index_status_and_chunk_count(client, make_user, auth_headers, make_pdf):
    user = make_user()
    headers = auth_headers(user)

    document_id = indexed_document(client, headers, make_pdf)

    body = client.get(f"{BASE}/{document_id}", headers=headers).json()
    assert body["index_status"] == INDEX_INDEXED
    assert body["index_error"] is None
    assert body["chunk_count"] == 1


def test_failed_indexing_reports_its_message(client, make_user, auth_headers, make_pdf, embedder):
    user = make_user()
    headers = auth_headers(user)
    embedder.fail_with = EmbeddingError(EMBEDDING_FAILED_MESSAGE)

    document_id = indexed_document(client, headers, make_pdf)

    body = client.get(f"{BASE}/{document_id}", headers=headers).json()
    assert body["status"] == "completed"
    assert body["index_status"] == INDEX_FAILED
    assert body["index_error"] == EMBEDDING_FAILED_MESSAGE
