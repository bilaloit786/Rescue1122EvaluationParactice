"""
Run this ONCE to create the first admin account.
Usage:
    cd backend
    ADMIN_PASSWORD='choose-a-strong-password' python seed_admin.py
"""
import asyncio
import os
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.user import User, StaffProfile
from app.core.security import get_password_hash
from sqlalchemy import select

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@rescue1122.gov.pk")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_PASSWORD:
    raise SystemExit("Set ADMIN_PASSWORD before running seed_admin.py.")


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.username == ADMIN_USERNAME))
        if existing.scalar_one_or_none():
            print(f"Admin '{ADMIN_USERNAME}' already exists. Skipping.")
            return

        admin = User(
            email=ADMIN_EMAIL,
            username=ADMIN_USERNAME,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        profile = StaffProfile(
            user_id=admin.id,
            full_name="System Administrator",
            designation="admin",
            district="Lahore",
        )
        db.add(profile)
        await db.commit()
        print(f"Admin created: username='{ADMIN_USERNAME}'")
        print("IMPORTANT: Store the admin password securely and rotate it when required.")


if __name__ == "__main__":
    asyncio.run(seed())
