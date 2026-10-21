from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import urlparse

import requests


class GitHubRepositoryService:
    @staticmethod
    def parse_github_url(url: str) -> Tuple[str, str, str]:
        parsed = urlparse(url.strip())
        if not parsed.netloc.endswith("github.com"):
            raise ValueError("仅支持 GitHub Repository URL")
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            raise ValueError("GitHub URL 应为 owner/repo 形式")
        owner, repo = parts[0], parts[1]
        repo = repo.replace(".git", "")
        return owner, repo, f"https://github.com/{owner}/{repo}"

    def fetch_repository_metadata(self, url: str) -> Dict:
        owner, repo, repo_url = self.parse_github_url(url)
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(api_url, timeout=20)
        if response.status_code != 200:
            raise ValueError(f"无法访问 GitHub 仓库: {response.status_code}")
        data = response.json()
        return {
            "full_name": data.get("full_name"),
            "default_branch": data.get("default_branch", "main"),
            "description": data.get("description", ""),
            "html_url": data.get("html_url"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "language": data.get("language", "Unknown"),
            "private": data.get("private", False),
            "default_branch": data.get("default_branch", "main"),
        }

    def clone_repository(self, url: str, target_root: Path) -> Path:
        owner, repo, repo_url = self.parse_github_url(url)
        destination = target_root / repo
        target_root.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            return destination

        command = ["git", "clone", "--depth", "1", repo_url, str(destination)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        return destination
