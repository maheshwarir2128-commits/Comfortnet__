"""
Shared pytest fixtures. Uses an isolated in-memory SQLite database per test
session so tests never touch comfortnet_dev.db (the demo database).

NOT EXECUTED IN THIS ENVIRONMENT — this sandbox has no network access to
pip install fastapi/sqlalchemy/pytest. Files are syntax-checked (py_compile)
but not run here. Run locally with: pytest
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=test_engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def demo_campus(client):
    resp = client.post("/campuses", json={"name": "Test Campus", "contact_org": "Test Org"})
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture()
def demo_node(client, demo_campus):
    resp = client.post("/nodes", json={
        "id": "tree-test-01",
        "campus_id": demo_campus["id"],
        "tree_reference": "Test Tree 01",
    })
    assert resp.status_code == 200
    return resp.json()
