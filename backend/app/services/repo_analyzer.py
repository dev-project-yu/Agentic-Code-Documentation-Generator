from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List


class RepoAnalyzerService:
    def __init__(self):
        self.supported_extensions = {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".txt"}

    def analyze_repository(self, repo_path: Path, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        files: List[Dict[str, Any]] = []
        modules: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []
        functions: List[Dict[str, Any]] = []
        api_endpoints: List[Dict[str, Any]] = []
        dependencies: List[Dict[str, Any]] = []
        readme_text = ""

        for path in sorted(repo_path.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(repo_path).as_posix()
            if rel.startswith(".git/"):
                continue
            ext = path.suffix.lower()
            if ext in {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".txt"}:
                files.append({
                    "path": rel,
                    "extension": ext,
                    "size": path.stat().st_size,
                })

            if path.suffix == ".py":
                module_name = rel.replace("/", ".").replace(".py", "")
                modules.append({
                    "name": module_name,
                    "path": rel,
                    "language": "python",
                })
                module_info = self._analyze_python_file(path, repo_path, module_name)
                classes.extend(module_info["classes"])
                functions.extend(module_info["functions"])
                api_endpoints.extend(module_info["api_endpoints"])

            if path.name.lower() in {"requirements.txt", "pyproject.toml", "poetry.lock", "package.json"}:
                dep_info = self._analyze_dependency_file(path)
                dependencies.extend(dep_info)

            if path.name.lower() in {"readme.md", "readme.rst", "readme.txt"}:
                try:
                    readme_text = path.read_text(encoding="utf-8")
                except Exception:
                    pass

        directories = sorted({str(Path(f["path"]).parent) for f in files if str(Path(f["path"]).parent) not in {"."}})
        language = repo_info.get("language") or self._infer_language(files)
        tech_stack = self._infer_tech_stack(files, dependencies)

        return {
            "repo": {
                "full_name": repo_info.get("full_name", repo_path.name),
                "default_branch": repo_info.get("default_branch", "main"),
                "description": repo_info.get("description", ""),
                "language": language,
                "stars": repo_info.get("stars", 0),
                "forks": repo_info.get("forks", 0),
            },
            "files": files,
            "directories": directories,
            "modules": modules,
            "classes": classes,
            "functions": functions,
            "api_endpoints": api_endpoints,
            "dependencies": dependencies,
            "tech_stack": tech_stack,
            "readme_summary": self._summarize_readme(readme_text),
            "commit_sha": self._detect_commit_sha(repo_path),
        }

    def _analyze_python_file(self, file_path: Path, repo_path: Path, module_name: str) -> Dict[str, Any]:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
        classes: List[Dict[str, Any]] = []
        functions: List[Dict[str, Any]] = []
        api_endpoints: List[Dict[str, Any]] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "path": file_path.relative_to(repo_path).as_posix(),
                    "module": module_name,
                    "line_number": node.lineno,
                    "module_id": f"repo:{module_name}",
                })
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "name": node.name,
                    "path": file_path.relative_to(repo_path).as_posix(),
                    "module": module_name,
                    "line_number": node.lineno,
                    "module_id": f"repo:{module_name}",
                })

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        func = decorator.func
                        if isinstance(func, ast.Attribute):
                            if func.attr in {"get", "post", "put", "delete", "patch"}:
                                path = None
                                if decorator.args:
                                    first = decorator.args[0]
                                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                                        path = first.value
                                api_endpoints.append({
                                    "method": func.attr.upper(),
                                    "path": path or "/",
                                    "handler": node.name,
                                    "source_file": file_path.relative_to(repo_path).as_posix(),
                                    "line_number": node.lineno,
                                    "module_id": f"repo:{module_name}",
                                })
                                api_endpoints[-1]["endpoint_path"] = path or "/"

        return {"classes": classes, "functions": functions, "api_endpoints": api_endpoints}

    def _analyze_dependency_file(self, file_path: Path) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return entries

        if file_path.name == "requirements.txt":
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "==" in line:
                    name, version = [part.strip() for part in line.split("==", 1)]
                elif ">=" in line:
                    name, version = [part.strip() for part in line.split(">=", 1)]
                elif "~=" in line:
                    name, version = [part.strip() for part in line.split("~=", 1)]
                else:
                    name, version = line, ""
                entries.append({"name": name, "version": version, "source": str(file_path)})

        if file_path.name == "package.json":
            try:
                data = json.loads(text)
                dependencies = data.get("dependencies", {})
                for name, version in dependencies.items():
                    entries.append({"name": name, "version": str(version), "source": str(file_path)})
            except Exception:
                pass

        return entries

    def _infer_language(self, files: List[Dict[str, Any]]) -> str:
        counts = {}
        for file in files:
            ext = file.get("extension", "")
            if ext == ".py":
                counts["Python"] = counts.get("Python", 0) + 1
            elif ext == ".js":
                counts["JavaScript"] = counts.get("JavaScript", 0) + 1
            elif ext == ".ts":
                counts["TypeScript"] = counts.get("TypeScript", 0) + 1
            elif ext == ".go":
                counts["Go"] = counts.get("Go", 0) + 1
        if not counts:
            return "Unknown"
        return max(counts.items(), key=lambda item: item[1])[0]

    def _infer_tech_stack(self, files: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[str]:
        stack = set()
        for file in files:
            ext = file.get("extension", "")
            if ext == ".py":
                stack.add("Python")
            if ext in {".js", ".ts"}:
                stack.add("JavaScript")
        for dep in dependencies:
            name = dep.get("name", "")
            if "fastapi" in name.lower():
                stack.add("FastAPI")
            if "flask" in name.lower():
                stack.add("Flask")
            if "react" in name.lower():
                stack.add("React")
            if "neo4j" in name.lower():
                stack.add("Neo4j")
            if "pydantic" in name.lower():
                stack.add("Pydantic")
        return sorted(stack)

    def _summarize_readme(self, readme_text: str) -> str:
        if not readme_text:
            return "未发现 README 内容，无法确认项目概述。"
        lines = [line.strip() for line in readme_text.splitlines() if line.strip()]
        summary = "\n".join(lines[:12])
        return summary[:1000]

    def _detect_commit_sha(self, repo_path: Path) -> str:
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return "unknown"
        try:
            import subprocess
            log = subprocess.check_output(["git", "-C", str(repo_path), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL)
            return log.strip()
        except Exception:
            return "unknown"
