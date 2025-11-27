import logging
import threading
from abc import ABC, abstractmethod
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from qdrant_client.http.exceptions import UnexpectedResponse
from app.config import Settings, VectorStoreError


logger = logging.getLogger(__name__)


class VectorStoreRepository(ABC):
    
    @abstractmethod
    def add_document(self, id: str, text: str, embedding: list[float]) -> str:
        pass
    
    @abstractmethod
    def search(self, query_embedding: list[float], limit: int, query_text: str = "") -> list[str]:
        pass
    
    @abstractmethod
    def get_document_count(self) -> int:
        pass


class QdrantVectorStore(VectorStoreRepository):
    
    def __init__(self, settings: Settings):
        self._settings = settings
        self._expected_dim = settings.embedding_dim
        self._collection_name = settings.collection_name
        
        try:
            self._client = QdrantClient(settings.qdrant_url)
            self._client.recreate_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=settings.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            # logger.info(
            #     f"Initialized Qdrant vector store",
            #     extra={
            #         "qdrant_url": settings.qdrant_url,
            #         "collection_name": self._collection_name,
            #         "embedding_dim": settings.embedding_dim
            #     }
            # )
        except Exception as e:
            logger.error(f"failed to initialize Qdrant: {e}")
            raise VectorStoreError(f"failed to connect to Qdrant: {str(e)}") from e
    
    def add_document(self, id: str, text: str, embedding: list[float]) -> str:
        if not id:
            raise VectorStoreError("document id cannot be empty")
        if not text or not text.strip():
            raise VectorStoreError("document text also cannot be empty")
        if len(embedding) != self._expected_dim:
            raise VectorStoreError(
                f"embedding dimension mismatch: expected {self._expected_dim}, got {len(embedding)}"
            )
        
        try:
            self._client.upsert(
                collection_name=self._collection_name,
                points=[
                    PointStruct(
                        id=id,
                        vector=embedding,
                        payload={"text": text}
                    )
                ]
            )
            # logger.debug(f"added document {id} to Qdrant collection {self._collection_name}")
            return id
        except UnexpectedResponse as e:
            logger.error(f"qdrant upsert failed on docs {id}: {e}")
            raise VectorStoreError(f"failed to store the docs : {str(e)}") from e
    
    def search(self, query_embedding: list[float], limit: int = 2, query_text: str = "") -> list[str]:
        if limit <= 0:
            raise VectorStoreError("search limit must be positive")
        if len(query_embedding) != self._expected_dim:
            raise VectorStoreError(
                f"query embedding dimension mismatch: expected {self._expected_dim}, got {len(query_embedding)}"
            )
        
        try:
            hits = self._client.query_points(
                collection_name=self._collection_name,
                query=query_embedding,
                limit=limit
            ).points
            results = [hit.payload["text"] for hit in hits]
            # logger.debug(f"qdrant search returned {len(results)} results")
            return results
        except UnexpectedResponse as e:
            logger.error(f"qdrant search failed: {e}")
            raise VectorStoreError(f"failed to search documents: {str(e)}") from e
    
    def get_document_count(self) -> int:
        try:
            collection_info = self._client.get_collection(self._collection_name)
            return collection_info.points_count
        except UnexpectedResponse as e:
            logger.error(f"failed to get Qdrant collection info: {e}")
            return 0

# if failed to connect to qdrant, will go here as memory vector store (jadi harusnya ga nge crash atau throw error nanti)
class InMemoryVectorStore(VectorStoreRepository):
    
    def __init__(self, expected_dim: int = 128):
        self._storage: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._expected_dim = expected_dim
        logger.info("initialized in-memory vector store (fallback dari failed qdrant connection)")
    
    def add_document(self, id: str, text: str, embedding: list[float]) -> str:
        if not id:
            raise VectorStoreError("doc id cannot be empty")
        if not text or not text.strip():
            raise VectorStoreError("doc text also cannot be empty")
        if len(embedding) != self._expected_dim:
            raise VectorStoreError(
                f"embedding dimension mismatch: expected {self._expected_dim}, got {len(embedding)}"
            )
        
        with self._lock:
            self._storage[id] = {
                "text": text,
                "embedding": embedding
            }
        # check if the document already add to in memory store
        # logger.debug(f"added document {id} to in-memory store")
        return id
    
    def search(self, query_embedding: list[float], limit: int = 2, query_text: str = "") -> list[str]:
        if limit <= 0:
            raise VectorStoreError("Search limit must be positive")
        if len(query_embedding) != self._expected_dim:
            raise VectorStoreError(
                f"embedding dimension to big: expected {self._expected_dim}, got {len(query_embedding)}"
            )
        
        with self._lock:
            if not self._storage:
                return []
            
            results = []
            query_lower = query_text.lower() if query_text else ""
            
            if query_lower:
                for doc_id, doc_data in self._storage.items():
                    if query_lower in doc_data["text"].lower():
                        results.append(doc_data["text"])
                        if len(results) >= limit:
                            break
            
            if not results:
                for doc_id, doc_data in list(self._storage.items())[:limit]:
                    results.append(doc_data["text"])
            
            return results
    
    def get_document_count(self) -> int:
        with self._lock:
            return len(self._storage)

