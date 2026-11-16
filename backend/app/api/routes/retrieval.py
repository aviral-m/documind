from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import VerifiedUser
from app.db.session import get_db
from app.rag.embeddings import Embedder, EmbeddingError
from app.schemas.retrieval import RetrievedChunkOut, SearchRequest, SearchResponse
from app.services import retrieval_service
from app.services.document_service import DocumentNotFound
from app.services.embedder import get_embedder
from app.services.retrieval_service import DocumentNotReady

router = APIRouter(prefix="/retrieval", tags=["retrieval"])
DbSession = Annotated[Session, Depends(get_db)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]


@router.post("/search", response_model=SearchResponse)
def search(
    body: SearchRequest,
    user: VerifiedUser,
    db: DbSession,
    embedder: EmbedderDep,
) -> SearchResponse:
    try:
        results = retrieval_service.search_documents(
            db, embedder, user, body.query, body.document_ids, body.top_k
        )
    except DocumentNotFound as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc
    except DocumentNotReady as exc:
        raise HTTPException(
            status_code=422, detail="This document isn't ready for search yet."
        ) from exc
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    return SearchResponse(results=[RetrievedChunkOut.model_validate(item) for item in results])
