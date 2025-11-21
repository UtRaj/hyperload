
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Detect if we're in a production environment (Railway, Render, Heroku, etc.)
PRODUCTION_ENV = any([
    os.getenv("RAILWAY_ENVIRONMENT"),
    os.getenv("RENDER"),
    os.getenv("DYNO"),  # Heroku
    os.getenv("FLY_APP_NAME"),  # Fly.io
])

print(f"DEBUG: Production environment detected: {PRODUCTION_ENV}")
print(f"DEBUG: RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT')}")

# Debug: Print all environment variables that might contain database info
print("\nDEBUG: Checking all database-related environment variables:")
for key in sorted(os.environ.keys()):
    if any(keyword in key.upper() for keyword in ['DATABASE', 'POSTGRES', 'DB_', 'PG']):
        value = os.environ[key]
        # Show first 30 chars for security
        print(f"  {key}: {value[:30]}..." if len(value) > 30 else f"  {key}: {value}")

# Try multiple possible environment variable names for Railway
DATABASE_URL = None

# Try standard DATABASE_URL first
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"\nDEBUG: DATABASE_URL from env: {DATABASE_URL[:30] if DATABASE_URL else 'NOT SET'}...")

# Railway-specific alternatives
if not DATABASE_URL:
    DATABASE_URL = os.getenv("DATABASE_PRIVATE_URL")
    print(f"DEBUG: Trying DATABASE_PRIVATE_URL: {DATABASE_URL[:30] if DATABASE_URL else 'NOT SET'}...")

if not DATABASE_URL:
    # Try constructing from individual components (Railway provides these)
    db_host = os.getenv("PGHOST") or os.getenv("DB_HOST")
    db_port = os.getenv("PGPORT") or os.getenv("DB_PORT") or "5432"
    db_name = os.getenv("PGDATABASE") or os.getenv("DB_NAME") or "railway"
    db_user = os.getenv("PGUSER") or os.getenv("DB_USER") or "postgres"
    db_password = os.getenv("PGPASSWORD") or os.getenv("DB_PASSWORD")
    
    if db_host and db_password:
        DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print(f"DEBUG: Constructed from components: postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}")

if not DATABASE_URL:
    if PRODUCTION_ENV:
        # In production, DATABASE_URL MUST be set
        print("\n" + "="*80)
        print("ERROR: DATABASE_URL environment variable is not set!")
        print("="*80)
        print("\nThis appears to be a production environment, but no database URL was found.")
        print("\nPlease configure the DATABASE_URL environment variable in your deployment platform:")
        print("  - Railway: Add a reference to your PostgreSQL service")
        print("  - Render: Link your PostgreSQL database")
        print("  - Heroku: Attach a Postgres add-on")
        print("\nSteps for Railway:")
        print("  1. Go to your service settings")
        print("  2. Click 'Variables' tab")
        print("  3. Click 'New Variable' → 'Add Reference'")
        print("  4. Select your PostgreSQL service")
        print("  5. Choose 'DATABASE_URL' from the dropdown")
        print("\nAlternatively, you can set individual variables:")
        print("  - PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD")
        print("="*80 + "\n")
        sys.exit(1)
    else:
        # Fallback to default for local development
        DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/product_importer"
        print(f"DEBUG: Using fallback localhost (development mode)")

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
