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

        # Seed repair team member account for Team Alpha
        alpha_team_res = await db.execute(select(RepairTeam).where(RepairTeam.name == "Team Alpha"))
        alpha_team = alpha_team_res.scalar_one_or_none()
        if alpha_team:
            existing_member = await db.execute(select(User).where(User.email == "team.alpha@paventra.local"))
            if not existing_member.scalar_one_or_none():
                team_user = User(
                    email="team.alpha@paventra.local",
                    full_name="Team Alpha Lead",
                    hashed_password=hash_password("TeamAlpha2024!"),
                    role=UserRole.REPAIR_TEAM,
                    team_id=alpha_team.id,
                )
                db.add(team_user)
                await db.commit()
                print("Created repair team user: team.alpha@paventra.local / TeamAlpha2024!")
            else:
                print("Repair team user already exists: team.alpha@paventra.local")

        print("\nSeed complete.")
        print(f"  Coordinator login: {COORDINATOR_EMAIL}")
        print(f"  Password:          {COORDINATOR_PASSWORD}")
        print("  Repair Team login: team.alpha@paventra.local / TeamAlpha2024!")


if __name__ == "__main__":
    asyncio.run(seed())
