from app.data_gen import generate_dataset
from app.vectorstore import build_vectorstore, query_vectorstore

def test_query_vectorstore_returns_relevant_documents():
    dataset = generate_dataset(seed=7, num_campaigns=5, num_leads=10)
    collection = build_vectorstore(dataset)  # in-memory, no persist_path
    results = query_vectorstore(collection, "leads from a large company", n_results=3)
    assert len(results) == 3
    assert all(isinstance(doc, str) for doc in results)
