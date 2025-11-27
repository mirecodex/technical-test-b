from pydantic_settings import BaseSettings
from fastapi import HTTPException, status


class Settings(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "demo_collection"
    embedding_dim: int = 128
    vector_search_limit: int = 2
    
    model_config = {
        "env_prefix": "RAG_",
        "case_sensitive": False
    }

#pakai super() untuk custom exceptions
class VectorStoreError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector store error: {detail}"
        )


class EmbeddingError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding error: {detail}"
        )

