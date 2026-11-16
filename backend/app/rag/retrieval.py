import uuid
from collections.abc import Callable, Sequence

from app.rag.types import RetrievedChunk, SearchHit

EmbedQuery = Callable[[str], list[float]]
Search = Callable[[Sequence[uuid.UUID], list[float], int], list[SearchHit]]


def retrieve(
    query: str,
    document_ids: Sequence[uuid.UUID],
    top_k: int,
    embed_query: EmbedQuery,
    search: Search,
) -> list[RetrievedChunk]:
    """Embeds the query and returns the nearest chunks, closest first, ranked from 1."""
    vector = embed_query(query)
    hits = sorted(search(document_ids, vector, top_k), key=lambda hit: hit.distance)
    return [
        RetrievedChunk(
            rank=rank,
            text=hit.text,
            document_id=hit.document_id,
            filename=hit.filename,
            page_number=hit.page_number,
            chunk_index=hit.chunk_index,
            distance=hit.distance,
        )
        for rank, hit in enumerate(hits[:top_k], start=1)
    ]
