from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Infrastructure ---
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/knowledge"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Auth ---
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 8
    allow_registration: bool = True

    # --- Gemini (chat model, and embeddings when provider=gemini) ---
    google_api_key: str = ""
    llm_model: str = "gemini-3.5-flash-lite"

    # --- Embeddings ---
    # "gemini"      -> Gemini embeddings (EMBEDDING_DIM defaults to 768)
    # "huggingface" -> local sentence-transformers model (set EMBEDDING_DIM to match,
    #                  e.g. 384 for all-MiniLM-L6-v2)
    embedding_provider: Literal["gemini", "huggingface"] = "gemini"
    gemini_embedding_model: str = "models/gemini-embedding-001"
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 768

    # --- Chunking / retrieval ---
    chunk_size: int = 1000
    chunk_overlap: int = 150
    fetch_k: int = 20  # candidates pulled from each of vector + keyword search
    top_k: int = 6  # chunks passed to the grader / generator
    max_query_rewrites: int = 1
    max_upload_mb: int = 25

    # Optional Hugging Face cross-encoder reranker (needs requirements-hf.txt)
    reranker_enabled: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
