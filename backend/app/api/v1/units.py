from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import managed_unit_ids, require_admin, require_operator
from app.core.database import get_db
from app.core.identity import UserRole
from app.core.time import local_day_bounds
from app.models.org import Org
from app.models.organizational_unit import ManagerUnitScope, OrganizationalUnit
from app.models.unit_assignment import UserUnitAssignment
from app.models.user import User
from app.schemas.unit import UnitCreate, UnitPatch, UnitResponse

router = APIRouter(prefix="/units", tags=["Units"])


def unit_response(unit: OrganizationalUnit) -> UnitResponse:
    return UnitResponse.model_validate(unit)


async def load_unit(db: AsyncSession, org_id: UUID, unit_id: UUID) -> OrganizationalUnit:
    unit = await db.scalar(
        select(OrganizationalUnit).where(
            OrganizationalUnit.id == unit_id,
            OrganizationalUnit.org_id == org_id,
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


async def commit_unit(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "UNIT_CONFLICT", "message": "A unit with this name already exists"},
        ) from exc


@router.get("", response_model=list[UnitResponse])
async def list_units(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> list[UnitResponse]:
    query = select(OrganizationalUnit).where(OrganizationalUnit.org_id == current_user.org_id)
    if current_user.role == UserRole.MANAGER.value:
        query = query.where(OrganizationalUnit.id.in_(await managed_unit_ids(db, current_user)))
    units = (await db.scalars(query.order_by(OrganizationalUnit.name))).all()
    return [unit_response(unit) for unit in units]


@router.post("", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(
    payload: UnitCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> UnitResponse:
    unit = OrganizationalUnit(org_id=current_user.org_id, name=payload.name, kind=payload.kind)
    db.add(unit)
    await commit_unit(db)
    await db.refresh(unit)
    return unit_response(unit)


@router.patch("/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: UUID,
    payload: UnitPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> UnitResponse:
    unit = await load_unit(db, current_user.org_id, unit_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("kind") is not None and changes["kind"] != unit.kind:
        assigned = await db.scalar(
            select(func.count(UserUnitAssignment.id)).where(
                UserUnitAssignment.unit_id == unit.id
            )
        )
        if assigned:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "UNIT_IN_USE", "message": "Assigned unit kind cannot change"},
            )
    if changes.get("is_active") is False and unit.is_active:
        timezone_name = await db.scalar(select(Org.timezone).where(Org.id == unit.org_id))
        if timezone_name is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        today = local_day_bounds(timezone_name)[0]
        assignment_count = await db.scalar(
            select(func.count(UserUnitAssignment.id)).where(
                UserUnitAssignment.unit_id == unit.id,
                (
                    UserUnitAssignment.effective_to.is_(None)
                    | (UserUnitAssignment.effective_to >= today)
                ),
            )
        )
        manager_count = await db.scalar(
            select(func.count()).select_from(ManagerUnitScope).where(
                ManagerUnitScope.unit_id == unit.id
            )
        )
        if assignment_count or manager_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "UNIT_IN_USE", "message": "Unit has active assignments"},
            )
    renamed = "name" in changes and changes["name"] != unit.name
    for field, value in changes.items():
        setattr(unit, field, value)
    if renamed:
        timezone_name = await db.scalar(select(Org.timezone).where(Org.id == unit.org_id))
        if timezone_name is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        today = local_day_bounds(timezone_name)[0]
        current_users = select(UserUnitAssignment.user_id).where(
            UserUnitAssignment.unit_id == unit.id,
            UserUnitAssignment.effective_from <= today,
            (
                UserUnitAssignment.effective_to.is_(None)
                | (UserUnitAssignment.effective_to >= today)
            ),
        )
        await db.execute(
            update(User)
            .where(User.id.in_(current_users))
            .values({User._legacy_department: unit.name})
        )
    await commit_unit(db)
    await db.refresh(unit)
    return unit_response(unit)
