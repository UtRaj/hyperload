from fastapi.testclient import TestClient
from app.models import Product

def test_create_product(client: TestClient):
    response = client.post(
        "/api/products",
        json={"sku": "TEST-001", "name": "Test Product", "description": "A test product"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sku"] == "TEST-001"
    assert data["name"] == "Test Product"
    assert data["id"] is not None

def test_create_duplicate_product(client: TestClient):
    # Create first product
    client.post(
        "/api/products",
        json={"sku": "TEST-001", "name": "Test Product"}
    )
    
    # Try to create same SKU
    response = client.post(
        "/api/products",
        json={"sku": "TEST-001", "name": "Duplicate Product"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_get_products(client: TestClient):
    # Create a few products
    client.post("/api/products", json={"sku": "P1", "name": "Product 1"})
    client.post("/api/products", json={"sku": "P2", "name": "Product 2"})
    
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2

def test_get_product_by_id(client: TestClient):
    create_res = client.post("/api/products", json={"sku": "P1", "name": "Product 1"})
    product_id = create_res.json()["id"]
    
    response = client.get(f"/api/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["sku"] == "P1"

def test_update_product(client: TestClient):
    create_res = client.post("/api/products", json={"sku": "P1", "name": "Product 1"})
    product_id = create_res.json()["id"]
    
    response = client.put(
        f"/api/products/{product_id}",
        json={"name": "Updated Name", "active": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["active"] is False

def test_delete_product(client: TestClient):
    create_res = client.post("/api/products", json={"sku": "P1", "name": "Product 1"})
    product_id = create_res.json()["id"]
    
    response = client.delete(f"/api/products/{product_id}")
    assert response.status_code == 200
    
    # Verify deleted
    get_res = client.get(f"/api/products/{product_id}")
    assert get_res.status_code == 404

def test_bulk_delete(client: TestClient):
    client.post("/api/products", json={"sku": "P1", "name": "Product 1"})
    client.post("/api/products", json={"sku": "P2", "name": "Product 2"})
    
    response = client.delete("/api/products")
    assert response.status_code == 200
    assert response.json()["count"] == 2
    
    # Verify empty
    list_res = client.get("/api/products")
    assert list_res.json()["total"] == 0
