import os
from itertools import count
from datetime import datetime

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./test_temp_{os.getpid()}.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["ENVIRONMENT"] = "development"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["RESEND_API_KEY"] = ""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, Base, engine, get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import QuestionBank, StaffProfile, User
from main import app


TEST_DESIGNATIONS = [
    "LEAD FIRE RESCUER (LFR)",
    "FIRE & DISASTER RESCUE (FDR)",
    "OTHER",
]


def make_questions(n: int = 25, correct_index: int = 0) -> list[dict]:
    return [
        {
            "id": i + 1,
            "q": f"In a Rescue 1122 training scenario, which option best describes the safe action for sample case {i}?",
            "question": f"In a Rescue 1122 training scenario, which option best describes the safe action for sample case {i}?",
            "opts": ["Option A", "Option B", "Option C", "Option D"],
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "ans": correct_index,
            "topic": "Fire Safety",
        }
        for i in range(n)
    ]


SAMPLE_QUESTIONS = make_questions()
TestingSessionLocal = AsyncSessionLocal
_client_counter = count(1)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db(test_engine):
    async with AsyncSessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
        try:
            yield session
        finally:
            await session.rollback()
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
            await session.commit()


@pytest_asyncio.fixture
async def client(db: AsyncSession):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    limiter = getattr(app.state, "limiter", None)
    storage = getattr(limiter, "_storage", None)
    if storage and hasattr(storage, "storage"):
        storage.storage.clear()
    client_ip = f"127.0.0.{next(_client_counter) % 240 + 1}"
    async with AsyncClient(transport=ASGITransport(app=app, client=(client_ip, 50000)), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def _create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str = "password123",
    role: str = "staff",
    full_name: str = "Test User",
    district: str = "Lahore",
    designation: str = "OTHER",
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=is_active,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()
    db.add(StaffProfile(
        user_id=user.id,
        full_name=full_name,
        father_name="Test Father",
        designation=designation,
        district=district,
        station="Central Station",
        employee_id=f"EMP-{user.id}",
        phone="03001234567",
    ))
    await db.commit()
    await db.refresh(user)
    result = await db.execute(select(User).where(User.id == user.id))
    return result.scalar_one()


async def _create_questions(db: AsyncSession, topic_id: str = "fire_safety") -> list[QuestionBank]:
    rows = []
    difficulties = ["easy"] * 10 + ["medium"] * 10 + ["hard"] * 10
    for i, difficulty in enumerate(difficulties):
        question = {
            "q": f"During a Rescue 1122 {topic_id.replace('_', ' ')} operation, which response is the safest correct practice for case {i}?",
            "question": f"During a Rescue 1122 {topic_id.replace('_', ' ')} operation, which response is the safest correct practice for case {i}?",
            "opts": ["A", "B", "C", "D"],
            "options": ["A", "B", "C", "D"],
            "ans": i % 4,
            "topic": "Fire Safety",
        }
        row = QuestionBank(topic_id=topic_id, difficulty=difficulty, question=question)
        db.add(row)
        rows.append(row)
    await db.commit()
    return rows


@pytest_asyncio.fixture
async def staff_user(db):
    return await _create_user(
        db,
        username="staff_user",
        email="staff@example.com",
        role="staff",
        full_name="Staff User",
        designation="FIRE & DISASTER RESCUE (FDR)",
    )


@pytest_asyncio.fixture
async def admin_user(db):
    return await _create_user(
        db,
        username="admin_user",
        email="admin@example.com",
        role="admin",
        full_name="Admin User",
        designation="LEAD FIRE RESCUER (LFR)",
    )


@pytest_asyncio.fixture
async def inactive_user(db):
    return await _create_user(
        db,
        username="inactive_user",
        email="inactive@example.com",
        role="staff",
        is_active=False,
    )


@pytest_asyncio.fixture
async def staff_token(staff_user):
    return create_access_token({"sub": str(staff_user.id)})


@pytest_asyncio.fixture
async def admin_token(admin_user):
    return create_access_token({"sub": str(admin_user.id)})


@pytest_asyncio.fixture
async def staff_headers(staff_token):
    return {"Authorization": f"Bearer {staff_token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def question_bank(db):
    return await _create_questions(db)
