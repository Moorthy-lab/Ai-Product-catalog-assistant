from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.memory.store import SqlAlchemyMemoryStore
from app.models.schemas import (
    CatalogResponse,
    ChatRequest,
    ChatResponse,
    EvalAggregateResponse,
    HealthResponse,
    HistoryResponse,
    MemoryResetResponse,
    MessageOut,
)
from app.services.chat_service import ChatService
from app.services.eval_service import EvalService
from app.tools.catalog import load_catalog


router = APIRouter()
chat_service = ChatService()
eval_service = EvalService()


@router.get("/")
def root():
    """Redirect root to API documentation"""
    return RedirectResponse(url="/docs")


@router.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Handle favicon requests to prevent 404 errors"""
    return None


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/catalog", response_model=CatalogResponse)
def catalog() -> CatalogResponse:
    return CatalogResponse(**load_catalog())


@router.post("/chat/{user_id}", response_model=ChatResponse)
def chat(user_id: str, payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return chat_service.chat(db=db, user_id=user_id, message=payload.message, session_id=payload.session_id)


@router.get("/chat/{user_id}/history", response_model=HistoryResponse)
def history(user_id: str, db: Session = Depends(get_db)) -> HistoryResponse:
    store = SqlAlchemyMemoryStore(db)
    messages = [
        MessageOut(role=row.role, content=row.content, session_id=row.session_id, created_at=row.created_at)
        for row in store.get_history(user_id)
    ]
    return HistoryResponse(user_id=user_id, messages=messages)


@router.delete("/chat/{user_id}/memory", response_model=MemoryResetResponse)
def reset_memory(user_id: str, db: Session = Depends(get_db)) -> MemoryResetResponse:
    counts = SqlAlchemyMemoryStore(db).reset_user(user_id)
    return MemoryResetResponse(user_id=user_id, **counts)


@router.get("/chat/{user_id}/evals", response_model=EvalAggregateResponse)
def evals(user_id: str, db: Session = Depends(get_db)) -> EvalAggregateResponse:
    return eval_service.aggregate_for_user(db=db, user_id=user_id)
