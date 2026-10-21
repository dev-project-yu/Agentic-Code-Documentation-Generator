from pathlib import Path

from app.core.knowledge_graph import KnowledgeGraphService
from app.core.semantic_layer import SemanticLayer
from app.services.agent_workflow import AgentWorkflow
from app.services.repo_analyzer import RepoAnalyzerService


def test_analyze_repository_detects_python_endpoints(tmp_path: Path):
    repo_dir = tmp_path / "demo_repo"
    repo_dir.mkdir()

    (repo_dir / "README.md").write_text("# Demo Repo\nA sample repository for tests.\n", encoding="utf-8")
    (repo_dir / "requirements.txt").write_text("fastapi==0.111.0\n", encoding="utf-8")

    app_dir = repo_dir / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("", encoding="utf-8")
    (app_dir / "main.py").write_text(
        "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n\nclass Service:\n    def run(self):\n        return 'done'\n",
        encoding="utf-8",
    )

    analysis = RepoAnalyzerService().analyze_repository(
        repo_dir,
        {
            "full_name": "demo/demo_repo",
            "default_branch": "main",
            "description": "Demo project",
            "stars": 2,
            "forks": 1,
        },
    )

    assert analysis["repo"]["full_name"] == "demo/demo_repo"
    assert any(item["name"] == "Service" for item in analysis["classes"])
    assert any(item["name"] == "health" for item in analysis["functions"])
    assert any(item["source_file"] == "app/main.py" and item["path"] == "/health" and item["method"] == "GET" for item in analysis["api_endpoints"])
    assert any(item["name"] == "fastapi" for item in analysis["dependencies"])


def test_document_uses_repo_facts_not_agent_config(tmp_path: Path):
    repo_dir = tmp_path / "demo_repo"
    repo_dir.mkdir()

    (repo_dir / "README.md").write_text("# Demo Repo\nFastAPI sample service.\n", encoding="utf-8")
    (repo_dir / "requirements.txt").write_text("fastapi==0.111.0\n", encoding="utf-8")
    (repo_dir / "app").mkdir()
    (repo_dir / "app" / "main.py").write_text(
        "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n",
        encoding="utf-8",
    )

    analysis = RepoAnalyzerService().analyze_repository(
        repo_dir,
        {
            "full_name": "demo/demo_repo",
            "default_branch": "main",
            "description": "Demo project",
            "stars": 2,
            "forks": 1,
        },
    )
    graph = KnowledgeGraphService(uri='', username='', password='')
    semantic_layer = SemanticLayer()
    semantic_layer.register({"entities": [], "relationships": []})
    workflow = AgentWorkflow(analysis, semantic_layer, None, graph)
    result = workflow.run()
    document = result.get("document", "")

    assert "demo/demo_repo" in document
    assert "GEMINI_API_KEY" not in document
    assert "Node 20" not in document
    assert "RepoDoc Agent" not in document
    assert "仓库中未发现" in document or "FastAPI" in document
