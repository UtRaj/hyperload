import pytest
import csv
import os
from fastapi.testclient import TestClient
from app.tasks import import_csv_task
from app.models import Product

def test_upload_endpoint(client: TestClient, mocker):
    # Mock the Celery task delay method
    mock_task = mocker.patch("app.tasks.import_csv_task.delay")
    mock_task.return_value.id = "test-task-id"
    
    # Create a dummy CSV file
    csv_content = "sku,name,description\nPROD-1,Test 1,Desc 1"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    
    response = client.post("/api/upload", files=files)
    assert response.status_code == 200
    assert response.json()["task_id"] == "test-task-id"
    
    # Verify task was called
    assert mock_task.called

def test_upload_invalid_file_type(client: TestClient):
    files = {"file": ("test.txt", "content", "text/plain")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400

def test_import_csv_task_logic(db, mock_redis, mocker):
    """Test the actual import logic without Celery/Redis"""
    # Mock publish_progress to avoid Redis calls
    mocker.patch("app.tasks.publish_progress")
    mocker.patch("app.tasks.trigger_webhooks.delay")
    
    # Create a temporary CSV file
    file_path = "temp_test_import.csv"
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "description"])
        writer.writerow(["TEST-A", "Product A", "Desc A"])
        writer.writerow(["TEST-B", "Product B", "Desc B"])
    
    try:
        # Run the task function synchronously
        # We need to patch SessionLocal in tasks.py to use our test db
        mocker.patch("app.tasks.SessionLocal", return_value=db)
        
        # Use .apply() to execute task synchronously with a real task instance/context
        result = import_csv_task.apply(args=[file_path]).result
        
        assert result["status"] == "success"
        assert result["unique_products"] == 2
        
        # Verify products in DB
        products = db.query(Product).all()
        assert len(products) == 2
        skus = [p.sku for p in products]
        assert "TEST-A" in skus
        assert "TEST-B" in skus
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def test_import_duplicates_logic(db, mock_redis, mocker):
    """Test duplicate handling (case-insensitive overwrite)"""
    mocker.patch("app.tasks.publish_progress")
    mocker.patch("app.tasks.trigger_webhooks.delay")
    mocker.patch("app.tasks.SessionLocal", return_value=db)
    
    file_path = "temp_test_duplicates.csv"
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "description"])
        writer.writerow(["TEST-DUP", "Original Name", "Original Desc"])
import pytest
import csv
import os
from fastapi.testclient import TestClient
from app.tasks import import_csv_task
from app.models import Product

def test_upload_endpoint(client: TestClient, mocker):
    # Mock the Celery task delay method
    mock_task = mocker.patch("app.tasks.import_csv_task.delay")
    mock_task.return_value.id = "test-task-id"
    
    # Create a dummy CSV file
    csv_content = "sku,name,description\nPROD-1,Test 1,Desc 1"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    
    response = client.post("/api/upload", files=files)
    assert response.status_code == 200
    assert response.json()["task_id"] == "test-task-id"
    
    # Verify task was called
    assert mock_task.called

def test_upload_invalid_file_type(client: TestClient):
    files = {"file": ("test.txt", "content", "text/plain")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400

def test_import_csv_task_logic(db, mock_redis, mocker):
    """Test the actual import logic without Celery/Redis"""
    # Mock publish_progress to avoid Redis calls
    mocker.patch("app.tasks.publish_progress")
    mocker.patch("app.tasks.trigger_webhooks.delay")
    
    # Create a temporary CSV file
    file_path = "temp_test_import.csv"
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "description"])
        writer.writerow(["TEST-A", "Product A", "Desc A"])
        writer.writerow(["TEST-B", "Product B", "Desc B"])
    
    try:
        # Run the task function synchronously
        # We need to patch SessionLocal in tasks.py to use our test db
        mocker.patch("app.tasks.SessionLocal", return_value=db)
        
        # Use .apply() to execute task synchronously with a real task instance/context
        result = import_csv_task.apply(args=[file_path]).result
        
        assert result["status"] == "success"
        assert result["unique_products"] == 2
        
        # Verify products in DB
        products = db.query(Product).all()
        assert len(products) == 2
        skus = [p.sku for p in products]
        assert "TEST-A" in skus
        assert "TEST-B" in skus
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def test_import_duplicates_logic(db, mock_redis, mocker):
    """Test duplicate handling (case-insensitive overwrite)"""
    mocker.patch("app.tasks.publish_progress")
    mocker.patch("app.tasks.trigger_webhooks.delay")
    mocker.patch("app.tasks.SessionLocal", return_value=db)
    
    file_path = "temp_test_duplicates.csv"
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "description"])
        writer.writerow(["TEST-DUP", "Original Name", "Original Desc"])
        writer.writerow(["test-dup", "Updated Name", "Updated Desc"]) # Should overwrite
    
    try:
        result = import_csv_task.apply(args=[file_path]).result
        
        assert result["unique_products"] == 1
        # The second row "test-dup" overwrites "TEST-DUP", so the stored SKU is "test-dup"
        product = db.query(Product).filter(Product.sku == "test-dup").first()
        # Note: The first SKU case encountered is usually preserved or updated depending on implementation
        # Our implementation updates existing products.
        # Let's check if the name was updated
        assert product.name == "Updated Name"
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
