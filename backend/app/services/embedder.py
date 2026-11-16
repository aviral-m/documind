from functools import lru_cache

from app.core.config import get_settings
from app.rag.embeddings import GeminiEmbedder


@lru_cache
def get_embedder() -> GeminiEmbedder:
    settings = get_settings()
    return GeminiEmbedder(
        api_key=settings.gemini_api_key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        batch_size=settings.embedding_batch_size,
    )
