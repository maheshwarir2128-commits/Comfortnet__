def test_ingest_requires_existing_node(client):
    resp = client.post("/telemetry", json={"node_id": "no-such-node", "battery_percent": 50})
    assert resp.status_code == 404


def test_ingest_and_get_latest(client, demo_node):
    node_id = demo_node["id"]
    resp = client.post("/telemetry", json={
        "node_id": node_id,
        "battery_percent": 82.0,
        "solar_power": 45.0,
        "temperature": 29.5,
        "network_status": "online",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "simulated"
    assert body["node_id"] == node_id

    resp = client.get(f"/telemetry/{node_id}/latest")
    assert resp.status_code == 200
    assert resp.json()["battery_percent"] == 82.0


def test_latest_with_no_telemetry_returns_404(client, demo_node):
    resp = client.get(f"/telemetry/{demo_node['id']}/latest")
    assert resp.status_code == 404


def test_historical_telemetry_ordering_and_limit(client, demo_node):
    node_id = demo_node["id"]
    for i in range(5):
        r = client.post("/telemetry", json={"node_id": node_id, "battery_percent": 50 + i})
        assert r.status_code == 200

    resp = client.get(f"/telemetry/{node_id}?limit=3")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 3
    # most recent first
    assert rows[0]["battery_percent"] == 54


def test_invalid_telemetry_payload_rejected(client, demo_node):
    # battery_percent must be a number, not a string — expect 422 validation error
    resp = client.post("/telemetry", json={"node_id": demo_node["id"], "battery_percent": "not-a-number"})
    assert resp.status_code == 422


def test_ingest_updates_node_last_seen(client, demo_node):
    node_id = demo_node["id"]
    client.post("/telemetry", json={"node_id": node_id, "battery_percent": 60})
    resp = client.get(f"/nodes/{node_id}")
    assert resp.json()["last_seen_at"] is not None
