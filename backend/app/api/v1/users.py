"""
User management endpoints for FaceLogix.

Provides CRUD operations for users and face enrollment functionality.
"""

from dataclasses import dataclass
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

import anyio
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    clear_manager_scopes,
    ensure_role_assignment_allowed,
    ensure_target_user_mutable,
    ensure_user_in_scope,
    managed_unit_ids,
    require_admin,
    require_operator,
)
from app.api.tenant import load_org, load_user
from app.core.database import get_db
from app.core.identity import UserRole
from app.core.images import ImagePayloadError, decode_image_payload
from app.core.security import hash_password
from app.core.time import local_day_bounds, utc_now
from app.models.face_embedding import FaceEmbedding
from app.models.organizational_unit import ManagerUnitScope, OrganizationalUnit
from app.models.shift import Shift
from app.models.shift_assignment import UserShiftAssignment
from app.models.unit_assignment import UserUnitAssignment
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.settings import canonical_org_settings
from app.schemas.shift import (
    ShiftAssignmentResponse,
    ShiftAssignmentUpdate,
    ShiftSummary,
)
from app.schemas.unit import (
    ManagedUnitsUpdate,
    UnitAssignmentResponse,
    UnitAssignmentUpdate,
    UnitSummary,
)
from app.schemas.user import (
    FaceEnrollmentRequest,
    FaceStatusResponse,
    ResetPasswordRequest,
    UserActivationRequest,
    UserCreate,
    UserEnrollResponse,
    UserImportCommitOptions,
    UserImportConflict,
    UserImportError,
    UserImportPreviewResponse,
    UserImportResult,
    UserResponse,
    UserUpdate,
)
from app.services.assignments import (
    close_assignments_for_deactivation,
    replace_shift_assignment,
    replace_unit_assignment,
)
from app.services.face_client import (
    FaceAnalysis,
    FaceServiceClient,
    FaceServiceError,
    get_face_client,
)
from app.services.face_identity import replace_face_identity
from app.services.user_import import (
    ParsedImportRow,
    ParsedUserImport,
    UserImportPackageError,
    parse_user_import_archive,
)

router = APIRouter(prefix="/users", tags=["Users"])


async def commit_or_conflict(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "USER_CONFLICT", "message": "Email or external ID already exists"},
        ) from exc


async def user_responses(
    db: AsyncSession,
    users: list[User],
    on_date: date,
) -> list[UserResponse]:
    if not users:
        return []
    user_ids = [user.id for user in users]
    unit_rows = (
        await db.execute(
            select(UserUnitAssignment.user_id, OrganizationalUnit)
            .join(OrganizationalUnit, OrganizationalUnit.id == UserUnitAssignment.unit_id)
            .where(
                UserUnitAssignment.user_id.in_(user_ids),
                UserUnitAssignment.effective_from <= on_date,
                (
                    UserUnitAssignment.effective_to.is_(None)
                    | (UserUnitAssignment.effective_to >= on_date)
                ),
            )
        )
    ).all()
    shift_rows = (
        await db.execute(
            select(UserShiftAssignment.user_id, Shift)
            .join(Shift, Shift.id == UserShiftAssignment.shift_id)
            .where(
                UserShiftAssignment.user_id.in_(user_ids),
                UserShiftAssignment.effective_from <= on_date,
                (
                    UserShiftAssignment.effective_to.is_(None)
                    | (UserShiftAssignment.effective_to >= on_date)
                ),
            )
        )
    ).all()
    managed_rows = (
        await db.execute(
            select(ManagerUnitScope.manager_id, OrganizationalUnit)
            .join(OrganizationalUnit, OrganizationalUnit.id == ManagerUnitScope.unit_id)
            .where(ManagerUnitScope.manager_id.in_(user_ids))
            .order_by(OrganizationalUnit.name)
        )
    ).all()
    units = {user_id: UnitSummary.model_validate(unit) for user_id, unit in unit_rows}
    shifts = {user_id: ShiftSummary.model_validate(shift) for user_id, shift in shift_rows}
    managed: dict[UUID, list[UnitSummary]] = {}
    for manager_id, unit in managed_rows:
        managed.setdefault(manager_id, []).append(UnitSummary.model_validate(unit))
    return [
        UserResponse(
            id=user.id,
            org_id=user.org_id,
            email=user.email,
            name=user.name,
            external_id=user.external_id,
            role=UserRole(user.role),
            current_unit=units.get(user.id),
            current_shift=shifts.get(user.id),
            managed_units=managed.get(user.id, []),
            is_active=user.is_active,
            enrolled_at=user.enrolled_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]


async def user_response(db: AsyncSession, user: User, on_date: date) -> UserResponse:
    return (await user_responses(db, [user], on_date))[0]


async def active_unit(db: AsyncSession, org_id: UUID, unit_id: UUID) -> OrganizationalUnit:
    unit = await db.scalar(
        select(OrganizationalUnit).where(
            OrganizationalUnit.id == unit_id,
            OrganizationalUnit.org_id == org_id,
            OrganizationalUnit.is_active.is_(True),
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


async def active_shift(db: AsyncSession, org_id: UUID, shift_id: UUID) -> Shift:
    shift = await db.scalar(
        select(Shift).where(
            Shift.id == shift_id,
            Shift.org_id == org_id,
            Shift.is_active.is_(True),
        )
    )
    if shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


async def sync_legacy_department(
    db: AsyncSession,
    user: User,
    today: date,
) -> None:
    name = await db.scalar(
        select(OrganizationalUnit.name)
        .join(UserUnitAssignment, UserUnitAssignment.unit_id == OrganizationalUnit.id)
        .where(
            UserUnitAssignment.user_id == user.id,
            UserUnitAssignment.effective_from <= today,
            (
                UserUnitAssignment.effective_to.is_(None)
                | (UserUnitAssignment.effective_to >= today)
            ),
        )
    )
    user._legacy_department = name


@dataclass(slots=True)
class UserImportPreviewState:
    response: UserImportPreviewResponse
    conflict_users: dict[int, User]
    unit_ids: dict[int, UUID | None]


async def parse_import_upload(package: UploadFile) -> ParsedUserImport:
    try:
        return await anyio.to_thread.run_sync(parse_user_import_archive, package.file)
    except UserImportPackageError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


async def build_import_preview(
    parsed: ParsedUserImport,
    db: AsyncSession,
    actor: User,
) -> UserImportPreviewState:
    errors = [
        UserImportError(row=error.row, code=error.code, message=error.message, field=error.field)
        for error in parsed.errors
    ]
    units = list(
        (
            await db.scalars(
                select(OrganizationalUnit).where(
                    OrganizationalUnit.org_id == actor.org_id,
                    OrganizationalUnit.is_active.is_(True),
                )
            )
        ).all()
    )
    units_by_name = {unit.name.strip().casefold(): unit for unit in units}
    actor_scope_ids = await managed_unit_ids(db, actor)
    unit_ids: dict[int, UUID | None] = {}
    for row in parsed.rows:
        if row.unit is None:
            unit_ids[row.row] = None
            if actor.role == UserRole.MANAGER.value:
                errors.append(
                    UserImportError(
                        row=row.row,
                        code="UNIT_FORBIDDEN",
                        message="Managers must assign an existing managed unit",
                        field="unit",
                    )
                )
            continue
        unit = units_by_name.get(row.unit.strip().casefold())
        if unit is None:
            errors.append(
                UserImportError(
                    row=row.row,
                    code="UNKNOWN_UNIT",
                    message=f"Unknown active unit: {row.unit}",
                    field="unit",
                )
            )
            continue
        if actor.role == UserRole.MANAGER.value and unit.id not in actor_scope_ids:
            errors.append(
                UserImportError(
                    row=row.row,
                    code="UNIT_FORBIDDEN",
                    message="Unit is outside manager scope",
                    field="unit",
                )
            )
            continue
        unit_ids[row.row] = unit.id
    errored_rows = {error.row for error in errors if error.row is not None}
    candidate_rows = [row for row in parsed.rows if row.row not in errored_rows]
    external_ids = [row.external_id for row in candidate_rows]
    emails = [row.email for row in candidate_rows if row.email is not None]
    existing_users: list[User] = []
    if external_ids:
        identity_filters = [User.external_id.in_(external_ids)]
        if emails:
            identity_filters.append(User.email.in_(emails))
        result = await db.execute(
            select(User).where(User.org_id == actor.org_id, or_(*identity_filters))
        )
        existing_users = list(result.scalars().all())
    scoped_existing_ids: set[UUID] | None = None
    if actor.role == UserRole.MANAGER.value:
        org = await load_org(db, actor.org_id)
        today = local_day_bounds(org.timezone)[0]
        scoped_existing_ids = set(
            (
                await db.scalars(
                    select(UserUnitAssignment.user_id).where(
                        UserUnitAssignment.user_id.in_([user.id for user in existing_users]),
                        UserUnitAssignment.unit_id.in_(actor_scope_ids),
                        UserUnitAssignment.effective_from <= today,
                        (
                            UserUnitAssignment.effective_to.is_(None)
                            | (UserUnitAssignment.effective_to >= today)
                        ),
                    )
                )
            ).all()
        )

    users_by_external_id = {
        user.external_id: user for user in existing_users if user.external_id is not None
    }
    users_by_email = {user.email: user for user in existing_users if user.email is not None}
    conflicts: list[UserImportConflict] = []
    conflict_users: dict[int, User] = {}
    matched_target_rows: dict[UUID, int] = {}
    for row in candidate_rows:
        external_user = users_by_external_id.get(row.external_id)
        email_user = users_by_email.get(row.email) if row.email is not None else None
        if (
            external_user is not None
            and email_user is not None
            and external_user.id != email_user.id
        ):
            errors.append(
                UserImportError(
                    row=row.row,
                    code="IDENTITY_CONFLICT",
                    message="External ID and email belong to different existing people",
                )
            )
            errored_rows.add(row.row)
            continue
        existing_user = external_user or email_user
        if existing_user is None:
            continue
        if scoped_existing_ids is not None and existing_user.id not in scoped_existing_ids:
            errors.append(
                UserImportError(
                    row=row.row,
                    code="UNIT_FORBIDDEN",
                    message="Existing person is outside manager scope",
                    field="unit",
                )
            )
            errored_rows.add(row.row)
            continue
        previous_row = matched_target_rows.get(existing_user.id)
        if previous_row is not None:
            errors.append(
                UserImportError(
                    row=row.row,
                    code="DUPLICATE_TARGET",
                    message=f"Existing person is already matched by row {previous_row}",
                )
            )
            errored_rows.add(row.row)
            continue
        matched_target_rows[existing_user.id] = row.row
        allowed_actions: list[Literal["skip", "replace"]] = ["skip"]
        if existing_user.role == UserRole.MEMBER.value:
            allowed_actions.append("replace")
        conflicts.append(
            UserImportConflict(
                row=row.row,
                external_id=row.external_id,
                email=row.email,
                name=row.name,
                existing_user_id=existing_user.id,
                existing_name=existing_user.name,
                allowed_actions=allowed_actions,
            )
        )
        conflict_users[row.row] = existing_user

    conflict_rows = {conflict.row for conflict in conflicts}
    ready_count = sum(
        row.row not in errored_rows and row.row not in conflict_rows for row in parsed.rows
    )
    response = UserImportPreviewResponse(
        package_sha256=parsed.package_sha256,
        total_rows=parsed.total_rows,
        ready_count=ready_count,
        conflict_count=len(conflicts),
        error_count=len(errors),
        conflicts=conflicts,
        errors=errors,
    )
    return UserImportPreviewState(
        response=response,
        conflict_users=conflict_users,
        unit_ids=unit_ids,
    )


def resolve_import_rows(
    parsed: ParsedUserImport,
    preview: UserImportPreviewState,
    options: UserImportCommitOptions,
) -> tuple[list[ParsedImportRow], dict[int, UUID], int]:
    if options.package_sha256 != parsed.package_sha256:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PACKAGE_CHANGED",
                "message": "The selected package changed after preview",
            },
        )
    if preview.response.errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "IMPORT_VALIDATION_FAILED",
                "message": "Resolve package errors before importing",
                "details": [error.model_dump(mode="json") for error in preview.response.errors],
            },
        )

    resolution_map = {resolution.row: resolution.action for resolution in options.resolutions}
    if len(resolution_map) != len(options.resolutions):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_RESOLUTIONS",
                "message": "Each conflict row must have exactly one resolution",
            },
        )
    expected_rows = set(preview.conflict_users)
    if set(resolution_map) != expected_rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_RESOLUTIONS",
                "message": "Choose skip or replace for every conflict",
            },
        )

    allowed_by_row = {
        conflict.row: set(conflict.allowed_actions) for conflict in preview.response.conflicts
    }
    replacement_ids: dict[int, UUID] = {}
    skipped_count = 0
    active_rows: list[ParsedImportRow] = []
    for row in parsed.rows:
        action = resolution_map.get(row.row)
        if action is None:
            active_rows.append(row)
            continue
        if action not in allowed_by_row[row.row]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "IMPORT_ACTION_FORBIDDEN",
                    "message": f"Replace is not allowed for conflict on row {row.row}",
                },
            )
        if action == "skip":
            skipped_count += 1
            continue
        replacement_ids[row.row] = preview.conflict_users[row.row].id
        active_rows.append(row)
    return active_rows, replacement_ids, skipped_count


def parse_commit_options(value: str) -> UserImportCommitOptions:
    try:
        return UserImportCommitOptions.model_validate_json(value)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_IMPORT_OPTIONS",
                "message": "Import conflict resolutions are invalid",
                "details": exc.errors(include_url=False),
            },
        ) from exc


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    search: Annotated[str | None, Query(description="Search by name or email")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by active status")] = None,
    unit_id: Annotated[UUID | None, Query(description="Filter by unit")] = None,
    shift_id: Annotated[UUID | None, Query(description="Filter by shift")] = None,
) -> PaginatedResponse[UserResponse]:
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    unit_assignment = select(UserUnitAssignment.user_id).where(
        UserUnitAssignment.org_id == current_user.org_id,
        UserUnitAssignment.effective_from <= today,
        (
            UserUnitAssignment.effective_to.is_(None)
            | (UserUnitAssignment.effective_to >= today)
        ),
    )
    if current_user.role == UserRole.MANAGER.value:
        scope_ids = await managed_unit_ids(db, current_user)
        if unit_id is not None:
            scope_ids &= {unit_id}
        unit_assignment = unit_assignment.where(UserUnitAssignment.unit_id.in_(scope_ids))
    elif unit_id is not None:
        unit_assignment = unit_assignment.where(UserUnitAssignment.unit_id == unit_id)

    conditions = [User.org_id == current_user.org_id]
    if current_user.role == UserRole.MANAGER.value or unit_id is not None:
        conditions.append(User.id.in_(unit_assignment))
    if shift_id is not None:
        shift_users = select(UserShiftAssignment.user_id).where(
            UserShiftAssignment.org_id == current_user.org_id,
            UserShiftAssignment.shift_id == shift_id,
            UserShiftAssignment.effective_from <= today,
            (
                UserShiftAssignment.effective_to.is_(None)
                | (UserShiftAssignment.effective_to >= today)
            ),
        )
        conditions.append(User.id.in_(shift_users))
    if is_active is not None:
        conditions.append(User.is_active == is_active)
    if search:
        conditions.append(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.external_id.ilike(f"%{search}%"),
            )
        )
    total = await db.scalar(select(func.count(User.id)).where(*conditions)) or 0
    users = list(
        (
            await db.scalars(
                select(User)
                .where(*conditions)
                .order_by(User.name)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return PaginatedResponse(
        items=await user_responses(db, users, today),
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 1,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    ensure_role_assignment_allowed(current_user, user_data.role.value)
    if current_user.role == UserRole.MANAGER.value and user_data.unit_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNIT_FORBIDDEN", "message": "Managers must assign a managed unit"},
        )
    unit = (
        await active_unit(db, current_user.org_id, user_data.unit_id)
        if user_data.unit_id is not None
        else None
    )
    if (
        unit is not None
        and current_user.role == UserRole.MANAGER.value
        and unit.id not in await managed_unit_ids(db, current_user)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNIT_FORBIDDEN", "message": "Unit is outside manager scope"},
        )
    shift = (
        await active_shift(db, current_user.org_id, user_data.shift_id)
        if user_data.shift_id is not None
        else None
    )
    if user_data.email:
        existing = await db.scalar(
            select(User).where(
                User.org_id == current_user.org_id,
                User.email == user_data.email,
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "USER_CONFLICT", "message": "Email already exists"},
            )
    if user_data.external_id:
        existing = await db.scalar(
            select(User).where(
                User.org_id == current_user.org_id,
                User.external_id == user_data.external_id,
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "USER_CONFLICT", "message": "External ID already exists"},
            )
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    user = User(
        org_id=current_user.org_id,
        name=user_data.name,
        email=user_data.email,
        external_id=user_data.external_id,
        _legacy_department=unit.name if unit is not None else None,
        role=user_data.role.value,
        password_hash=hash_password(user_data.password) if user_data.password else None,
    )
    db.add(user)
    await db.flush()
    if unit is not None:
        await replace_unit_assignment(db, user, unit.id, today)
    if shift is not None:
        await replace_shift_assignment(db, user, shift.id, today)
    await commit_or_conflict(db)
    await db.refresh(user)
    return await user_response(db, user, today)


@router.post("/import/preview", response_model=UserImportPreviewResponse)
async def preview_user_import(
    package: Annotated[
        UploadFile, File(description="ZIP package containing people.csv and face images")
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserImportPreviewResponse:
    parsed = await parse_import_upload(package)
    preview = await build_import_preview(parsed, db, current_user)
    return preview.response


@router.post("/import", response_model=UserImportResult)
async def import_users(
    package: Annotated[
        UploadFile, File(description="ZIP package containing people.csv and face images")
    ],
    options_json: Annotated[str, Form(alias="options")],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    face_client: Annotated[FaceServiceClient, Depends(get_face_client)],
) -> UserImportResult:
    parsed = await parse_import_upload(package)
    options = parse_commit_options(options_json)
    initial_preview = await build_import_preview(parsed, db, current_user)
    active_rows, initial_replacements, skipped_count = resolve_import_rows(
        parsed, initial_preview, options
    )
    await db.commit()

    analyses_by_row: dict[int, list[FaceAnalysis]] = {}
    for row in active_rows:
        analyses: list[FaceAnalysis] = []
        for image_path in row.image_paths:
            try:
                analyses.append(await face_client.analyze(parsed.images[image_path]))
            except FaceServiceError as exc:
                import_status = (
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                    if exc.code in {"INVALID_IMAGE", "NO_FACE", "MULTIPLE_FACES", "LOW_QUALITY"}
                    else exc.status_code
                )
                raise HTTPException(
                    status_code=import_status,
                    detail={
                        "code": exc.code,
                        "message": f"Face validation failed on CSV row {row.row}",
                        "details": {
                            "row": row.row,
                            "image": image_path,
                            "face_code": exc.code,
                        },
                    },
                ) from exc
        analyses_by_row[row.row] = analyses

    final_preview = await build_import_preview(parsed, db, current_user)
    final_rows, final_replacements, final_skipped_count = resolve_import_rows(
        parsed, final_preview, options
    )
    if (
        [row.row for row in final_rows] != [row.row for row in active_rows]
        or final_replacements != initial_replacements
        or final_skipped_count != skipped_count
    ):
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IMPORT_CONFLICT_CHANGED",
                "message": "Person conflicts changed during import; preview the package again",
            },
        )

    org = await load_org(db, current_user.org_id)
    policy = canonical_org_settings(org.settings)
    today = local_day_bounds(org.timezone)[0]
    resolved_unit_ids = {
        unit_id for unit_id in final_preview.unit_ids.values() if unit_id is not None
    }
    import_units = {
        unit.id: unit
        for unit in (
            await db.scalars(
                select(OrganizationalUnit).where(
                    OrganizationalUnit.id.in_(resolved_unit_ids)
                )
            )
        ).all()
    }
    if policy.require_liveness:
        for row in final_rows:
            for image_path, analysis in zip(row.image_paths, analyses_by_row[row.row], strict=True):
                if analysis.pad_live_score < policy.liveness_threshold:
                    await db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail={
                            "code": "SPOOF_DETECTED",
                            "message": f"Liveness verification failed on CSV row {row.row}",
                            "details": {"row": row.row, "image": image_path},
                        },
                    )

    if not final_rows:
        await db.rollback()
        return UserImportResult(
            total_rows=parsed.total_rows,
            created_count=0,
            replaced_count=0,
            skipped_count=skipped_count,
            embeddings_count=0,
        )

    users_by_row: dict[int, User] = {}
    enrolled_at = utc_now()
    for row in final_rows:
        replacement_user = final_preview.conflict_users.get(row.row)
        if replacement_user is None:
            user = User(
                org_id=current_user.org_id,
                role=UserRole.MEMBER.value,
                is_active=True,
            )
            db.add(user)
        else:
            ensure_target_user_mutable(current_user, replacement_user)
            await ensure_user_in_scope(db, current_user, replacement_user)
            if replacement_user.role != UserRole.MEMBER.value:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "IMPORT_ACTION_FORBIDDEN",
                        "message": f"CSV row {row.row} cannot replace an elevated user",
                    },
                )
            user = replacement_user
        user.external_id = row.external_id
        user.name = row.name
        user.email = row.email
        unit_id = final_preview.unit_ids[row.row]
        user._legacy_department = (
            import_units[unit_id].name if unit_id is not None else None
        )
        user.enrolled_at = enrolled_at
        users_by_row[row.row] = user

    try:
        await db.flush()
        for row in final_rows:
            await replace_unit_assignment(
                db,
                users_by_row[row.row],
                final_preview.unit_ids[row.row],
                today,
            )
        await db.flush()
        embeddings_count = 0
        for row in final_rows:
            analyses = analyses_by_row[row.row]
            await replace_face_identity(
                db,
                org_id=org.id,
                user_id=users_by_row[row.row].id,
                analyses=analyses,
                collision_threshold=policy.face_match_threshold,
            )
            embeddings_count += len(analyses)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IMPORT_CONFLICT_CHANGED",
                "message": "A person changed during import; preview the package again",
            },
        ) from exc

    return UserImportResult(
        total_rows=parsed.total_rows,
        created_count=len(final_rows) - len(final_replacements),
        replaced_count=len(final_replacements),
        skipped_count=skipped_count,
        embeddings_count=embeddings_count,
    )


@router.put("/{manager_id}/managed-units", response_model=UserResponse)
async def replace_managed_units(
    manager_id: UUID,
    payload: ManagedUnitsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
) -> UserResponse:
    manager = await load_user(db, current_user.org_id, manager_id)
    if manager.role != UserRole.MANAGER.value:
        raise HTTPException(status_code=422, detail="Target user must be a manager")
    units = list(
        (
            await db.scalars(
                select(OrganizationalUnit).where(
                    OrganizationalUnit.org_id == current_user.org_id,
                    OrganizationalUnit.id.in_(payload.unit_ids),
                )
            )
        ).all()
    )
    if len(units) != len(payload.unit_ids):
        raise HTTPException(status_code=404, detail="Unit not found")
    await db.execute(
        delete(ManagerUnitScope).where(ManagerUnitScope.manager_id == manager.id)
    )
    db.add_all(
        [ManagerUnitScope(manager_id=manager.id, unit_id=unit_id) for unit_id in payload.unit_ids]
    )
    await db.commit()
    org = await load_org(db, current_user.org_id)
    return await user_response(db, manager, local_day_bounds(org.timezone)[0])


@router.get(
    "/{user_id}/unit-assignments",
    response_model=list[UnitAssignmentResponse],
)
async def list_unit_assignments(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> list[UnitAssignmentResponse]:
    user = await load_user(db, current_user.org_id, user_id)
    await ensure_user_in_scope(db, current_user, user)
    rows = (
        await db.execute(
            select(UserUnitAssignment, OrganizationalUnit)
            .join(OrganizationalUnit, OrganizationalUnit.id == UserUnitAssignment.unit_id)
            .where(UserUnitAssignment.user_id == user.id)
            .order_by(UserUnitAssignment.effective_from)
        )
    ).all()
    return [
        UnitAssignmentResponse(
            id=assignment.id,
            user_id=user.id,
            unit=UnitSummary.model_validate(unit),
            effective_from=assignment.effective_from,
            effective_to=assignment.effective_to,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
        )
        for assignment, unit in rows
    ]


@router.put("/{user_id}/unit-assignment", response_model=UserResponse)
async def put_unit_assignment(
    user_id: UUID,
    payload: UnitAssignmentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    if current_user.role == UserRole.MANAGER.value:
        if payload.effective_from < today:
            raise HTTPException(status_code=403, detail="Managers cannot backdate assignments")
        await ensure_user_in_scope(db, current_user, user, payload.effective_from)
    unit = (
        await active_unit(db, current_user.org_id, payload.unit_id)
        if payload.unit_id is not None
        else None
    )
    if (
        unit is not None
        and current_user.role == UserRole.MANAGER.value
        and unit.id not in await managed_unit_ids(db, current_user)
    ):
        raise HTTPException(status_code=403, detail="Unit is outside manager scope")
    await replace_unit_assignment(
        db,
        user,
        unit.id if unit is not None else None,
        payload.effective_from,
    )
    await db.flush()
    await sync_legacy_department(db, user, today)
    await db.commit()
    return await user_response(db, user, today)


@router.get(
    "/{user_id}/shift-assignments",
    response_model=list[ShiftAssignmentResponse],
)
async def list_shift_assignments(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> list[ShiftAssignmentResponse]:
    user = await load_user(db, current_user.org_id, user_id)
    await ensure_user_in_scope(db, current_user, user)
    rows = (
        await db.execute(
            select(UserShiftAssignment, Shift)
            .join(Shift, Shift.id == UserShiftAssignment.shift_id)
            .where(UserShiftAssignment.user_id == user.id)
            .order_by(UserShiftAssignment.effective_from)
        )
    ).all()
    return [
        ShiftAssignmentResponse(
            id=assignment.id,
            user_id=user.id,
            shift=ShiftSummary.model_validate(shift),
            effective_from=assignment.effective_from,
            effective_to=assignment.effective_to,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
        )
        for assignment, shift in rows
    ]


@router.put("/{user_id}/shift-assignment", response_model=UserResponse)
async def put_shift_assignment(
    user_id: UUID,
    payload: ShiftAssignmentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    if current_user.role == UserRole.MANAGER.value:
        if payload.effective_from < today:
            raise HTTPException(status_code=403, detail="Managers cannot backdate assignments")
        await ensure_user_in_scope(db, current_user, user, payload.effective_from)
    shift = (
        await active_shift(db, current_user.org_id, payload.shift_id)
        if payload.shift_id is not None
        else None
    )
    await replace_shift_assignment(
        db,
        user,
        shift.id if shift is not None else None,
        payload.effective_from,
    )
    await db.commit()
    return await user_response(db, user, today)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    """
    Get a user by ID.

    Admin only.
    """
    user = await load_user(db, current_user.org_id, user_id)
    await ensure_user_in_scope(db, current_user, user)
    org = await load_org(db, current_user.org_id)
    return await user_response(db, user, local_day_bounds(org.timezone)[0])


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    """
    Update user details.

    Admin only.
    """
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)
    await ensure_user_in_scope(db, current_user, user)
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    was_active = user.is_active

    # Update fields if provided
    update_data = user_data.model_dump(exclude_unset=True)
    if not was_active and update_data.get("is_active") is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the activation endpoint to assign a valid unit",
        )
    if "role" in update_data and update_data["role"] is not None:
        role = update_data["role"]
        ensure_role_assignment_allowed(current_user, role.value)
        update_data["role"] = role.value

    # Check email uniqueness if being updated
    if update_data.get("email"):
        existing = await db.execute(
            select(User).where(
                User.org_id == current_user.org_id,
                User.email == update_data["email"],
                User.id != user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "USER_CONFLICT", "message": "Email already exists"},
            )

    # Check external_id uniqueness if being updated
    if update_data.get("external_id"):
        existing = await db.execute(
            select(User).where(
                User.org_id == current_user.org_id,
                User.external_id == update_data["external_id"],
                User.id != user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "USER_CONFLICT", "message": "External ID already exists"},
            )

    was_manager = user.role == UserRole.MANAGER.value
    for field, value in update_data.items():
        setattr(user, field, value)
    if (
        was_manager
        and (
            update_data.get("role") not in (None, UserRole.MANAGER.value)
            or update_data.get("is_active") is False
        )
    ):
        await clear_manager_scopes(db, user)
    if was_active and update_data.get("is_active") is False:
        await close_assignments_for_deactivation(db, user, today)
        await sync_legacy_department(db, user, today)

    await commit_or_conflict(db)
    await db.refresh(user)

    return await user_response(db, user, today)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> Response:
    """
    Soft delete a user (sets is_active=False).

    Admin only.
    """
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)
    await ensure_user_in_scope(db, current_user, user)
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]

    # Prevent deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    # Soft delete
    user.is_active = False
    if user.role == UserRole.MANAGER.value:
        await clear_manager_scopes(db, user)
    await close_assignments_for_deactivation(db, user, today)
    await sync_legacy_department(db, user, today)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/enroll-face", response_model=UserEnrollResponse)
async def enroll_user_face(
    user_id: UUID,
    request: FaceEnrollmentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
    face_client: Annotated[FaceServiceClient, Depends(get_face_client)],
) -> UserEnrollResponse:
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)
    await ensure_user_in_scope(db, current_user, user)
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Cannot enroll inactive user")

    org = await load_org(db, current_user.org_id)
    policy = canonical_org_settings(org.settings)

    try:
        images = [decode_image_payload(image) for image in request.images]
    except ImagePayloadError as exc:
        enrollment_status = (
            status.HTTP_422_UNPROCESSABLE_CONTENT
            if exc.code == "INVALID_IMAGE"
            else exc.status_code
        )
        raise HTTPException(
            status_code=enrollment_status,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    analyses = []
    for image in images:
        try:
            analysis = await face_client.analyze(image)
        except FaceServiceError as exc:
            enrollment_status = (
                status.HTTP_422_UNPROCESSABLE_CONTENT
                if exc.code
                in {
                    "INVALID_IMAGE",
                    "NO_FACE",
                    "MULTIPLE_FACES",
                    "LOW_QUALITY",
                }
                else exc.status_code
            )
            raise HTTPException(
                status_code=enrollment_status,
                detail={"code": exc.code, "message": exc.message},
            ) from exc
        if policy.require_liveness and analysis.pad_live_score < policy.liveness_threshold:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "SPOOF_DETECTED",
                    "message": "Liveness verification failed",
                },
            )
        analyses.append(analysis)

    await replace_face_identity(
        db,
        org_id=org.id,
        user_id=user.id,
        analyses=analyses,
        collision_threshold=policy.face_match_threshold,
    )
    user.enrolled_at = utc_now()
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return UserEnrollResponse(
        user_id=user.id,
        embeddings_count=len(analyses),
        enrolled_at=user.enrolled_at,
    )


@router.get("/{user_id}/face-status", response_model=FaceStatusResponse)
async def get_face_status(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> FaceStatusResponse:
    """
    Get face enrollment status for a user.

    Returns whether the user has face embeddings and the count.
    Admin only.
    """
    user = await load_user(db, current_user.org_id, user_id)
    await ensure_user_in_scope(db, current_user, user)

    # Count embeddings
    result = await db.execute(
        select(func.count(FaceEmbedding.id)).where(FaceEmbedding.user_id == user_id)
    )
    embeddings_count = result.scalar() or 0

    return FaceStatusResponse(
        has_face=embeddings_count > 0,
        embeddings_count=embeddings_count,
        enrolled_at=user.enrolled_at,
    )


@router.delete("/{user_id}/face-embeddings", status_code=status.HTTP_204_NO_CONTENT)
async def delete_face_embeddings(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> Response:
    """
    Delete all face embeddings for a user.

    Admin only.
    """
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)
    await ensure_user_in_scope(db, current_user, user)

    # Delete all embeddings for this user

    await db.execute(delete(FaceEmbedding).where(FaceEmbedding.user_id == user_id))

    # Clear enrollment timestamp
    user.enrolled_at = None
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    request: UserActivationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    unit = await active_unit(db, current_user.org_id, request.unit_id)
    if current_user.role == UserRole.MANAGER.value:
        scope_ids = await managed_unit_ids(db, current_user)
        last_unit_id = await db.scalar(
            select(UserUnitAssignment.unit_id)
            .where(UserUnitAssignment.user_id == user.id)
            .order_by(UserUnitAssignment.effective_from.desc())
            .limit(1)
        )
        if last_unit_id not in scope_ids or unit.id not in scope_ids:
            raise HTTPException(status_code=403, detail="Unit is outside manager scope")
    shift = (
        await active_shift(db, current_user.org_id, request.shift_id)
        if request.shift_id is not None
        else None
    )
    user.is_active = True
    await replace_unit_assignment(db, user, unit.id, today)
    if shift is not None:
        await replace_shift_assignment(db, user, shift.id, today)
    await db.flush()
    await sync_legacy_department(db, user, today)
    await db.commit()
    await db.refresh(user)
    return await user_response(db, user, today)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)
    await ensure_user_in_scope(db, current_user, user)
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )
    org = await load_org(db, current_user.org_id)
    today = local_day_bounds(org.timezone)[0]
    user.is_active = False
    if user.role == UserRole.MANAGER.value:
        await clear_manager_scopes(db, user)
    await close_assignments_for_deactivation(db, user, today)
    await db.flush()
    await sync_legacy_department(db, user, today)
    await db.commit()
    await db.refresh(user)
    return await user_response(db, user, today)


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: UUID,
    request: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> dict[str, str]:
    """
    Reset a user's password (admin action).

    Admin only.
    """
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)
    await ensure_user_in_scope(db, current_user, user)

    user.password_hash = hash_password(request.new_password)
    await db.commit()

    return {"message": "Password reset successfully"}
