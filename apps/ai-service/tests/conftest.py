"""
Pytest fixtures for SwipeHire AI service tests.
Mocks heavy ML dependencies (sentence_transformers) so tests run without
downloading models. Each test gets its own SAVEPOINT-isolated DB session.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch
import numpy as np

import pytest
import pytest_asyncio

# ── Mock sentence_transformers BEFORE any app import ──────────────────────────
_mock_st = MagicMock()
_mock_model = MagicMock()
_mock_model.encode = lambda text, **kw: np.random.rand(384).astype("float32")
_mock_st.SentenceTransformer.return_value = _mock_model
sys.modules.setdefault("sentence_transformers", _mock_st)

# Mock other heavy optional deps
for _mod in ("playwright", "playwright.async_api", "pytesseract",
             "pdfplumber", "fitz", "docx", "spacy",
             "qdrant_client", "qdrant_client.http", "qdrant_client.http.models"):
    sys.modules.setdefault(_mod, MagicMock())

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from database import Base, get_db
from main import app
from models.user import User, UserProfile
from models.job import Job

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    await connection.begin()
    await connection.begin_nested()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()
    yield session
    await session.close()
    await connection.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        phone="9876543210",
        email="test@swipehire.in",
        full_name="Test User",
        is_verified=True,
        plan="free",
    )
    db_session.add(user)
    profile = UserProfile(
        user_id=user.id,
        skills=["Python", "React"],
        experience_years=2.0,
        is_onboarded=True,
        preferred_locations=["Bangalore"],
        job_types=["full-time"],
    )
    db_session.add(profile)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    from routers.auth import _create_access_token
    token = _create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_job(db_session: AsyncSession) -> Job:
    job = Job(
        id=uuid.uuid4(),
        source="seed",
        title="Senior Python Developer",
        company="TechCorp India",
        location="Bangalore",
        is_remote=False,
        salary_min_lpa=10.0,
        salary_max_lpa=18.0,
        experience_min=2.0,
        experience_max=5.0,
        skills_required=["Python", "FastAPI", "PostgreSQL"],
        description="Build amazing products with Python.",
        apply_url="https://techcorp.in/careers/1",
        job_type="full-time",
        industry="Engineering",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()
    return job
