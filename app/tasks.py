import csv
import json
import time
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Product, Webhook
import redis
import os
import httpx
import logging

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL)

CHUNK_SIZE = 1000

logger = logging.getLogger(__name__)

def publish_progress(task_id: str, status: str, progress: float, message: str, total_rows: int = 0, processed_rows: int = 0):
    data = {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "message": message,
        "total_rows": total_rows,
        "processed_rows": processed_rows,
    }
    redis_client.publish(f"progress:{task_id}", json.dumps(data))
    redis_client.setex(f"task_status:{task_id}", 3600, json.dumps(data))

@celery_app.task(bind=True)
def import_csv_task(self, file_path: str, file_size: int = 0):
    task_id = self.request.id
    db = SessionLocal()
    
    try:
        publish_progress(task_id, "counting", 0, "Counting CSV rows...")
        
        total_data_rows = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            if not reader.fieldnames or 'sku' not in reader.fieldnames or 'name' not in reader.fieldnames:
                raise ValueError("CSV must contain 'sku' and 'name' columns")
            
            for row in reader:
                if row.get('sku', '').strip() and row.get('name', '').strip():
                    total_data_rows += 1
        
        if total_data_rows == 0:
            publish_progress(task_id, "completed", 100, "No valid rows to import", 0, 0)
            return {"status": "success", "total_csv_rows": 0, "unique_products": 0}
        
        publish_progress(task_id, "importing", 5, f"Found {total_data_rows} rows to import", total_data_rows, 0)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            rows_processed = 0
            unique_products_saved = 0
            all_seen_skus = set()
            current_batch = {}
            last_progress_row = 0
            last_progress_time = time.time()
            PROGRESS_ROW_INTERVAL = 100
            PROGRESS_TIME_INTERVAL = 0.5
            
            for row in reader:
                sku = row.get('sku', '').strip()
                name = row.get('name', '').strip()
                description = row.get('description', '').strip()
                
                if not sku or not name:
                    continue
                
                rows_processed += 1
                sku_lower = sku.lower()
                
                all_seen_skus.add(sku_lower)
                current_batch[sku_lower] = {
                    'sku': sku,
                    'name': name,
                    'description': description if description else None,
                    'active': True
                }
                
                current_time = time.time()
                should_publish = (
                    rows_processed - last_progress_row >= PROGRESS_ROW_INTERVAL or
                    current_time - last_progress_time >= PROGRESS_TIME_INTERVAL
                )
                
                if should_publish:
                    progress = 5 + (rows_processed / total_data_rows) * 85
                    publish_progress(task_id, "importing", progress, 
                                   f"Processing: {rows_processed}/{total_data_rows} rows ({len(all_seen_skus)} unique, {unique_products_saved} saved)",
                                   total_data_rows, rows_processed)
                    last_progress_row = rows_processed
                    last_progress_time = current_time
                
                if len(current_batch) >= CHUNK_SIZE:
                    batch_data = list(current_batch.values())
                    result = _bulk_upsert_products(db, batch_data)
                    
                    for product_id, event_type in result:
                        trigger_webhooks.delay(product_id, event_type)
                    
                    unique_products_saved += len(batch_data)
                    current_batch = {}
            
            if current_batch:
                batch_data = list(current_batch.values())
                result = _bulk_upsert_products(db, batch_data)
                
                for product_id, event_type in result:
                    trigger_webhooks.delay(product_id, event_type)
                
                unique_products_saved += len(batch_data)
            
            publish_progress(task_id, "completed", 100, 
                           f"Successfully imported {unique_products_saved} unique products from {rows_processed} total rows",
                           total_data_rows, rows_processed)
        
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to remove temp file: {e}")
        
        return {"status": "success", "total_csv_rows": total_data_rows, "unique_products": unique_products_saved}
    
    except Exception as e:
        error_msg = f"Import failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        publish_progress(task_id, "failed", 0, error_msg)
        db.rollback()
        raise
    
    finally:
        db.close()

def _bulk_upsert_products(db, products_data):
    product_ids_and_events = []
    
    existing_skus = {}
    sku_list = [p['sku'].lower() for p in products_data]
    existing_products = db.query(Product).filter(func.lower(Product.sku).in_(sku_list)).all()
    
    for p in existing_products:
        existing_skus[p.sku.lower()] = p
    
    products_to_add = []
    products_to_update = []
    
    for product_dict in products_data:
        sku_lower = product_dict['sku'].lower()
        
        if sku_lower in existing_skus:
            existing = existing_skus[sku_lower]
            existing.name = product_dict['name']
            existing.description = product_dict['description']
            products_to_update.append(existing)
            product_ids_and_events.append((existing.id, "product.updated"))
        else:
            new_product = Product(**product_dict)
            products_to_add.append(new_product)
    
    if products_to_add:
        db.add_all(products_to_add)
        db.flush()
        for p in products_to_add:
            product_ids_and_events.append((p.id, "product.created"))
    
    db.commit()
    return product_ids_and_events

@celery_app.task
def trigger_webhooks(product_id: int, event_type: str):
    db = SessionLocal()
    
    try:
        webhooks = db.query(Webhook).filter(
            Webhook.enabled == True,
            Webhook.event_type == event_type
        ).all()
        
        if not webhooks:
            return
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return
        
        payload = {
            "event": event_type,
            "product": {
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "description": product.description,
                "active": product.active,
            }
        }
        
        for webhook in webhooks:
            try:
                with httpx.Client(timeout=10.0) as client:
                    client.post(webhook.url, json=payload)
            except:
                pass
    
    finally:
        db.close()
