from fastapi.testclient import TestClient

def test_create_webhook(client: TestClient):
    response = client.post(
        "/api/webhooks",
        json={
            "url": "https://example.com/webhook",
            "event_type": "product.created",
            "enabled": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com/webhook"
    assert data["event_type"] == "product.created"
    assert data["id"] is not None

def test_list_webhooks(client: TestClient):
    client.post("/api/webhooks", json={"url": "http://a.com", "event_type": "a"})
    client.post("/api/webhooks", json={"url": "http://b.com", "event_type": "b"})
    
    response = client.get("/api/webhooks")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_update_webhook(client: TestClient):
    create_res = client.post(
        "/api/webhooks",
        json={"url": "http://old.com", "event_type": "old"}
    )
    webhook_id = create_res.json()["id"]
    
    response = client.put(
        f"/api/webhooks/{webhook_id}",
        json={"url": "http://new.com", "enabled": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "http://new.com"
    assert data["enabled"] is False

def test_delete_webhook(client: TestClient):
    create_res = client.post(
        "/api/webhooks",
        json={"url": "http://del.com", "event_type": "del"}
    )
    webhook_id = create_res.json()["id"]
    
    response = client.delete(f"/api/webhooks/{webhook_id}")
    assert response.status_code == 200
    
    # Verify deleted
    list_res = client.get("/api/webhooks")
    assert len(list_res.json()) == 0

def test_test_webhook_endpoint(client: TestClient, mocker):
    # Mock httpx in the endpoint
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_post.return_value.status_code = 200
    
    create_res = client.post(
        "/api/webhooks",
        json={"url": "http://test.com", "event_type": "test"}
    )
    webhook_id = create_res.json()["id"]
    
    response = client.post(f"/api/webhooks/{webhook_id}/test")
    assert response.status_code == 200
    assert response.json()["success"] is True
