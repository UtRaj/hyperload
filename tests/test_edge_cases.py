import pytest
import csv
import os
from app.tasks import import_csv_task
from app.models import Product

def test_import_missing_columns(db, mock_redis, mocker):
    """Test CSV missing required columns"""
    mocker.patch("app.tasks.publish_progress")
    mocker.patch("app.tasks.SessionLocal", return_value=db)
    
    file_path = "temp_missing_cols.csv"
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "description"]) # Missing 'name'
        writer.writerow(["TEST-1", "Desc"])
    
    try:
        with pytest.raises(ValueError) as exc:
            import_csv_task.apply(args=[file_path], throw=True).result
        
        assert "must contain 'sku' and 'name'" in str(exc.value)
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def test_import_empty_file(db, mock_redis, mocker):
    """Test empty CSV file"""
    mocker.patch("app.tasks.publish_progress")
    mocker.patch("app.tasks.SessionLocal", return_value=db)
    
    file_path = "temp_empty.csv"
    with open(file_path, "w", newline="") as f:
        pass # Empty file
    
    try:
        # Should handle gracefully or raise specific error depending on implementation
        # DictReader on empty file returns empty iterator, but now we check fieldnames
        with pytest.raises(ValueError) as exc:
            import_csv_task.apply(args=[file_path], throw=True).result
        assert "must contain 'sku' and 'name'" in str(exc.value)
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def test_sql_injection_attempt(client, db):
    """Test that SQL injection in search is handled safely"""
    # Create a product
    client.post("/api/products", json={"sku": "SAFE", "name": "Safe Product"})
    
    # Attempt injection
    injection = "' OR '1'='1"
    response = client.get(f"/api/products?search={injection}")
    
    assert response.status_code == 200
    # Should not return all products if search logic is correct (it searches for literal string)
    # If it was injected, it might return everything or error
    # Our implementation uses parameterized queries via ORM, so it should be safe.
    # It will look for products with name/sku containing the literal injection string.
    data = response.json()
    assert data["total"] == 0 

def test_xss_protection(client):
    """Test that XSS scripts are stored but should be sanitized on frontend (API just stores)"""
    xss_payload = "<script>alert('XSS')</script>"
    
    response = client.post(
        "/api/products",
        json={"sku": "XSS-1", "name": xss_payload}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == xss_payload
    
    # Verify retrieval
    get_res = client.get(f"/api/products/{data['id']}")
    assert get_res.json()["name"] == xss_payload
