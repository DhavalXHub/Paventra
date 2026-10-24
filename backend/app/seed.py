"""
Seed script — creates the first coordinator account and sample repair teams.
Run from backend/: python -m app.seed
"""
import asyncio
import sys
from app.core.security import hash_password
from app.db.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.team import RepairTeam
from sqlalchemy import select


COORDINATOR_EMAIL = "coordinator@paventra.local"
COORDINATOR_PASSWORD = "Paventra2024!"
COORDINATOR_NAME = "City Coordinator"


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        existing = await db.execute(select(User).where(User.email == COORDINATOR_EMAIL))
        if existing.scalar_one_or_none():
            print(f"Coordinator already exists: {COORDINATOR_EMAIL}")
        else:
            coordinator = User(
                email=COORDINATOR_EMAIL,
                full_name=COORDINATOR_NAME,
                hashed_password=hash_password(COORDINATOR_PASSWORD),
                role=UserRole.COORDINATOR,
            )
            db.add(coordinator)
            print(f"Created coordinator: {COORDINATOR_EMAIL} / {COORDINATOR_PASSWORD}")

        # Repair teams
        teams = [
            {"name": "Team Alpha", "description": "North district road repair crew", "contact_email": "alpha@paventra.local"},
            {"name": "Team Beta",  "description": "South district road repair crew", "contact_email": "beta@paventra.local"},
            {"name": "Team Gamma", "description": "Emergency pothole repair unit",   "contact_email": "gamma@paventra.local"},
        ]
        for t in teams:
            existing_team = await db.execute(select(RepairTeam).where(RepairTeam.name == t["name"]))
            if not existing_team.scalar_one_or_none():
                db.add(RepairTeam(**t))
                print(f"Created team: {t['name']}")
            else:
                print(f"Team already exists: {t['name']}")

        await db.commit()
        print("\nSeed complete.")
        print(f"  Coordinator login: {COORDINATOR_EMAIL}")
        print(f"  Password:          {COORDINATOR_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
