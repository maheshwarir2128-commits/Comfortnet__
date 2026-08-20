def test_create_and_list_campus(client):
    resp = client.post("/campuses", json={"name": "Test Campus"})
    assert resp.status_code == 200
    campus = resp.json()
    assert campus["name"] == "Test Campus"

    resp = client.get("/campuses")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_node_requires_valid_campus(client):
    resp = client.post("/nodes", json={
        "id": "tree-x",
        "campus_id": "does-not-exist",
        "tree_reference": "Tree X",
    })
    assert resp.status_code == 404


def test_create_and_get_node(client, demo_node):
    resp = client.get(f"/nodes/{demo_node['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == demo_node["id"]
    assert body["install_status"] == "proposed"
    assert body["latest_telemetry"] is None


def test_duplicate_node_id_rejected(client, demo_campus):
    payload = {"id": "dup-node", "campus_id": demo_campus["id"], "tree_reference": "Dup"}
    r1 = client.post("/nodes", json=payload)
    assert r1.status_code == 200
    r2 = client.post("/nodes", json=payload)
    assert r2.status_code == 409


def test_list_nodes_filtered_by_campus(client, demo_campus, demo_node):
    resp = client.get(f"/nodes?campus_id={demo_campus['id']}")
    assert resp.status_code == 200
    ids = [n["id"] for n in resp.json()]
    assert demo_node["id"] in ids
