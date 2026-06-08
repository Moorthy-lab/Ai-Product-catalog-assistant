import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings


@lru_cache
def load_catalog() -> dict[str, Any]:
    path: Path = get_settings().catalog_path
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def search_catalog(query: str, limit: int = 5) -> list[dict[str, Any]]:
    catalog = load_catalog()
    searchable_items: list[dict[str, Any]] = []

    for plan in catalog.get("plans", []):
        searchable_items.append({"type": "plan", **plan})
    for add_on in catalog.get("add_ons", []):
        searchable_items.append({"type": "add_on", **add_on})

    terms = {term.lower().strip(".,?!:;()") for term in query.split() if term.strip()}

    def item_score(item: dict[str, Any]) -> int:
        text = " ".join(
            [
                str(item.get("name", "")),
                str(item.get("price", "")),
                str(item.get("best_for", "")),
                " ".join(item.get("features", [])),
            ]
        ).lower()
        exact_name_boost = 4 if str(item.get("name", "")).lower() in query.lower() else 0
        return exact_name_boost + sum(1 for term in terms if term in text)

    ranked = sorted(searchable_items, key=item_score, reverse=True)
    return [item for item in ranked if item_score(item) > 0][:limit] or ranked[: min(limit, len(ranked))]
