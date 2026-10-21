from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.core.knowledge_graph import KnowledgeGraphService
from app.core.ontology import OntologyBuilder
from app.core.semantic_layer import SemanticLayer
from app.services.agent_workflow import AgentWorkflow
from app.services.github_service import GitHubRepositoryService
from app.services.rag_service import RAGService
from app.services.repo_analyzer import RepoAnalyzerService

app = FastAPI(title="RepoDoc Agent", version=settings.APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TASKS: Dict[str, Dict[str, Any]] = {}


class AnalyzeRequest(BaseModel):
    github_url: str


class AnalyzeResponse(BaseModel):
    task_id: str
    status: str
    data: Dict[str, Any]


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "neo4j_configured": bool(settings.NEO4J_URI and settings.NEO4J_USERNAME and settings.NEO4J_PASSWORD),
    }


@app.get("/api/tasks")
def list_tasks() -> Dict[str, Any]:
    return {"tasks": TASKS}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> Dict[str, Any]:
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.post("/api/analyze")
def analyze_repository(payload: AnalyzeRequest) -> AnalyzeResponse:
    github_url = payload.github_url.strip()
    if not github_url:
        raise HTTPException(status_code=400, detail="GitHub URL 不能为空")

    task_id = str(uuid.uuid4())
    try:
        with_task = {
            "task_id": task_id,
            "status": "running",
            "github_url": github_url,
        }
        TASKS[task_id] = with_task

        git_service = GitHubRepositoryService()
        repo_meta = git_service.fetch_repository_metadata(github_url)
        target_root = settings.TEMP_ROOT / "repos"
        target_root.mkdir(parents=True, exist_ok=True)
        repo_path = git_service.clone_repository(github_url, target_root)

        analyzer = RepoAnalyzerService()
        analysis = analyzer.analyze_repository(repo_path, repo_meta)

        ontology = OntologyBuilder.from_analysis(analysis)
        semantic_layer = SemanticLayer()
        semantic_layer.register(ontology)

        graph_service = KnowledgeGraphService(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        graph_status = graph_service.write_repository_graph(analysis, ontology)

        rag_service = RAGService(settings.DATA_ROOT / "chroma")
        rag_index = rag_service.index_repository(analysis)

        workflow = AgentWorkflow(analysis, semantic_layer, rag_service, graph_service)
        workflow_result = workflow.run()

        document = workflow_result.get("document", "")
        validation = workflow_result.get("validation", {})
        response_data = {
            "repo": analysis["repo"],
            "tech_stack": analysis["tech_stack"],
            "directories": analysis["directories"],
            "modules": analysis["modules"],
            "classes": analysis["classes"],
            "functions": analysis["functions"],
            "api_endpoints": analysis["api_endpoints"],
            "dependencies": analysis["dependencies"],
            "knowledge_graph": graph_status,
            "graph_context": workflow_result.get("graph_context", []),
            "semantic_layer": semantic_layer.summary(),
            "rag": rag_index,
            "rag_evidence": workflow_result.get("rag_evidence", []),
            "document": document,
            "validation": validation,
            "gemini_status": workflow_result.get("gemini_status", {"configured": bool(settings.GEMINI_API_KEY), "status": "missing_gemini_api_key"}),
            "agent_status": workflow_result.get("agent_status", {"status": "completed", "steps": []}),
            "readme_summary": analysis.get("readme_summary", ""),
            "commit_sha": analysis.get("commit_sha", "unknown"),
        }
        TASKS[task_id] = {
            "task_id": task_id,
            "status": "completed",
            "github_url": github_url,
            "data": response_data,
        }
        return AnalyzeResponse(task_id=task_id, status="completed", data=response_data)
    except Exception as exc:  # pragma: no cover
        TASKS[task_id] = {
            "task_id": task_id,
            "status": "failed",
            "github_url": github_url,
            "error": str(exc),
        }
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "RepoDoc Agent backend is running"}
