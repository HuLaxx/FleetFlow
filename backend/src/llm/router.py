from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .client import LLMClient
from .config import RAGSettings
from .store import RAGStore

router = APIRouter()


class IndexRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)


class DocumentInput(BaseModel):
    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    metadata: dict[str, Any] | None = None


class IngestRequest(BaseModel):
    index: str
    documents: list[DocumentInput]


class QueryRequest(BaseModel):
    index: str
    query: str
    top_k: int | None = None


class Citation(BaseModel):
    doc_id: str
    score: float
    snippet: str
    metadata: dict[str, Any]


class QueryResponse(BaseModel):
    answer: str
    llm_used: bool
    citations: list[Citation]


@router.get("/api/v1/rag/indexes")
async def list_indexes() -> dict[str, list[str]]:
    store = RAGStore()
    return {"indexes": store.list_indexes()}


@router.post("/api/v1/rag/indexes")
async def create_index(request: IndexRequest) -> dict[str, str]:
    store = RAGStore()
    try:
        store.create_index(request.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "created", "index": request.name}


@router.post("/api/v1/rag/ingest")
async def ingest_documents(request: IngestRequest) -> dict[str, Any]:
    store = RAGStore()
    try:
        count = store.ingest(request.index, [doc.model_dump() for doc in request.documents])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ingested", "index": request.index, "documents": count}


@router.post("/api/v1/rag/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest) -> QueryResponse:
    settings = RAGSettings.from_env()
    store = RAGStore(settings)
    try:
        hits = store.query(request.index, request.query, request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    llm = LLMClient(settings)
    answer, llm_used = await llm.generate(request.query, hits)

    citations = [
        Citation(
            doc_id=hit.doc_id,
            score=hit.score,
            snippet=hit.text[:240].strip(),
            metadata=hit.metadata,
        )
        for hit in hits
    ]

    return QueryResponse(answer=answer, llm_used=llm_used, citations=citations)
