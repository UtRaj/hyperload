import os
import uuid
import json
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
import asyncio
import redis.asyncio as aioredis

from app.database import get_db, init_db
from app.models import Product, Webhook
from app.schemas import (
    Product as ProductSchema,
    ProductCreate,
    ProductUpdate,
    Webhook as WebhookSchema,
    WebhookCreate,
    WebhookUpdate,
    UploadResponse,
)
from app.tasks import import_csv_task, trigger_webhooks

app = FastAPI(title="Product Importer API")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.csv")
    
    CHUNK_SIZE = 1024 * 1024
    
    with open(file_path, "wb") as f:
        while chunk := await file.read(CHUNK_SIZE):
            f.write(chunk)
    
    file_size = os.path.getsize(file_path)
    task = import_csv_task.delay(file_path, file_size)
    
    return UploadResponse(
        task_id=task.id,
        message="File upload started. Processing in background."
    )

@app.get("/api/progress/{task_id}")
async def progress_stream(task_id: str):
    async def event_generator():
        redis_conn = await aioredis.from_url(REDIS_URL)
        pubsub = redis_conn.pubsub()
        await pubsub.subscribe(f"progress:{task_id}")
        
        cached_status = await redis_conn.get(f"task_status:{task_id}")
        if cached_status:
            yield f"data: {cached_status.decode()}\n\n"
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
                if message and message['type'] == 'message':
                    data = message['data'].decode()
                    yield f"data: {data}\n\n"
                    
                    parsed = json.loads(data)
                    if parsed['status'] in ['completed', 'failed']:
                        break
                
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"progress:{task_id}")
            await redis_conn.close()
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/products", response_model=dict)
def list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sku: Optional[str] = None,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    
    if sku:
        query = query.filter(func.lower(Product.sku).contains(sku.lower()))
    
    if name:
        query = query.filter(func.lower(Product.name).contains(name.lower()))
    
    if active is not None:
        query = query.filter(Product.active == active)
    
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Product.sku).like(search_term),
                func.lower(Product.name).like(search_term),
                func.lower(Product.description).like(search_term)
            )
        )
    
    total = query.count()
    
    products = query.order_by(Product.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "items": [ProductSchema.from_orm(p) for p in products],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }

@app.post("/api/products", response_model=ProductSchema)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    sku_lower = product.sku.lower()
    existing = db.query(Product).filter(func.lower(Product.sku) == sku_lower).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    trigger_webhooks.delay(db_product.id, "product.created")
    
    return ProductSchema.from_orm(db_product)

@app.get("/api/products/{product_id}", response_model=ProductSchema)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductSchema.from_orm(product)

@app.put("/api/products/{product_id}", response_model=ProductSchema)
def update_product(product_id: int, product_update: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_update.dict(exclude_unset=True)
    
    if 'sku' in update_data and update_data['sku']:
        sku_lower = update_data['sku'].lower()
        existing = db.query(Product).filter(
            func.lower(Product.sku) == sku_lower,
            Product.id != product_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    trigger_webhooks.delay(product.id, "product.updated")
    
    return ProductSchema.from_orm(product)

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    trigger_webhooks.delay(product.id, "product.deleted")
    
    db.delete(product)
    db.commit()
    
    return {"message": "Product deleted successfully"}

@app.delete("/api/products")
def bulk_delete_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    count = len(products)
    
    for product in products:
        trigger_webhooks.delay(product.id, "product.deleted")
    
    db.query(Product).delete()
    db.commit()
    
    return {"message": f"Deleted {count} products successfully", "count": count}

@app.get("/api/webhooks", response_model=List[WebhookSchema])
def list_webhooks(db: Session = Depends(get_db)):
    webhooks = db.query(Webhook).order_by(Webhook.id.desc()).all()
    return [WebhookSchema.from_orm(w) for w in webhooks]

@app.post("/api/webhooks", response_model=WebhookSchema)
def create_webhook(webhook: WebhookCreate, db: Session = Depends(get_db)):
    db_webhook = Webhook(**webhook.dict())
    db.add(db_webhook)
    db.commit()
    db.refresh(db_webhook)
    return WebhookSchema.from_orm(db_webhook)

@app.put("/api/webhooks/{webhook_id}", response_model=WebhookSchema)
def update_webhook(webhook_id: int, webhook_update: WebhookUpdate, db: Session = Depends(get_db)):
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    update_data = webhook_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(webhook, field, value)
    
    db.commit()
    db.refresh(webhook)
    return WebhookSchema.from_orm(webhook)

@app.delete("/api/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    db.delete(webhook)
    db.commit()
    return {"message": "Webhook deleted successfully"}

@app.post("/api/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: int, db: Session = Depends(get_db)):
    import httpx
    import time
    
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    test_payload = {
        "event": "webhook.test",
        "webhook_id": webhook.id,
        "timestamp": time.time()
    }
    
    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook.url, json=test_payload)
        response_time = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "status_code": response.status_code,
            "response_time_ms": round(response_time, 2),
            "message": f"Webhook test successful (HTTP {response.status_code})"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Webhook test failed: {str(e)}"
        }
