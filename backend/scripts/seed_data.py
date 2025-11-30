#!/usr/bin/env python3
"""
Seed script to create default organization and admin user.

Usage:
    python -m scripts.seed_data
    
Or from Docker:
    docker compose exec backend python -m scripts.seed_data
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models import Base, Org, User


# Default seed data
DEFAULT_ORG = {
    "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "name": "Demo Organization",
    "slug": "demo-org",
    "settings": {
        "work_start_time": "09:00",
        "work_end_time": "18:00",
        "late_threshold_minutes": 15,
        "timezone": "UTC",
    },
}

DEFAULT_ADMIN = {
    "id": "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22",
    "email": "admin@facelogix.local",
    "password": "admin123",  # Will be hashed
    "name": "System Administrator",
    "role": "admin",
}


async def seed_database():
    """Create default organization and admin user if they don't exist."""
    
    print("=" * 60)
    print("FaceLogix Database Seeder")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        # Check if org exists
        result = await session.execute(
            select(Org).where(Org.id == DEFAULT_ORG["id"])
        )
        org = result.scalar_one_or_none()
        
        if org:
            print(f"[SKIP] Organization '{DEFAULT_ORG['name']}' already exists")
        else:
            # Create organization
            org = Org(
                id=DEFAULT_ORG["id"],
                name=DEFAULT_ORG["name"],
                slug=DEFAULT_ORG["slug"],
                settings=DEFAULT_ORG["settings"],
            )
            session.add(org)
            await session.flush()
            print(f"[CREATE] Organization '{DEFAULT_ORG['name']}' created")
        
        # Check if admin user exists
        result = await session.execute(
            select(User).where(User.email == DEFAULT_ADMIN["email"])
        )
        user = result.scalar_one_or_none()
        
        if user:
            print(f"[SKIP] Admin user '{DEFAULT_ADMIN['email']}' already exists")
        else:
            # Create admin user
            user = User(
                id=DEFAULT_ADMIN["id"],
                org_id=DEFAULT_ORG["id"],
                email=DEFAULT_ADMIN["email"],
                password_hash=hash_password(DEFAULT_ADMIN["password"]),
                name=DEFAULT_ADMIN["name"],
                role=DEFAULT_ADMIN["role"],
                is_active=True,
            )
            session.add(user)
            print(f"[CREATE] Admin user '{DEFAULT_ADMIN['email']}' created")
        
        await session.commit()
    
    print()
    print("=" * 60)
    print("Seeding complete!")
    print()
    print("Default Admin Credentials:")
    print(f"  Email:    {DEFAULT_ADMIN['email']}")
    print(f"  Password: {DEFAULT_ADMIN['password']}")
    print()
    print("WARNING: Change the default password in production!")
    print("=" * 60)


async def main():
    """Main entry point."""
    try:
        await seed_database()
    except Exception as e:
        print(f"[ERROR] Seeding failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
