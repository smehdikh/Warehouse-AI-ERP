"""Tests for warehouse endpoints."""

from fastapi.testclient import TestClient


def test_list_warehouses_empty(client: TestClient) -> None:
    """List returns empty array when no warehouses exist."""
    response = client.get("/api/v1/warehouses/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_warehouse(client: TestClient) -> None:
    """Create a warehouse and retrieve it by ID."""
    payload = {"name": "Main Warehouse", "location": "New York", "capacity": 5000.0}
    create_resp = client.post("/api/v1/warehouses/", json=payload)
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["name"] == "Main Warehouse"
    assert data["location"] == "New York"
    wid = data["id"]

    get_resp = client.get(f"/api/v1/warehouses/{wid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == wid


def test_get_warehouse_not_found(client: TestClient) -> None:
    """Returns 404 for a non-existent warehouse."""
    response = client.get("/api/v1/warehouses/nonexistent-id")
    assert response.status_code == 404
