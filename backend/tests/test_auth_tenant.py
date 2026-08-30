import os
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.auth import login
from app.core.security import hash_password, verify_access_token
from app.models.org import Org
from app.models.user import User
from app.schemas.auth import LoginRequest


@pytest.mark.asyncio
async def test_login_uses_organization_slug_to_disambiguate_email() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    shared_email = f"shared-{uuid4()}@example.com"
    first_org = Org(
        id=uuid4(),
        name="First",
        slug=f"first-{uuid4()}",
        timezone="UTC",
        settings={},
        is_active=True,
    )
    second_org = Org(
        id=uuid4(),
        name="Second",
        slug=f"second-{uuid4()}",
        timezone="UTC",
        settings={},
        is_active=True,
    )
    first_user = User(
        id=uuid4(),
        org_id=first_org.id,
        name="First User",
        email=shared_email,
        password_hash=hash_password("first-password"),
        role="admin",
        is_active=True,
    )
    second_user = User(
        id=uuid4(),
        org_id=second_org.id,
        name="Second User",
        email=shared_email,
        password_hash=hash_password("second-password"),
        role="admin",
        is_active=True,
    )

    try:
        async with session_factory() as session:
            session.add_all([first_org, second_org, first_user, second_user])
            await session.commit()
            response = await login(
                LoginRequest(
                    organization=second_org.slug,
                    email=shared_email,
                    password="second-password",
                ),
                session,
            )
            claims = verify_access_token(response.access_token)
            assert response.user_id == second_user.id
            assert claims is not None
            assert claims["org_id"] == str(second_org.id)
    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(
                delete(Org).where(Org.id.in_([first_org.id, second_org.id]))
            )
            await cleanup_session.commit()
        await engine.dispose()
