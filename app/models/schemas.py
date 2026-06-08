from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class EvalBlock(BaseModel):
    groundedness: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    flagged: bool
    reasoning: str


class ChatResponse(BaseModel):
    response: str
    eval: EvalBlock
    tools_called: list[str]
    session_id: str


class MessageOut(BaseModel):
    role: str
    content: str
    session_id: str
    created_at: datetime


class HistoryResponse(BaseModel):
    user_id: str
    messages: list[MessageOut]


class MemoryResetResponse(BaseModel):
    user_id: str
    deleted_messages: int
    deleted_memory_facts: int
    deleted_evals: int
    deleted_flags: int


class CatalogResponse(BaseModel):
    plans: list[dict]
    add_ons: list[dict] = []


class HealthResponse(BaseModel):
    status: str


class EvalAggregateResponse(BaseModel):
    user_id: str
    total_responses: int
    average_groundedness: float
    average_relevance: float
    average_confidence: float
    high_confidence_rate: float
    flagged_rate: float
