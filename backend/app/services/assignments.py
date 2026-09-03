from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shift_assignment import UserShiftAssignment
from app.models.unit_assignment import UserUnitAssignment
from app.models.user import User


async def lock_user(db: AsyncSession, user: User) -> User:
    locked = await db.scalar(select(User).where(User.id == user.id).with_for_update())
    if locked is None:
        raise RuntimeError("user disappeared while acquiring assignment lock")
    return locked


async def replace_unit_assignment(
    db: AsyncSession,
    user: User,
    unit_id: UUID | None,
    effective_from: date,
    *,
    user_locked: bool = False,
) -> UserUnitAssignment | None:
    if not user_locked:
        await lock_user(db, user)
    rows = list(
        (
            await db.scalars(
                select(UserUnitAssignment)
                .where(UserUnitAssignment.user_id == user.id)
                .order_by(UserUnitAssignment.effective_from)
                .with_for_update()
            )
        ).all()
    )
    containing = next(
        (
            row
            for row in rows
            if row.effective_from <= effective_from
            and (row.effective_to is None or row.effective_to >= effective_from)
        ),
        None,
    )
    next_row = next((row for row in rows if row.effective_from > effective_from), None)
    if containing is not None and containing.effective_from == effective_from:
        if unit_id is None:
            await db.delete(containing)
            return None
        containing.unit_id = unit_id
        return containing
    if containing is not None:
        previous_end = containing.effective_to
        containing.effective_to = effective_from - timedelta(days=1)
        if unit_id is None:
            return None
        replacement_end = previous_end
    else:
        if unit_id is None:
            return None
        replacement_end = (
            next_row.effective_from - timedelta(days=1) if next_row is not None else None
        )
    replacement = UserUnitAssignment(
        org_id=user.org_id,
        user_id=user.id,
        unit_id=unit_id,
        effective_from=effective_from,
        effective_to=replacement_end,
    )
    db.add(replacement)
    return replacement


async def replace_shift_assignment(
    db: AsyncSession,
    user: User,
    shift_id: UUID | None,
    effective_from: date,
    *,
    user_locked: bool = False,
) -> UserShiftAssignment | None:
    if not user_locked:
        await lock_user(db, user)
    rows = list(
        (
            await db.scalars(
                select(UserShiftAssignment)
                .where(UserShiftAssignment.user_id == user.id)
                .order_by(UserShiftAssignment.effective_from)
                .with_for_update()
            )
        ).all()
    )
    containing = next(
        (
            row
            for row in rows
            if row.effective_from <= effective_from
            and (row.effective_to is None or row.effective_to >= effective_from)
        ),
        None,
    )
    next_row = next((row for row in rows if row.effective_from > effective_from), None)
    if containing is not None and containing.effective_from == effective_from:
        if shift_id is None:
            await db.delete(containing)
            return None
        containing.shift_id = shift_id
        return containing
    if containing is not None:
        previous_end = containing.effective_to
        containing.effective_to = effective_from - timedelta(days=1)
        if shift_id is None:
            return None
        replacement_end = previous_end
    else:
        if shift_id is None:
            return None
        replacement_end = (
            next_row.effective_from - timedelta(days=1) if next_row is not None else None
        )
    replacement = UserShiftAssignment(
        org_id=user.org_id,
        user_id=user.id,
        shift_id=shift_id,
        effective_from=effective_from,
        effective_to=replacement_end,
    )
    db.add(replacement)
    return replacement


async def close_assignments_for_deactivation(
    db: AsyncSession,
    user: User,
    deactivation_date: date,
) -> None:
    await lock_user(db, user)
    await db.execute(
        delete(UserUnitAssignment).where(
            UserUnitAssignment.user_id == user.id,
            UserUnitAssignment.effective_from >= deactivation_date,
        )
    )
    unit_assignment = await db.scalar(
        select(UserUnitAssignment)
        .where(
            UserUnitAssignment.user_id == user.id,
            UserUnitAssignment.effective_from < deactivation_date,
            (
                UserUnitAssignment.effective_to.is_(None)
                | (UserUnitAssignment.effective_to >= deactivation_date)
            ),
        )
        .with_for_update()
    )
    if unit_assignment is not None:
        unit_assignment.effective_to = deactivation_date - timedelta(days=1)

    await db.execute(
        delete(UserShiftAssignment).where(
            UserShiftAssignment.user_id == user.id,
            UserShiftAssignment.effective_from >= deactivation_date,
        )
    )
    shift_assignment = await db.scalar(
        select(UserShiftAssignment)
        .where(
            UserShiftAssignment.user_id == user.id,
            UserShiftAssignment.effective_from < deactivation_date,
            (
                UserShiftAssignment.effective_to.is_(None)
                | (UserShiftAssignment.effective_to >= deactivation_date)
            ),
        )
        .with_for_update()
    )
    if shift_assignment is not None:
        shift_assignment.effective_to = deactivation_date - timedelta(days=1)
