from abc import ABC, abstractmethod

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.tables import ConversationMessage, HumanFlag, ResponseEval, UserMemoryFact


class MemoryStore(ABC):
    @abstractmethod
    def add_message(self, user_id: str, session_id: str, role: str, content: str) -> ConversationMessage:
        raise NotImplementedError

    @abstractmethod
    def add_fact(self, user_id: str, session_id: str, fact: str) -> UserMemoryFact:
        raise NotImplementedError

    @abstractmethod
    def get_history(self, user_id: str) -> list[ConversationMessage]:
        raise NotImplementedError

    @abstractmethod
    def get_relevant_facts(self, user_id: str, query: str, limit: int = 6) -> list[UserMemoryFact]:
        raise NotImplementedError

    @abstractmethod
    def reset_user(self, user_id: str) -> dict[str, int]:
        raise NotImplementedError


class SqlAlchemyMemoryStore(MemoryStore):
    def __init__(self, db: Session):
        self.db = db

    def add_message(self, user_id: str, session_id: str, role: str, content: str) -> ConversationMessage:
        message = ConversationMessage(user_id=user_id, session_id=session_id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def add_fact(self, user_id: str, session_id: str, fact: str) -> UserMemoryFact:
        normalized = fact.strip()
        existing = self.db.scalar(
            select(UserMemoryFact).where(UserMemoryFact.user_id == user_id, UserMemoryFact.fact == normalized)
        )
        if existing:
            return existing

        memory_fact = UserMemoryFact(user_id=user_id, source_session_id=session_id, fact=normalized)
        self.db.add(memory_fact)
        self.db.commit()
        self.db.refresh(memory_fact)
        return memory_fact

    def get_history(self, user_id: str) -> list[ConversationMessage]:
        return list(
            self.db.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.user_id == user_id)
                .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
            )
        )

    def get_relevant_facts(self, user_id: str, query: str, limit: int = 6) -> list[UserMemoryFact]:
        facts = list(
            self.db.scalars(
                select(UserMemoryFact)
                .where(UserMemoryFact.user_id == user_id)
                .order_by(UserMemoryFact.created_at.desc(), UserMemoryFact.id.desc())
            )
        )
        terms = {term.lower().strip(".,?!:;()") for term in query.split() if len(term) > 2}

        def score(fact: UserMemoryFact) -> int:
            text = fact.fact.lower()
            return sum(1 for term in terms if term in text)

        ranked = sorted(facts, key=lambda item: (score(item), item.created_at, item.id), reverse=True)
        return ranked[:limit]

    def reset_user(self, user_id: str) -> dict[str, int]:
        tables = {
            "deleted_evals": ResponseEval,
            "deleted_flags": HumanFlag,
            "deleted_memory_facts": UserMemoryFact,
            "deleted_messages": ConversationMessage,
        }
        counts: dict[str, int] = {}
        for label, table in tables.items():
            result = self.db.execute(delete(table).where(table.user_id == user_id))
            counts[label] = result.rowcount or 0
        self.db.commit()
        return counts
