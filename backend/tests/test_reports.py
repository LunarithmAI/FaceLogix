import csv
import io
import os
from datetime import UTC, date, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import require_operator
from app.api.v1 import reports
from app.core.database import get_db
from app.models.attendance_log import AttendanceLog
from app.models.org import Org
from app.models.user import User


def test_report_range_validation_rejects_reverse_and_oversized_ranges() -> None:
    with pytest.raises(HTTPException) as reverse:
        reports.validate_range(date(2026, 8, 2), date(2026, 8, 1))
    assert "INVALID_DATE_RANGE" in str(reverse.value.detail)

    with pytest.raises(HTTPException) as oversized:
        reports.validate_range(date(2025, 1, 1), date(2026, 1, 2))
    assert "DATE_RANGE_TOO_LARGE" in str(oversized.value.detail)


@pytest.mark.asyncio
async def test_reports_group_by_local_date_and_export_safe_csv() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    org = Org(
        id=uuid4(),
        name="Report Test",
        slug=f"report-test-{uuid4()}",
        timezone="America/New_York",
        settings={},
        is_active=True,
    )
    operator = User(
        id=uuid4(),
        org_id=org.id,
        name="Operator",
        email=f"operator-{uuid4()}@example.com",
        role="admin",
        is_active=True,
    )
    member = User(
        id=uuid4(),
        org_id=org.id,
        name="=SUM(1,2)",
        email=f"member-{uuid4()}@example.com",
        role="member",
        is_active=True,
    )

    try:
        async with session_factory() as session:
            session.add_all([org, operator, member])
            await session.flush()
            session.add_all(
                [
                    AttendanceLog(
                        org_id=org.id,
                        user_id=member.id,
                        ts=datetime(2026, 8, 3, 3, 30, tzinfo=UTC),
                        type="check_in",
                        status="on_time",
                        confidence_score=0.5,
                        meta={},
                    ),
                    AttendanceLog(
                        org_id=org.id,
                        user_id=member.id,
                        ts=datetime(2026, 8, 3, 13, 30, tzinfo=UTC),
                        type="check_in",
                        status="on_time",
                        confidence_score=0.0,
                        meta={},
                    ),
                    AttendanceLog(
                        org_id=org.id,
                        user_id=member.id,
                        ts=datetime(2026, 8, 3, 22, 0, tzinfo=UTC),
                        type="check_out",
                        status="early",
                        confidence_score=0.9,
                        meta={},
                    ),
                ]
            )
            await session.commit()

            daily = await reports.get_daily_summaries(
                date(2026, 8, 3),
                date(2026, 8, 3),
                session,
                operator,
            )
            assert len(daily) == 1
            assert daily[0].check_ins == 1
            assert daily[0].check_outs == 1
            assert daily[0].absent == 1

            user_stats = await reports.get_user_stats(
                member.id,
                session,
                operator,
                date(2026, 8, 3),
                date(2026, 8, 3),
            )
            assert user_stats.summary.total_check_ins == 1
            assert user_stats.average_check_in_time == "09:30"

            response = await reports.export_report(
                date(2026, 8, 3),
                date(2026, 8, 3),
                session,
                operator,
                member.id,
                "csv",
            )
            rows = list(csv.reader(io.StringIO(bytes(response.body).decode())))
            assert len(rows) == 3
            assert {row[1] for row in rows[1:]} == {"'=SUM(1,2)"}
            assert any(row[-1] == "0.0000" for row in rows[1:])

            app = FastAPI()
            app.include_router(reports.router)

            async def override_db():  # type: ignore[no-untyped-def]
                yield session

            app.dependency_overrides[get_db] = override_db
            app.dependency_overrides[require_operator] = lambda: operator
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                invalid_format = await client.get(
                    "/reports/export",
                    params={
                        "from_date": "2026-08-03",
                        "to_date": "2026-08-03",
                        "format": "xlsx",
                    },
                )
            assert invalid_format.status_code == 422
            paths = app.openapi()["paths"]
            assert "/reports/summary/user/{user_id}" not in paths
            assert "/reports/attendance/csv" not in paths
    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(delete(Org).where(Org.id == org.id))
            await cleanup_session.commit()
        await engine.dispose()
