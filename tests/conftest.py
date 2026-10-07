import os
from collections.abc import Generator
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.services.storage_service import storage_service

# Create an in-memory SQLite engine for fast, isolated testing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables before each test and drop them afterward."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a standalone SQLAlchemy session for direct database assertions."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def override_storage(tmp_path: Path):
    """Ensure all test files are written to an isolated temporary directory."""
    original_storage = settings.STORAGE_PATH
    original_base = storage_service.base_dir

    settings.STORAGE_PATH = str(tmp_path / "certificates")
    storage_service.base_dir = tmp_path / "certificates"
    storage_service.base_dir.mkdir(parents=True, exist_ok=True)

    yield tmp_path / "certificates"

    settings.STORAGE_PATH = original_storage
    storage_service.base_dir = original_base


@pytest.fixture
def client(monkeypatch) -> Generator[TestClient, None, None]:
    """TestClient fixture with get_db dependency overridden to the test database."""
    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Also ensure the worker uses TestingSessionLocal during tests
    from app.workers.certificate_worker import certificate_worker
    monkeypatch.setattr(certificate_worker, "session_factory", TestingSessionLocal)

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
