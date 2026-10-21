from __future__ import annotations

from typing import Any, Dict, List

from app.models import SemanticQueryResult


class SemanticLayer:
    def __init__(self):
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.relations: List[Dict[str, Any]] = []

    def register(self, ontology: Dict[str, Any]) -> None:
        for entity in ontology.get("entities", []):
            self.entities[entity["entity_id"]] = entity
        for relation in ontology.get("relationships", []):
            self.relations.append(relation)

    def query(self, entity_type: str | None = None, name: str | None = None, limit: int = 25) -> SemanticQueryResult:
        matches = []
        for entity in self.entities.values():
            if entity_type and entity.get("type") != entity_type:
                continue
            if name and name.lower() not in entity.get("name", "").lower():
                continue
            matches.append(entity)
        return SemanticQueryResult(entities=matches[:limit], relations=self.relations[:limit])

    def summary(self) -> Dict[str, Any]:
        by_type: Dict[str, int] = {}
        for entity in self.entities.values():
            by_type[entity.get("type", "Unknown")] = by_type.get(entity.get("type", "Unknown"), 0) + 1
        return {
            "entity_count": len(self.entities),
            "relationship_count": len(self.relations),
            "by_type": by_type,
        }
