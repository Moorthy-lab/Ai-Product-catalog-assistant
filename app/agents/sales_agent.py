from dataclasses import dataclass

from app.memory.store import MemoryStore
from app.tools.catalog import search_catalog
from app.tools.memory import get_user_memory


@dataclass
class AgentResult:
    response: str
    catalog_results: list[dict]
    memory_facts: list[str]
    tools_called: list[str]


class SalesAssistantAgent:
    def run(self, user_id: str, message: str, memory_store: MemoryStore) -> AgentResult:
        tools_called: list[str] = []

        memory_facts = get_user_memory(user_id=user_id, query=message, memory_store=memory_store)
        tools_called.append("get_user_memory")

        search_query = self._expand_query_with_memory(message, memory_facts)
        catalog_results = search_catalog(search_query)
        tools_called.append("search_catalog")

        response = self._compose_response(message, catalog_results, memory_facts)
        return AgentResult(
            response=response,
            catalog_results=catalog_results,
            memory_facts=memory_facts,
            tools_called=tools_called,
        )

    def _expand_query_with_memory(self, message: str, memory_facts: list[str]) -> str:
        lowered = message.lower()
        if any(token in lowered for token in ["that", "those", "previous", "earlier", "include", "includes"]):
            return f"{message} {' '.join(memory_facts)}"
        return message

    def _compose_response(self, message: str, catalog_results: list[dict], memory_facts: list[str]) -> str:
        if not catalog_results:
            return "I could not find a matching catalog item. I can still help compare plans if you ask about Starter, Growth, Enterprise, or add-ons."

        primary = catalog_results[0]
        name = primary.get("name", "the matching catalog item")
        price = primary.get("price", "pricing not listed")
        features = primary.get("features", [])
        feature_text = ", ".join(features)

        lowered = message.lower()
        if any(term in lowered for term in ["include", "includes", "included", "sso", "audit", "sla"]):
            remembered = self._memory_reference(memory_facts)
            return f"{remembered}{name} is {price} and includes {feature_text}."

        if any(term in lowered for term in ["price", "pricing", "cost", "how much"]):
            return f"{name} is priced at {price}. It includes {feature_text}."

        if "compare" in lowered:
            snippets = [
                f"{item.get('name')} ({item.get('price')}): {', '.join(item.get('features', []))}"
                for item in catalog_results[:3]
            ]
            return "Here is the closest catalog comparison: " + " | ".join(snippets)

        best_for = primary.get("best_for")
        if best_for:
            return f"{name} is {price} and includes {feature_text}. It is best for {best_for}"
        return f"{name} is {price} and includes {feature_text}."

    def _memory_reference(self, memory_facts: list[str]) -> str:
        for fact in memory_facts:
            if "enterprise" in fact.lower():
                return "Since you were asking about Enterprise earlier, "
            if "growth" in fact.lower():
                return "Since you were asking about Growth earlier, "
            if "starter" in fact.lower():
                return "Since you were asking about Starter earlier, "
        return ""
