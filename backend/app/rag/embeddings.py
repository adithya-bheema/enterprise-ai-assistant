from functools import lru_cache

from langchain_core.embeddings import Embeddings

from ..config import settings


@lru_cache
def get_embeddings() -> Embeddings:
    """Embedding model selected by EMBEDDING_PROVIDER (gemini | huggingface)."""
    if settings.embedding_provider == "huggingface":
        # Needs requirements-hf.txt (sentence-transformers + torch).
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=settings.hf_embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )

    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set (required for Gemini embeddings)")

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.google_api_key,
        output_dimensionality=settings.embedding_dim,
    )
