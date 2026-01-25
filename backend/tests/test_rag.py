from pathlib import Path
from tempfile import TemporaryDirectory

from src.llm.config import RAGSettings
from src.llm.store import RAGStore


def test_rag_index_and_query():
    with TemporaryDirectory() as tmp:
        settings = RAGSettings(data_dir=Path(tmp), top_k=2, min_score=0.0)
        store = RAGStore(settings)

        store.create_index("fleetflow")
        store.ingest(
            "fleetflow",
            [
                {"id": "doc1", "text": "Route optimization with OR-Tools for delivery fleets."},
                {"id": "doc2", "text": "Kafka streams GPS events for real-time tracking."},
            ],
        )

        hits = store.query("fleetflow", "route optimization", top_k=1)
        assert hits
        assert hits[0].doc_id == "doc1"