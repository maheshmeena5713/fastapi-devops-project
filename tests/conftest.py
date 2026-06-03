# tests/conftest.py
"""
Shared fixtures for Blog API tests.

KEY CONCEPT: We use SQLite in-memory for tests.
- No PostgreSQL needed to run tests
- Each test gets a fresh empty database
- Tests are fast and isolated
- Production uses PostgreSQL — same SQLAlchemy code works with both
"""

import pytest
import os

# Set test environment BEFORE any app imports
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db


# ── Test Database Setup ────────────────────────────────
SQLITE_URL = "sqlite:///./test.db"

# connect_args needed for SQLite only (not PostgreSQL)
test_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False}
)

TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


# ── Fixtures ───────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh database for each test.
    - Creates all tables before test
    - Drops all tables after test
    - Each test starts with empty DB
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Creates a TestClient with overridden DB dependency.

    KEY CONCEPT: dependency_overrides
    - Replaces get_db() with our test DB session
    - Endpoints use test DB instead of real PostgreSQL
    - No real DB needed for tests
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_post(client):
    """
    Creates one post and returns it.
    Used by tests that need an existing post.
    """
    response = client.post("/posts", json={
        "title": "Sample Blog Post",
        "content": "This is sample content for testing purposes.",
        "author": "Test Author"
    })
    return response.json()


@pytest.fixture
def multiple_posts(client):
    """
    Creates 5 posts for pagination/filter tests.
    """
    posts = [
        {"title": f"Post Number {i}", "content": f"Content for post {i} here.", "author": f"Author{i}"}
        for i in range(1, 6)
    ]
    created = []
    for post in posts:
        response = client.post("/posts", json=post)
        created.append(response.json())
    return created