from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import managed_unit_ids, require_admin, require_operator
from app.core.database import get_db
from app.models.calendar_exception import CalendarException
from app.models.organizational_unit import OrganizationalUnit
from app.models.user import User
from app.schemas.calendar import (
    CalendarExceptionCreate,
    CalendarExceptionPatch,
    CalendarExceptionResponse,
)

router = APIRouter(prefix="/calendar-exceptions", tags=["Calendar"])


async def load_exception(
    db: AsyncSession,
    org_id: UUID,
    exception_id: UUID,
) -> CalendarException:
    exception = await db.scalar(
        select(CalendarException).where(
            CalendarException.id == exception_id,
            CalendarException.org_id == org_id,
        )
    )
    if exception is None:
        raise HTTPException(status_code=404, detail="Calendar exception not found")
    return exception


async def validate_unit(db: AsyncSession, org_id: UUID, unit_id: UUID | None) -> None:
    if unit_id is None:
        return
    exists = await db.scalar(
        select(OrganizationalUnit.id).where(
            OrganizationalUnit.id == unit_id,
            OrganizationalUnit.org_id == org_id,
        )
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="Unit not found")


async def commit_exception(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CALENDAR_EXCEPTION_CONFLICT",
                "message": "An exception already exists for this date and scope",
            },
        ) from exc


@router.get("", response_model=list[CalendarExceptionResponse])
async def list_calendar_exceptions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
    unit_id: Annotated[UUID | None, Query()] = None,
) -> list[CalendarException]:
    conditions = [CalendarException.org_id == current_user.org_id]
    if from_date is not None:
        conditions.append(CalendarException.exception_date >= from_date)
    if to_date is not None:
        conditions.append(CalendarException.exception_date <= to_date)
    scope_ids = await managed_unit_ids(db, current_user)
    if unit_id is not None:
        if unit_id not in scope_ids:
            raise HTTPException(status_code=403, detail="Unit is outside managed scope")
        conditions.append(CalendarException.unit_id == unit_id)
    elif current_user.role == "manager":
        conditions.append(
            or_(
                CalendarException.unit_id.is_(None),
                CalendarException.unit_id.in_(scope_ids),
            )
        )
    return list(
        (
            await db.scalars(
                select(CalendarException)
                .where(*conditions)
                .order_by(CalendarException.exception_date, CalendarException.unit_id)
            )
        ).all()
    )


@router.post("", response_model=CalendarExceptionResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_exception(
    payload: CalendarExceptionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> CalendarException:
    await validate_unit(db, current_user.org_id, payload.unit_id)
    exception = CalendarException(org_id=current_user.org_id, **payload.model_dump())
    db.add(exception)
    await commit_exception(db)
    await db.refresh(exception)
    return exception


@router.patch("/{exception_id}", response_model=CalendarExceptionResponse)
async def update_calendar_exception(
    exception_id: UUID,
    payload: CalendarExceptionPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> CalendarException:
    exception = await load_exception(db, current_user.org_id, exception_id)
    changes = payload.model_dump(exclude_unset=True)
    if "unit_id" in changes:
        await validate_unit(db, current_user.org_id, changes["unit_id"])
    for field, value in changes.items():
        setattr(exception, field, value)
    await commit_exception(db)
    await db.refresh(exception)
    return exception


@router.delete("/{exception_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_exception(
    exception_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> None:
    exception = await load_exception(db, current_user.org_id, exception_id)
    await db.delete(exception)
    await db.commit()
