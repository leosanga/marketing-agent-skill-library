from app.data_gen import generate_dataset

def test_generate_dataset_is_deterministic_for_same_seed():
    first = generate_dataset(seed=42)
    second = generate_dataset(seed=42)
    assert first == second

def test_generate_dataset_has_expected_shape():
    dataset = generate_dataset(seed=1, num_campaigns=5, num_leads=10)
    assert len(dataset["campaigns"]) == 5
    assert len(dataset["leads"]) == 10
    assert len(dataset["email_metrics"]) == 5

    campaign = dataset["campaigns"][0]
    for field in ["id", "name", "channel", "start_date", "end_date", "budget", "impressions", "clicks", "conversions"]:
        assert field in campaign

    lead = dataset["leads"][0]
    for field in ["id", "name", "company", "title", "company_size", "source_campaign_id", "created_at", "score", "status"]:
        assert field in lead
