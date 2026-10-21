from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RepoDocumentChunk:
    id: str
    text: str
    source_path: str
    commit_sha: str
    line_start: int = 0
    line_end: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OntologyEntity:
    entity_id: str
    type: str
    name: str
    source_path: str
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OntologyRelationship:
    start: str
    end: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticQueryResult:
    entities: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]
