import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException

from app.schemas import (
    QuestionRequest, QuestionResponse, 
    DocumentRequest, DocumentAddedResponse, 
    StatusResponse
)
from app.config import Settings, VectorStoreError, EmbeddingError
from app.repositories import VectorStoreRepository, QdrantVectorStore, InMemoryVectorStore
from app.services import EmbeddingService, RagWorkflowService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# inti global variables
_settings: Settings | None = None
_vector_store: VectorStoreRepository | None = None
_embedding_service: EmbeddingService | None = None
_is_qdrant_ready: bool = False

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStoreRepository:
    global _vector_store, _is_qdrant_ready
    if _vector_store is None:
        try:
            _vector_store = QdrantVectorStore(settings)
            _is_qdrant_ready = True
            logger.warning("qrant connect, using connection")
        except VectorStoreError as e:
            logger.warning(f"check qdrant connection its failed, fallback to in-memory store: {e}")
            _vector_store = InMemoryVectorStore(settings.embedding_dim)
            _is_qdrant_ready = False
    return _vector_store

def get_embedding_service(settings: Settings = Depends(get_settings)) -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(settings.embedding_dim)
    return _embedding_service

def get_rag_workflow(request: Request) -> RagWorkflowService:
    return request.app.state.rag_workflow

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RAG application")
    settings = get_settings()
    vector_store = get_vector_store(settings)
    embedding_service = get_embedding_service(settings)
    
    app.state.rag_workflow = RagWorkflowService(
        vector_store=vector_store,
        embedding_service=embedding_service,
        search_limit=settings.vector_search_limit
    )
    logger.info("RAG application started successfully")
    yield
    logger.info("Shutting down RAG application")

app = FastAPI(title="Learning RAG Demo", lifespan=lifespan)

# --- ROUTES ---
@app.post("/ask", response_model=QuestionResponse)
def ask_question(
    req: QuestionRequest,
    rag_workflow: RagWorkflowService = Depends(get_rag_workflow)
):
    start = time.time()
    try:
        result = rag_workflow.ask(req.question)
        latency = round(time.time() - start, 3)
        return QuestionResponse(
            question=req.question,
            answer=result["answer"],
            context_used=result.get("context", []),
            latency_sec=latency
        )
    except (VectorStoreError, EmbeddingError) as e:
        logger.error(f"RAG workflow failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in ask endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add", response_model=DocumentAddedResponse)
def add_document(
    req: DocumentRequest,
    vector_store: VectorStoreRepository = Depends(get_vector_store),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
):
    try:
        doc_id = str(uuid.uuid4())
        embedding = embedding_service.embed(req.text)
        vector_store.add_document(doc_id, req.text, embedding)
        logger.info(f"Document added successfully with ID: {doc_id}")
        return DocumentAddedResponse(id=doc_id, status="added")
    except (VectorStoreError, EmbeddingError) as e:
        logger.error(f"Failed to add document: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in add endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", response_model=StatusResponse)
def status(
    request: Request,
    vector_store: VectorStoreRepository = Depends(get_vector_store)
):
    try:
        doc_count = vector_store.get_document_count()
        graph_ready = hasattr(request.app.state, "rag_workflow") and request.app.state.rag_workflow is not None
        return StatusResponse(
            qdrant_ready=_is_qdrant_ready,
            in_memory_docs_count=doc_count,
            graph_ready=graph_ready
        )
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))