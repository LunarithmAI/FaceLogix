from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import managed_unit_ids, require_admin, require_operator
from app.api.tenant import load_org
from app.core.database import get_db
from app.core.identity import UserRole
from app.core.time import local_day_bounds
from app.models.attendance_log import AttendanceLog
from app.models.organizational_unit import OrganizationalUnit
from app.models.shift import Shift
from app.models.shift_assignment import UserShiftAssignment
from app.models.unit_assignment import UserUnitAssignment
from app.models.user import User
from app.schemas.shift import (
    ShiftCreate,
    ShiftPatch,
    ShiftResponse,
    UnitShiftAssignmentResponse,
    UnitShiftAssignmentUpdate,
)
from app.services.assignments import replace_shift_assignment

router = APIRouter(tags=["Shifts"])
_TIMING_FIELDS = {
    "start_time",
    "end_time",
    "late_grace_minutes",
    "early_departure_grace_minutes",
    "scheduled_weekdays",
}


async def load_shift(db: AsyncSession, org_id: UUID, shift_id: UUID) -> Shift:
    shift = await db.scalar(select(Shift).where(Shift.id == shift_id, Shift.org_id == org_id))
    if shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


async def commit_shift(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SHIFT_CONFLICT", "message": "Shift data conflicts with existing records"},
        ) from exc


@router.get("/shifts", response_model=list[ShiftResponse])
async def list_shifts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    include_inactive: bool = False,
) -> list[Shift]:
    conditions = [Shift.org_id == current_user.org_id]
    if not include_inactive:
        conditions.append(Shift.is_active.is_(True))
    return list((await db.scalars(select(Shift).where(*conditions).order_by(Shift.name))).all())


@router.post("/shifts", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
async def create_shift(
    payload: ShiftCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> Shift:
    shift = Shift(org_id=current_user.org_id, **payload.model_dump())
    db.add(shift)
    await commit_shift(db)
    await db.refresh(shift)
    return shift


@router.patch("/shifts/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    shift_id: UUID,
    payload: ShiftPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> Shift:
    shift = await load_shift(db, current_user.org_id, shift_id)
    changes = payload.model_dump(exclude_unset=True)
    start_time = changes.get("start_time", shift.start_time)
    end_time = changes.get("end_time", shift.end_time)
    if start_time == end_time:
        raise HTTPException(status_code=422, detail="Shift start and end times must differ")
    in_use = await db.scalar(
        select(
            or_(
                select(func.count())
                .select_from(UserShiftAssignment)
                .where(UserShiftAssignment.shift_id == shift.id)
                .scalar_subquery()
                > 0,
                select(func.count())
                .select_from(AttendanceLog)
                .where(AttendanceLog.shift_id == shift.id)
                .scalar_subquery()
                > 0,
            )
        )
    )
    if in_use and _TIMING_FIELDS.intersection(changes):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SHIFT_TIMING_IN_USE", "message": "In-use shift timing cannot be changed"},
        )
    if changes.get("is_active") is False and shift.is_active:
        org = await load_org(db, current_user.org_id)
        today = local_day_bounds(org.timezone)[0]
        active_assignments = await db.scalar(
            select(func.count()).select_from(UserShiftAssignment).where(
                UserShiftAssignment.shift_id == shift.id,
                or_(
                    UserShiftAssignment.effective_to.is_(None),
                    UserShiftAssignment.effective_to >= today,
                ),
            )
        )
        if active_assignments:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "SHIFT_IN_USE", "message": "Shift has active or future assignments"},
            )
    for field, value in changes.items():
        setattr(shift, field, value)
    await commit_shift(db)
    await db.refresh(shift)
    return shift


@router.put(
    "/units/{unit_id}/shift-assignment",
    response_model=UnitShiftAssignmentResponse,
)
async def assign_unit_shift(
    unit_id: UUID,
    payload: UnitShiftAssignmentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UnitShiftAssignmentResponse:
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    scope_ids = await managed_unit_ids(db, current_user)
    if current_user.role == UserRole.MANAGER.value:
        if unit_id not in scope_ids:
            raise HTTPException(status_code=403, detail="Unit is outside managed scope")
        if payload.effective_from < today:
            raise HTTPException(status_code=403, detail="Managers cannot backdate assignments")
    unit = await db.scalar(
        select(OrganizationalUnit).where(
            OrganizationalUnit.id == unit_id,
            OrganizationalUnit.org_id == current_user.org_id,
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    if payload.shift_id is not None:
        shift = await load_shift(db, current_user.org_id, payload.shift_id)
        if not shift.is_active:
            raise HTTPException(status_code=409, detail="Shift is archived")
    user_ids = list(
        (
            await db.scalars(
                select(UserUnitAssignment.user_id)
                .where(
                    UserUnitAssignment.org_id == current_user.org_id,
                    UserUnitAssignment.unit_id == unit_id,
                    UserUnitAssignment.effective_from <= payload.effective_from,
                    or_(
                        UserUnitAssignment.effective_to.is_(None),
                        UserUnitAssignment.effective_to >= payload.effective_from,
                    ),
                )
                .order_by(UserUnitAssignment.user_id)
            )
        ).all()
    )
    users = list(
        (
            await db.scalars(
                select(User)
                .where(User.id.in_(user_ids))
                .order_by(User.id)
                .with_for_update()
            )
        ).all()
    )
    for user in users:
        await replace_shift_assignment(
            db,
            user,
            payload.shift_id,
            payload.effective_from,
            user_locked=True,
        )
    await commit_shift(db)
    return UnitShiftAssignmentResponse(
        unit_id=unit_id,
        shift_id=payload.shift_id,
        effective_from=payload.effective_from,
        users_updated=len(users),
    )
