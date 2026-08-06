import sys

from app.data_gen import generate_dataset
from app.vectorstore import build_vectorstore, query_vectorstore

def test_query_vectorstore_returns_relevant_documents():
    dataset = generate_dataset(seed=7, num_campaigns=5, num_leads=10)
    collection = build_vectorstore(dataset)  # in-memory, no persist_path
    results = query_vectorstore(collection, "leads from a large company", n_results=3)
    assert len(results) == 3
    assert all(isinstance(doc, str) for doc in results)


def test_vectorstore_never_imports_onnxruntime():
    """Regression: chromadb's DefaultEmbeddingFunction lazily loads onnxruntime +
    MiniLM on first embed, which OOM-kills the 512MB Render instance."""
    dataset = generate_dataset(seed=3, num_campaigns=3, num_leads=5)
    collection = build_vectorstore(dataset)
    query_vectorstore(collection, "top performing email campaign", n_results=2)
    assert "onnxruntime" not in sys.modules


def test_query_retrieves_matching_record_type():
    dataset = {
        "campaigns": [
            {
                "id": "camp_001", "name": "Spring Email Push", "channel": "email",
                "start_date": "2026-01-01", "end_date": "2026-02-01", "budget": 5000,
                "impressions": 100000, "clicks": 2000, "conversions": 120,
            }
        ],
        "leads": [
            {
                "id": "lead_001", "name": "Lead 1", "company": "Company 42",
                "title": "VP Marketing", "company_size": "1000+",
                "source_campaign_id": "camp_001", "score": 91, "status": "qualified",
            },
            {
                "id": "lead_002", "name": "Lead 2", "company": "Company 7",
                "title": "CMO", "company_size": "11-50",
                "source_campaign_id": "camp_001", "score": 12, "status": "new",
            },
        ],
    }
    collection = build_vectorstore(dataset)

    assert query_vectorstore(collection, "which leads have a high score", n_results=1)[0].startswith("Lead ")
    assert query_vectorstore(
        collection, "campaign budget impressions clicks conversions", n_results=1
    )[0].startswith("Campaign ")
