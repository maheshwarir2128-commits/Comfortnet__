def test_health_endpoint_labels_as_rule_based_not_ai(client, demo_node):
    node_id = demo_node["id"]
    client.post("/telemetry", json={"node_id": node_id, "battery_percent": 90, "network_status": "online"})

    resp = client.get(f"/analytics/node/{node_id}/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ai_predictive_maintenance_implemented"] is False
    assert body["method"] == "rule_based_explainable_analytics"
    assert body["status"] == "healthy"


def test_health_score_drops_on_low_battery(client, demo_node):
    node_id = demo_node["id"]
    client.post("/telemetry", json={"node_id": node_id, "battery_percent": 8, "network_status": "offline"})

    resp = client.get(f"/analytics/node/{node_id}/health")
    body = resp.json()
    assert body["status"] == "critical"
    assert any("Battery" in f for f in body["contributing_factors"])
    assert any("Network" in f for f in body["contributing_factors"])


def test_anomaly_detection_flags_battery_drop(client, demo_node):
    node_id = demo_node["id"]
    client.post("/telemetry", json={"node_id": node_id, "battery_percent": 90})
    client.post("/telemetry", json={"node_id": node_id, "battery_percent": 60})

    resp = client.get(f"/analytics/node/{node_id}/anomalies")
    assert resp.status_code == 200
    anomalies = resp.json()["anomalies"]
    assert any("battery drain" in a.lower() for a in anomalies)


def test_campus_summary(client, demo_campus, demo_node):
    client.post("/telemetry", json={"node_id": demo_node["id"], "battery_percent": 70})
    resp = client.get(f"/analytics/campus/{demo_campus['id']}/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["node_count"] == 1
    assert body["nodes_reporting"] == 1
    assert body["average_battery_percent"] == 70
