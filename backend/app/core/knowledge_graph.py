from __future__ import annotations

from typing import Any, Dict, List, Optional

import networkx as nx
from neo4j import GraphDatabase


class KnowledgeGraphService:
    def __init__(self, uri: str, username: str, password: str):
        self.uri = uri or ""
        self.username = username
        self.password = password
        self.driver = None
        self.status = "memory"
        self.graph = nx.DiGraph()
        self.in_memory_graph: List[Dict[str, Any]] = []
        self._connect()

    def _connect(self) -> None:
        if not self.uri:
            self.status = "memory"
            return
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            self.status = "connected"
        except Exception:
            self.status = "memory"
            self.driver = None

    def write_repository_graph(self, repo_analysis: Dict[str, Any], ontology: Dict[str, Any]) -> Dict[str, Any]:
        repo_name = repo_analysis["repo"]["full_name"]
        self.graph = nx.DiGraph()
        self.graph.add_node(repo_name, type="Repository", name=repo_name, repo=repo_name)

        for entity in ontology.get("entities", []):
            label = entity.get("type") or "Entity"
            node_id = entity.get("entity_id") or entity.get("name") or f"entity:{len(self.graph.nodes)}"
            self.graph.add_node(node_id, type=label, name=entity.get("name", node_id), repo=repo_name)
            if entity.get("source_file"):
                self.graph.nodes[node_id]["source_file"] = entity.get("source_file")
            if entity.get("source_path"):
                self.graph.nodes[node_id]["source_path"] = entity.get("source_path")

        for relation in ontology.get("relationships", []):
            self.graph.add_edge(relation.get("start"), relation.get("end"), type=relation.get("type"), repo=repo_name)

        self.in_memory_graph = [
            {"type": "Repository", "name": repo_name},
            *[
                {"type": "File", "name": file["path"], "source": "repo-analysis"}
                for file in repo_analysis.get("files", [])[:25]
            ],
        ]

        if self.driver is not None:
            with self.driver.session(database="neo4j") as session:
                for node_id, data in self.graph.nodes(data=True):
                    session.run(
                        "MERGE (n:GraphNode {id: $id}) SET n.name = $name, n.type = $type, n.repo = $repo",
                        {"id": node_id, "name": data.get("name", node_id), "type": data.get("type", "Entity"), "repo": repo_name},
                    )
                for source, target, data in self.graph.edges(data=True):
                    session.run(
                        "MATCH (a:GraphNode {id: $source}), (b:GraphNode {id: $target}) MERGE (a)-[:REL {type: $type, repo: $repo}]->(b)",
                        {"source": source, "target": target, "type": data.get("type", "related"), "repo": repo_name},
                    )

        return {
            "status": "memory" if self.driver is None else "connected",
            "repo": repo_name,
            "graph_nodes": self.graph.number_of_nodes(),
            "graph_edges": self.graph.number_of_edges(),
            "graph_preview": self.in_memory_graph[:10],
        }

    def query(self, repo_name: str, label: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.driver is not None:
            with self.driver.session(database="neo4j") as session:
                rows = session.run(
                    "MATCH (n {repo: $repo}) RETURN n LIMIT 25",
                    {"repo": repo_name},
                )
                return [dict(record["n"].items()) for record in rows]

        matches: List[Dict[str, Any]] = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("repo") != repo_name:
                continue
            if label and data.get("type") != label:
                continue
            matches.append({"id": node_id, **data})
        return matches
