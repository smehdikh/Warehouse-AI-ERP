"""Tests for product endpoints."""

from fastapi.testclient import TestClient


def test_list_products_empty(client: TestClient) -> None:
    """List returns empty array when no products exist."""
    response = client.get("/api/v1/products/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_product(client: TestClient) -> None:
    """Create a product and retrieve it by ID."""
    payload = {"sku": "SKU-001", "name": "Widget A", "category": "Electronics", "unit_price": 9.99}
    create_resp = client.post("/api/v1/products/", json=payload)
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["sku"] == "SKU-001"
    pid = data["id"]

    get_resp = client.get(f"/api/v1/products/{pid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == pid


def test_get_product_not_found(client: TestClient) -> None:
    """Returns 404 for a non-existent product."""
    response = client.get("/api/v1/products/nonexistent-id")
    assert response.status_code == 404
