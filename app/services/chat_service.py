from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.sales_agent import SalesAssistantAgent
from app.memory.store import SqlAlchemyMemoryStore
from app.models.schemas import ChatResponse
from app.services.eval_service import EvalService
from app.tools.human import flag_for_human


class ChatService:
    def __init__(self) -> None:
        self.agent = SalesAssistantAgent()
        self.eval_service = EvalService()

    def chat(self, db: Session, user_id: str, message: str, session_id: str | None = None) -> ChatResponse:
        resolved_session_id = session_id or str(uuid4())
        memory_store = SqlAlchemyMemoryStore(db)

        memory_store.add_message(user_id=user_id, session_id=resolved_session_id, role="user", content=message)
        self._persist_interest_fact(memory_store, user_id, resolved_session_id, message)

        agent_result = self.agent.run(user_id=user_id, message=message, memory_store=memory_store)
        assistant_message = memory_store.add_message(
            user_id=user_id,
            session_id=resolved_session_id,
            role="assistant",
            content=agent_result.response,
        )

        eval_block = self.eval_service.score(
            user_message=message,
            response=agent_result.response,
            catalog_results=agent_result.catalog_results,
            memory_facts=agent_result.memory_facts,
        )

        tools_called = list(agent_result.tools_called)
        if eval_block.flagged:
            flag_for_human(user_id=user_id, session_id=resolved_session_id, reason=eval_block.reasoning, db=db)
            tools_called.append("flag_for_human")

        self.eval_service.log_eval(
            db=db,
            user_id=user_id,
            session_id=resolved_session_id,
            message_id=assistant_message.id,
            eval_block=eval_block,
            tools_called=tools_called,
        )

        return ChatResponse(
            response=agent_result.response,
            eval=eval_block,
            tools_called=tools_called,
            session_id=resolved_session_id,
        )

    def _persist_interest_fact(
        self,
        memory_store: SqlAlchemyMemoryStore,
        user_id: str,
        session_id: str,
        message: str,
    ) -> None:
        lowered = message.lower()
        plan_names = ["starter", "growth", "enterprise"]
        for plan in plan_names:
            if plan in lowered:
                memory_store.add_fact(user_id=user_id, session_id=session_id, fact=f"User asked about the {plan.title()} plan.")

        if any(term in lowered for term in ["sso", "audit", "sla", "security", "compliance"]):
            memory_store.add_fact(user_id=user_id, session_id=session_id, fact="User is interested in security and compliance features.")

        if any(term in lowered for term in ["price", "pricing", "cost", "how much"]):
            memory_store.add_fact(user_id=user_id, session_id=session_id, fact="User is evaluating pricing.")
