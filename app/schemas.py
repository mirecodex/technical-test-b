from pydantic import BaseModel, Field

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)

class QuestionResponse(BaseModel):
    question: str
    answer: str
    context_used: list[str]
    latency_sec: float

class DocumentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)

class DocumentAddedResponse(BaseModel):
    id: str
    status: str

class StatusResponse(BaseModel):
    qdrant_ready: bool
    in_memory_docs_count: int
    graph_ready: bool