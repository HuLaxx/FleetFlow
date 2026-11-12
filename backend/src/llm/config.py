import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RAGSettings:
    data_dir: Path
    top_k: int = 4
    min_score: float = 0.2
    max_context_chars: int = 4000
    llm_api_base: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "RAGSettings":
        data_dir = Path(os.getenv("RAG_DATA_DIR", ".rag"))
        return cls(
            data_dir=data_dir,
            top_k=int(os.getenv("RAG_TOP_K", "4")),
            min_score=float(os.getenv("RAG_MIN_SCORE", "0.2")),
            max_context_chars=int(os.getenv("RAG_MAX_CONTEXT_CHARS", "4000")),
            llm_api_base=os.getenv("LLM_API_BASE"),
            llm_api_key=os.getenv("LLM_API_KEY"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        )
