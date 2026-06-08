from app.memory.store import MemoryStore


def get_user_memory(user_id: str, query: str, memory_store: MemoryStore) -> list[str]:
    return [fact.fact for fact in memory_store.get_relevant_facts(user_id=user_id, query=query)]
