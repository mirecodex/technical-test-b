import random
import logging
from langgraph.graph import StateGraph, END
from app.repositories import VectorStoreRepository
from app.config import EmbeddingError


logger = logging.getLogger(__name__)


class EmbeddingService:
    
    def __init__(self, embedding_dim: int = 128):
        self._embedding_dim = embedding_dim
        logger.info(f"test intialze embedding service with dimention {embedding_dim}")
    
    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise EmbeddingError("cannot embed because its empty text")
        
        embedding = self._generate_embedding(text)
        
        if len(embedding) != self._embedding_dim:
            raise EmbeddingError(
                f"generated embedding dimension mismatch: expected {self._embedding_dim}, got {len(embedding)}"
            )
        
        return embedding
    
    def _generate_embedding(self, text: str) -> list[float]:
        random.seed(abs(hash(text)) % 10000)
        return [random.random() for _ in range(self._embedding_dim)]


class RagWorkflowService:
    
    def __init__(self, vector_store: VectorStoreRepository, embedding_service: EmbeddingService, search_limit: int = 2):
        self._vector_store = vector_store
        self._embedding_service = embedding_service
        self._search_limit = search_limit
        
        def retrieve_node(state: dict) -> dict:
            query = state["question"]
            embedding = self._embedding_service.embed(query)
            results = self._vector_store.search(embedding, limit=self._search_limit, query_text=query)
            state["context"] = results
            return state
        
        def answer_node(state: dict) -> dict:
            context = state.get("context", [])
            if context:
                answer = f"I found this: '{context[0][:100]}...'"
            else:
                answer = "Sorry, I don't know."
            state["answer"] = answer
            return state
        
        workflow = StateGraph(dict)
        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("answer", answer_node)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "answer")
        workflow.add_edge("answer", END)
        
        self._chain = workflow.compile()
        logger.info("RAG workflow initialized")
    
    def ask(self, question: str) -> dict:
        if not question or not question.strip():
            return {
                "question": question,
                "answer": "sorry, i don't get any knowledge",
                "context": []
            }
        
        result = self._chain.invoke({"question": question})
        return result

