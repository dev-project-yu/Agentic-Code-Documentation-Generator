import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings:
    APP_NAME = "RepoDoc Agent"
    APP_VERSION = "0.1.0"
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    TEMP_ROOT = PROJECT_ROOT / ".tmp"
    DATA_ROOT = PROJECT_ROOT / "state"
    WORKSPACE_ROOT = PROJECT_ROOT

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "repo-doc-agent")

    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
