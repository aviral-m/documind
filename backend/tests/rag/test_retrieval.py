import uuid

from app.rag.retrieval import retrieve
from app.rag.types import SearchHit


def hit(distance: float, chunk_index: int, document_id: uuid.UUID) -> SearchHit:
    return SearchHit(
        text=f"chunk {chunk_index}",
        document_id=document_id,
        filename="policy.pdf",
        page_number=chunk_index + 1,
        chunk_index=chunk_index,
        distance=distance,
    )


def test_results_are_ordered_by_distance_and_ranked_from_one():
    document_id = uuid.uuid4()
    hits = [hit(0.4, 2, document_id), hit(0.1, 0, document_id), hit(0.2, 1, document_id)]

    results = retrieve(
        "query",
        [document_id],
        top_k=3,
        embed_query=lambda text: [1.0],
        search=lambda ids, vector, k: hits,
    )

    assert [result.chunk_index for result in results] == [0, 1, 2]
    assert [result.rank for result in results] == [1, 2, 3]
    assert results[0].filename == "policy.pdf"
    assert results[0].page_number == 1


def test_search_receives_the_document_ids_and_top_k():
    document_ids = [uuid.uuid4(), uuid.uuid4()]
    seen = {}

    def search(ids, vector, k):
        seen.update(ids=list(ids), vector=vector, k=k)
        return []

    retrieve(
        "what is it",
        document_ids,
        top_k=4,
        embed_query=lambda text: [0.5, 0.5],
        search=search,
    )

    assert seen == {"ids": document_ids, "vector": [0.5, 0.5], "k": 4}


def test_results_are_capped_at_top_k():
    document_id = uuid.uuid4()
    hits = [hit(float(index), index, document_id) for index in range(10)]

    results = retrieve(
        "query",
        [document_id],
        top_k=3,
        embed_query=lambda text: [1.0],
        search=lambda ids, vector, k: hits,
    )

    assert len(results) == 3
