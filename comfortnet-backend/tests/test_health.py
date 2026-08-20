def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert body["components"]["mqtt_broker"] == "not_implemented"
    assert body["components"]["predictive_maintenance_ai"] == "not_implemented"
