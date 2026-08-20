def test_low_battery_ingest_creates_alert_automatically(client, demo_node):
    node_id = demo_node["id"]
    resp = client.post("/telemetry", json={"node_id": node_id, "battery_percent": 10.0})
    assert resp.status_code == 200

    resp = client.get(f"/alerts?node_id={node_id}")
    assert resp.status_code == 200
    alerts = resp.json()
    assert any(a["type"] == "low_battery" and a["severity"] == "critical" for a in alerts)


def test_manual_alert_create_and_acknowledge(client, demo_node):
    node_id = demo_node["id"]
    resp = client.post("/alerts", json={
        "node_id": node_id, "type": "sos", "severity": "critical", "message": "Test SOS"
    })
    assert resp.status_code == 200
    alert = resp.json()
    assert alert["acknowledged_at"] is None

    resp = client.post(f"/alerts/{alert['id']}/acknowledge", json={"acknowledged_by": "test-admin"})
    assert resp.status_code == 200
    assert resp.json()["acknowledged_at"] is not None


def test_acknowledge_nonexistent_alert_404(client):
    resp = client.post("/alerts/does-not-exist/acknowledge", json={})
    assert resp.status_code == 404


def test_filter_unacknowledged_alerts(client, demo_node):
    node_id = demo_node["id"]
    client.post("/alerts", json={"node_id": node_id, "type": "test", "severity": "info", "message": "a"})
    resp = client.get(f"/alerts?node_id={node_id}&acknowledged=false")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert all(a["acknowledged_at"] is None for a in resp.json())
