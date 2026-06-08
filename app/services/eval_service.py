from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.tables import ResponseEval
from app.models.schemas import EvalAggregateResponse, EvalBlock


class EvalService:
    def score(
        self,
        user_message: str,
        response: str,
        catalog_results: list[dict],
        memory_facts: list[str],
    ) -> EvalBlock:
        user_terms = {term.lower().strip(".,?!:;()") for term in user_message.split() if len(term) > 2}
        response_text = response.lower()
        relevance_hits = sum(1 for term in user_terms if term in response_text)
        relevance = min(1.0, 0.55 + (relevance_hits / max(len(user_terms), 1)) * 0.4)

        groundedness = 0.45
        if catalog_results:
            groundedness += 0.4
        if any(str(item.get("name", "")).lower() in response_text for item in catalog_results):
            groundedness += 0.1
        if any(str(item.get("price", "")).lower() in response_text for item in catalog_results):
            groundedness += 0.05
        groundedness = min(1.0, groundedness)

        memory_bonus = 0.08 if memory_facts else 0
        confidence = min(1.0, (groundedness * 0.62) + (relevance * 0.3) + memory_bonus)
        flagged = confidence < get_settings().confidence_flag_threshold

        if flagged:
            reasoning = "Low confidence because the answer had limited catalog grounding or relevance."
        elif memory_facts:
            reasoning = "Response is grounded in catalog results and uses stored user context."
        else:
            reasoning = "Response is grounded in catalog results. No prior user context was needed."

        return EvalBlock(
            groundedness=round(groundedness, 2),
            relevance=round(relevance, 2),
            confidence=round(confidence, 2),
            flagged=flagged,
            reasoning=reasoning,
        )

    def log_eval(
        self,
        db: Session,
        user_id: str,
        session_id: str,
        message_id: int,
        eval_block: EvalBlock,
        tools_called: list[str],
    ) -> ResponseEval:
        row = ResponseEval(
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            groundedness=eval_block.groundedness,
            relevance=eval_block.relevance,
            confidence=eval_block.confidence,
            flagged=eval_block.flagged,
            reasoning=eval_block.reasoning,
            tools_called=tools_called,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def aggregate_for_user(self, db: Session, user_id: str) -> EvalAggregateResponse:
        rows = list(db.scalars(select(ResponseEval).where(ResponseEval.user_id == user_id)))
        total = len(rows)
        if total == 0:
            return EvalAggregateResponse(
                user_id=user_id,
                total_responses=0,
                average_groundedness=0,
                average_relevance=0,
                average_confidence=0,
                high_confidence_rate=0,
                flagged_rate=0,
            )

        return EvalAggregateResponse(
            user_id=user_id,
            total_responses=total,
            average_groundedness=round(sum(row.groundedness for row in rows) / total, 2),
            average_relevance=round(sum(row.relevance for row in rows) / total, 2),
            average_confidence=round(sum(row.confidence for row in rows) / total, 2),
            high_confidence_rate=round(sum(1 for row in rows if row.confidence >= 0.8) / total, 2),
            flagged_rate=round(sum(1 for row in rows if row.flagged) / total, 2),
        )
