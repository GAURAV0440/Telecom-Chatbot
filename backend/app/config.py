from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "3GPP Standards RAG Assistant"

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"

    embedding_model: str = "BAAI/bge-small-en-v1.5"

    qdrant_path: str = "./backend/data/qdrant"
    qdrant_collection: str = "3gpp_documents"

    top_k: int = 10
    bm25_top_k: int = 10
    similarity_threshold: float = 0.65

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()