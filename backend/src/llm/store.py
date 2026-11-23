import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import RAGSettings

INDEX_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{2,64}$")


@dataclass
class StoredDocument:
    doc_id: str
    text: str
    metadata: dict[str, Any]
    created_at: float
    updated_at: float


@dataclass
class SearchHit:
    doc_id: str
    score: float
    text: str
    metadata: dict[str, Any]


class RAGStore:
    def __init__(self, settings: RAGSettings | None = None) -> None:
        self.settings = settings or RAGSettings.from_env()
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)

    def list_indexes(self) -> list[str]:
        return sorted([p.name for p in self.settings.data_dir.iterdir() if p.is_dir()])

    def create_index(self, name: str) -> Path:
        self._validate_index_name(name)
        index_dir = self._index_dir(name)
        index_dir.mkdir(parents=True, exist_ok=True)
        if not (index_dir / "documents.json").exists():
            self._save_documents(index_dir, [])
        return index_dir

    def ingest(self, name: str, documents: list[dict[str, Any]]) -> int:
        self._validate_index_name(name)
        index_dir = self.create_index(name)
        existing = self._load_documents(index_dir)
        existing_by_id = {doc.doc_id: doc for doc in existing}
        now = time.time()

        for doc in documents:
            doc_id = str(doc.get("id") or "").strip()
            text = str(doc.get("text") or "").strip()
            if not doc_id or not text:
                continue

            metadata = doc.get("metadata") or {}
            if doc_id in existing_by_id:
                current = existing_by_id[doc_id]
                current.text = text
                current.metadata = metadata
                current.updated_at = now
            else:
                existing_by_id[doc_id] = StoredDocument(
                    doc_id=doc_id,
                    text=text,
                    metadata=metadata,
                    created_at=now,
                    updated_at=now,
                )

        updated_docs = list(existing_by_id.values())
        self._save_documents(index_dir, updated_docs)
        self._rebuild_index(index_dir, updated_docs)
        return len(documents)

    def query(self, name: str, query: str, top_k: int | None = None) -> list[SearchHit]:
        self._validate_index_name(name)
        index_dir = self._index_dir(name)
        docs = self._load_documents(index_dir)
        if not docs:
            return []

        vectorizer, matrix = self._load_vector_index(index_dir)
        if vectorizer is None or matrix is None:
            return []

        query_vec = vectorizer.transform([query])
        scores = self._cosine_similarity(query_vec, matrix)

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        hits: list[SearchHit] = []
        limit = top_k or self.settings.top_k

        for idx, score in ranked[: limit * 2]:
            if score < self.settings.min_score:
                continue
            doc = docs[idx]
            hits.append(
                SearchHit(
                    doc_id=doc.doc_id,
                    score=float(score),
                    text=doc.text,
                    metadata=doc.metadata,
                )
            )
            if len(hits) >= limit:
                break

        return hits

    def _index_dir(self, name: str) -> Path:
        return self.settings.data_dir / name

    def _validate_index_name(self, name: str) -> None:
        if not INDEX_NAME_RE.match(name):
            raise ValueError("Index name must be 2-64 chars of letters, numbers, _ or -")

    def _load_documents(self, index_dir: Path) -> list[StoredDocument]:
        doc_path = index_dir / "documents.json"
        if not doc_path.exists():
            return []
        raw = json.loads(doc_path.read_text(encoding="utf-8"))
        docs = []
        for item in raw:
            docs.append(
                StoredDocument(
                    doc_id=item["doc_id"],
                    text=item["text"],
                    metadata=item.get("metadata") or {},
                    created_at=float(item.get("created_at", time.time())),
                    updated_at=float(item.get("updated_at", time.time())),
                )
            )
        return docs

    def _save_documents(self, index_dir: Path, docs: list[StoredDocument]) -> None:
        payload = [
            {
                "doc_id": doc.doc_id,
                "text": doc.text,
                "metadata": doc.metadata,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
            }
            for doc in docs
        ]
        (index_dir / "documents.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _rebuild_index(self, index_dir: Path, docs: list[StoredDocument]) -> None:
        from joblib import dump
        from sklearn.feature_extraction.text import TfidfVectorizer

        texts = [doc.text for doc in docs]
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=50000)
        matrix = vectorizer.fit_transform(texts)

        dump(vectorizer, index_dir / "vectorizer.joblib")
        dump(matrix, index_dir / "matrix.joblib")

    def _load_vector_index(self, index_dir: Path):
        from joblib import load

        vec_path = index_dir / "vectorizer.joblib"
        mat_path = index_dir / "matrix.joblib"
        if not vec_path.exists() or not mat_path.exists():
            return None, None
        return load(vec_path), load(mat_path)

    def _cosine_similarity(self, query_vec, matrix):
        from sklearn.metrics.pairwise import cosine_similarity

        return cosine_similarity(query_vec, matrix).flatten()
