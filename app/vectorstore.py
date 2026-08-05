import chromadb
from chromadb.utils import embedding_functions


def _campaign_to_document(campaign: dict) -> str:
    return (
        f"Campaign {campaign['name']} ({campaign['id']}) ran on {campaign['channel']} "
        f"from {campaign['start_date']} to {campaign['end_date']}, budget ${campaign['budget']}, "
        f"{campaign['impressions']} impressions, {campaign['clicks']} clicks, "
        f"{campaign['conversions']} conversions."
    )


def _lead_to_document(lead: dict) -> str:
    return (
        f"Lead {lead['name']} is {lead['title']} at {lead['company']} "
        f"({lead['company_size']} employees), sourced from campaign {lead['source_campaign_id']}, "
        f"score {lead['score']}, status {lead['status']}."
    )


def build_vectorstore(dataset: dict, persist_path: str | None = None):
    client = (
        chromadb.PersistentClient(path=persist_path)
        if persist_path
        else chromadb.EphemeralClient()
    )
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(
        name="marketing_data", embedding_function=embedding_fn
    )

    documents, ids, metadatas = [], [], []
    for campaign in dataset["campaigns"]:
        documents.append(_campaign_to_document(campaign))
        ids.append(f"campaign::{campaign['id']}")
        metadatas.append({"type": "campaign", "record_id": campaign["id"]})
    for lead in dataset["leads"]:
        documents.append(_lead_to_document(lead))
        ids.append(f"lead::{lead['id']}")
        metadatas.append({"type": "lead", "record_id": lead["id"]})

    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    return collection


def query_vectorstore(collection, text: str, n_results: int = 3) -> list[str]:
    results = collection.query(query_texts=[text], n_results=n_results)
    return results["documents"][0]
