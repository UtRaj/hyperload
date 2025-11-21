
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Handle different deployment platforms
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"DEBUG: DATABASE_URL from env: {DATABASE_URL[:30] if DATABASE_URL else 'NOT SET'}...")

# Railway provides DATABASE_URL, but if not set, try alternatives
if not DATABASE_URL:
    # Try Railway's private networking format
    DATABASE_URL = os.getenv("DATABASE_PRIVATE_URL")
    print(f"DEBUG: Trying DATABASE_PRIVATE_URL: {DATABASE_URL[:30] if DATABASE_URL else 'NOT SET'}...")
    
if not DATABASE_URL:
    # Fallback to default for local development
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/product_importer"
    print(f"DEBUG: Using fallback localhost")

# Fix for Railway/Render: they might use postgres:// instead of postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print(f"DEBUG: Fixed postgres:// to postgresql://")

print(f"DEBUG: Final DATABASE_URL: {DATABASE_URL[:50]}...")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
