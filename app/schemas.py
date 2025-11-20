from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    sku: str = Field(..., max_length=255)
    name: str = Field(..., max_length=500)
    description: Optional[str] = None
    active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    active: Optional[bool] = None

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class WebhookBase(BaseModel):
    url: str = Field(..., max_length=2048)
    event_type: str = Field(..., max_length=50)
    enabled: bool = True

class WebhookCreate(WebhookBase):
    pass

class WebhookUpdate(BaseModel):
    url: Optional[str] = Field(None, max_length=2048)
    event_type: Optional[str] = Field(None, max_length=50)
    enabled: Optional[bool] = None

class Webhook(WebhookBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    task_id: str
    message: str

class ProgressUpdate(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str
    total_rows: Optional[int] = None
    processed_rows: Optional[int] = None
