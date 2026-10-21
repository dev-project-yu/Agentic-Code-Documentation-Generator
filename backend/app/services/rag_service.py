from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.model = None
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception:
            self.model = None

    def embed(self, text: str) -> List[float]:
        if self.model is None:
            return [0.0] * 384
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()


class RAGService:
    def __init__(self, persist_directory: Path | None = None):
        self.persist_directory = persist_directory or Path(__file__).resolve().parents[2] / "state" / "vector-index"
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.embedding_service = EmbeddingService()
        self.docs: List[Dict[str, Any]] = []

    def index_repository(self, repo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        docs: List[Dict[str, Any]] = []
        repo_name = repo_analysis.get("repo", {}).get("full_name", "unknown")

        docs.append({"id": "overview", "text": f"{repo_name}\n{repo_analysis.get('readme_summary', '')}", "metadata": {"type": "overview", "repo": repo_name}})
        for file in repo_analysis.get("files", [])[:200]:
            docs.append({"id": file["path"], "text": f"File: {file['path']}\nExtension: {file.get('extension', '')}", "metadata": {"type": "file", "repo": repo_name, "path": file["path"]}})
        for func in repo_analysis.get("functions", [])[:200]:
            docs.append({"id": func["name"], "text": f"Function: {func['name']} in {func.get('path', '')}", "metadata": {"type": "function", "repo": repo_name, "path": func.get("path", "")}})
        for api in repo_analysis.get("api_endpoints", [])[:200]:
            docs.append({"id": api["handler"], "text": f"API: {api['method']} {api['path']} in {api.get('source_file', '')}", "metadata": {"type": "api", "repo": repo_name, "path": api.get("source_file", "")}})

        self.docs = docs
        return {"status": "indexed", "count": len(docs)}

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.docs:
            return []
        query_vector = np.array(self.embedding_service.embed(query), dtype=float)
        scored = []
        for item in self.docs:
            text_vector = np.array(self.embedding_service.embed(item["text"]), dtype=float)
            cosine = float(np.dot(query_vector, text_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(text_vector) + 1e-8))
            scored.append({"text": item["text"], "metadata": item["metadata"], "distance": 1.0 - cosine})
        scored.sort(key=lambda x: x["distance"])
        return scored[:limit]
