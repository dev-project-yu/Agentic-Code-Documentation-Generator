from __future__ import annotations

from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.services.gemini_service import GeminiService


class AgentState(TypedDict):
    repo_analysis: Dict[str, Any]
    semantic_summary: Dict[str, Any]
    rag_context: List[str]
    rag_evidence: List[Dict[str, Any]]
    graph_context: List[Dict[str, Any]]
    document: str
    validation: Dict[str, Any]
    gemini_status: Dict[str, Any]
    agent_status: Dict[str, Any]


class AgentWorkflow:
    def __init__(self, repo_analysis: Dict[str, Any], semantic_layer: Any, rag_service: Optional[Any], graph_service: Optional[Any] = None):
        self.repo_analysis = repo_analysis
        self.semantic_layer = semantic_layer
        self.rag_service = rag_service
        self.graph_service = graph_service
        self.gemini = GeminiService()

    def _repo_analysis_agent(self, state: AgentState) -> AgentState:
        repo = state["repo_analysis"]["repo"]
        summary = {
            "project": repo.get("full_name", "Unknown"),
            "language": repo.get("language", "Unknown"),
            "description": repo.get("description", ""),
            "tech_stack": state["repo_analysis"].get("tech_stack", []),
        }
        state["repo_analysis"]["summary"] = summary
        state["agent_status"] = {"status": "repo_analysis", "steps": ["repo_analysis", "architecture", "documentation", "validation"]}
        return state

    def _architecture_agent(self, state: AgentState) -> AgentState:
        state["semantic_summary"] = self.semantic_layer.summary()
        state["repo_analysis"]["architecture"] = {
            "module_count": len(state["repo_analysis"].get("modules", [])),
            "api_count": len(state["repo_analysis"].get("api_endpoints", [])),
            "dependency_count": len(state["repo_analysis"].get("dependencies", [])),
        }
        if self.graph_service is not None:
            state["graph_context"] = self.graph_service.query(state["repo_analysis"]["repo"]["full_name"])
        else:
            state["graph_context"] = []
        state["agent_status"] = {"status": "architecture", "steps": ["repo_analysis", "architecture", "documentation", "validation"]}
        return state

    def _documentation_agent(self, state: AgentState) -> AgentState:
        repo_name = state["repo_analysis"]["repo"]["full_name"]
        query = f"{repo_name} README installation usage API and source references"
        rag_hits = self.rag_service.search(query, limit=5) if self.rag_service else []
        state["rag_context"] = [hit.get("text", "") for hit in rag_hits]
        state["rag_evidence"] = rag_hits
        state["gemini_status"] = {
            "configured": self.gemini.enabled,
            "model": self.gemini.model_name,
            "source": ".env",
            "status": "ready" if self.gemini.enabled else "missing_gemini_api_key",
        }

        if self.gemini.enabled:
            prompt = self._build_prompt(state)
            try:
                generated = self.gemini.generate(prompt)
                state["document"] = generated
            except Exception:
                state["document"] = self._fallback_document(state)
        else:
            state["document"] = self._fallback_document(state)
        state["agent_status"] = {"status": "documentation", "steps": ["repo_analysis", "architecture", "documentation", "validation"]}
        return state

    def _validation_agent(self, state: AgentState) -> AgentState:
        sources = [
            item.get("source_file") for item in state["repo_analysis"].get("api_endpoints", []) if item.get("source_file")
        ] + [module.get("path") for module in state["repo_analysis"].get("modules", []) if module.get("path")]
        validation = {
            "source_count": len(set(sources)),
            "references_found": bool(sources),
            "warning": "Gemini 未配置：请在项目根目录 .env 中填写 GEMINI_API_KEY。" if not self.gemini.enabled else "已结合源码、RAG 检索与图谱信息生成文档。",
            "graph_context_size": len(state.get("graph_context", [])),
            "rag_context_size": len(state.get("rag_evidence", [])),
        }
        state["validation"] = validation
        state["agent_status"] = {"status": "completed", "steps": ["repo_analysis", "architecture", "documentation", "validation"]}
        return state

    def _build_prompt(self, state: AgentState) -> str:
        repo = state["repo_analysis"]["repo"]
        repo_facts = state["repo_analysis"]
        context = "\n\n".join(state["rag_context"][:8]) or "仓库中未发现额外检索上下文。"
        graph_context = state.get("graph_context", [])
        return (
            "你是技术文档生成 Agent。必须仅基于目标仓库的真实 README、源码、配置和依赖信息生成文档，不得写入 RepoDoc Agent 自身配置。\n"
            "规则：\n"
            "1. 认识‘被分析仓库’和‘RepoDoc Agent’是两个不同系统，不得出现 Python 3.11、Node 20、GEMINI_API_KEY、FastAPI、Vite、Neo4j 等与目标仓库无关的系统设定。\n"
            "2. 如果仓库中没有安装步骤、部署配置或 API 信息，就明确写成‘仓库中未发现相关信息’。\n"
            "3. API Reference 必须基于源码中的路由声明，且尽量附带 source_file。\n"
            f"项目：{repo.get('full_name')}\n"
            f"描述：{repo.get('description') or '仓库中未发现描述信息。'}\n"
            f"README 摘要：{repo_facts.get('readme_summary', '仓库中未发现 README 内容。')}\n"
            f"技术栈：{repo_facts.get('tech_stack', [])}\n"
            f"依赖：{repo_facts.get('dependencies', [])[:10]}\n"
            f"模块：{repo_facts.get('modules', [])[:10]}\n"
            f"API：{repo_facts.get('api_endpoints', [])[:10]}\n"
            f"知识图谱上下文：{graph_context[:10]}\n\n"
            f"RAG 检索证据：\n{context}\n\n"
            "请输出中文 Markdown 文档，并在无法确认处写明‘仓库中未发现相关信息’。"
        )

    def _fallback_document(self, state: AgentState) -> str:
        repo = state["repo_analysis"]["repo"]
        tech_stack = state["repo_analysis"].get("tech_stack", []) or ["未知"]
        api_endpoints = state["repo_analysis"].get("api_endpoints", [])
        dependencies = state["repo_analysis"].get("dependencies", [])
        files = state["repo_analysis"].get("files", [])
        deployment_files = [
            item.get("path") for item in files if item.get("path", "").lower() in {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml"}
        ]

        install_block = (
            "\n".join(f"- {dep.get('name')} {dep.get('version') or ''}".strip() for dep in dependencies[:10])
            if dependencies
            else "- 仓库中未发现安装依赖配置。"
        )
        api_block = (
            "\n".join(f"- {api.get('method')} {api.get('path')} -> {api.get('source_file')}" for api in api_endpoints[:10])
            if api_endpoints
            else "- 仓库中未发现可验证的 API 路由。"
        )
        deploy_block = "- 发现部署文件: " + ", ".join(deployment_files) if deployment_files else "- 仓库中未发现部署配置。"
        readme_summary = state["repo_analysis"].get("readme_summary", "仓库中未发现 README 内容。")

        return (
            f"# {repo.get('full_name', 'Repository')}\n\n"
            "## Overview\n"
            f"- 项目：{repo.get('full_name', 'Unknown')}\n"
            f"- 描述：{repo.get('description') or '仓库中未发现描述信息。'}\n"
            f"- README 摘要：{readme_summary}\n"
            f"- 识别技术栈：{', '.join(tech_stack)}\n\n"
            "## Installation\n"
            f"{install_block}\n\n"
            "> 说明：此部分仅基于仓库中的依赖文件/README，未发现确切安装命令时请写为“仓库中未发现相关信息”。\n\n"
            "## Deployment\n"
            f"{deploy_block}\n\n"
            "## Architecture\n"
            f"- 模块数：{len(state['repo_analysis'].get('modules', []))}\n"
            f"- API 数：{len(api_endpoints)}\n"
            f"- 依赖数：{len(dependencies)}\n\n"
            "## API Reference\n"
            f"{api_block}\n\n"
            "## Evidence\n"
            "- RAG 检索与图谱查询已在 Agent 中执行。\n"
            "- Gemini 未配置时，只输出基于仓库事实的文档，不编造系统配置。\n"
            "- 若仓库中没有相关信息，则明确标注“仓库中未发现相关信息”。\n"
        )

    def run(self) -> Dict[str, Any]:
        workflow = StateGraph(AgentState)
        workflow.add_node("analyze_repo", self._repo_analysis_agent)
        workflow.add_node("build_architecture", self._architecture_agent)
        workflow.add_node("build_documentation", self._documentation_agent)
        workflow.add_node("validate_document", self._validation_agent)
        workflow.set_entry_point("analyze_repo")
        workflow.add_edge("analyze_repo", "build_architecture")
        workflow.add_edge("build_architecture", "build_documentation")
        workflow.add_edge("build_documentation", "validate_document")
        workflow.add_edge("validate_document", END)
        app = workflow.compile()
        state = {
            "repo_analysis": self.repo_analysis,
            "semantic_summary": {},
            "rag_context": [],
            "rag_evidence": [],
            "graph_context": [],
            "document": "",
            "validation": {},
            "gemini_status": {
                "configured": self.gemini.enabled,
                "model": self.gemini.model_name,
                "source": ".env",
                "status": "ready" if self.gemini.enabled else "missing_gemini_api_key",
            },
            "agent_status": {"status": "running", "steps": ["repo_analysis", "architecture", "documentation", "validation"]},
        }
        result = app.invoke(state)
        result["gemini_status"] = state["gemini_status"]
        result["agent_status"] = {"status": "completed", "steps": ["repo_analysis", "architecture", "documentation", "validation"]}
        return result
