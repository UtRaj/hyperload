import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import app
import os

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db, mocker):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock init_db to prevent startup event from trying to connect to real DB
    with mocker.patch("app.main.init_db"):
        with TestClient(app) as c:
            yield c
    
    del app.dependency_overrides[get_db]

@pytest.fixture(autouse=True)
def mock_celery(mocker):
    """Mock Celery tasks to avoid running them"""
    mocker.patch("app.tasks.import_csv_task.delay")
    mocker.patch("app.tasks.trigger_webhooks.delay")
    return mocker

@pytest.fixture(autouse=True)
def mock_redis(mocker):
    """Mock Redis to avoid connection errors"""
    mock_redis = mocker.patch("app.tasks.redis_client")
    mock_redis.publish.return_value = None
    mock_redis.setex.return_value = None
    return mock_redis
