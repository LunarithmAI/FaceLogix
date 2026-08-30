"""
User management endpoints for FaceLogix.

Provides CRUD operations for users and face enrollment functionality.
"""

from dataclasses import dataclass
from typing import Annotated
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
    ensure_role_assignment_allowed,
    ensure_target_user_mutable,
    require_operator,
)
from app.api.tenant import load_org, load_user
from app.core.database import get_db
from app.core.identity import UserRole
from app.core.images import ImagePayloadError, decode_image_payload
from app.core.security import hash_password
from app.core.time import utc_now
from app.models.face_embedding import FaceEmbedding
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.settings import canonical_org_settings
from app.schemas.user import (
    FaceEnrollmentRequest,
    FaceStatusResponse,
    ResetPasswordRequest,
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
from app.services.face_client import (
    FaceAnalysis,
    FaceServiceClient,
    FaceServiceError,
    get_face_client,
)
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


@dataclass(slots=True)
class UserImportPreviewState:
    response: UserImportPreviewResponse
    conflict_users: dict[int, User]


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
    org_id: UUID,
) -> UserImportPreviewState:
    errors = [
        UserImportError(row=error.row, code=error.code, message=error.message, field=error.field)
        for error in parsed.errors
    ]
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
            select(User).where(User.org_id == org_id, or_(*identity_filters))
        )
        existing_users = list(result.scalars().all())

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
        allowed_actions: list[str] = ["skip"]
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
    return UserImportPreviewState(response=response, conflict_users=conflict_users)


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
    department: Annotated[str | None, Query(description="Filter by department")] = None,
) -> PaginatedResponse[UserResponse]:
    """
    List all users in the organization with pagination and filtering.

    Admin only.
    """
    # Base query
    query = select(User).where(User.org_id == current_user.org_id)
    count_query = select(func.count(User.id)).where(User.org_id == current_user.org_id)

    # Apply filters
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    if department:
        query = query.where(User.department == department)
        count_query = count_query.where(User.department == department)

    if search:
        search_filter = or_(
            User.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            User.external_id.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    total = await db.scalar(count_query) or 0

    pages = (total + page_size - 1) // page_size if total else 1
    offset = (page - 1) * page_size

    # Execute query with pagination
    query = query.order_by(User.name).offset(offset).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return PaginatedResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    """
    Create a new user in the organization.

    Admin only.
    """
    ensure_role_assignment_allowed(current_user, user_data.role.value)
    # Check if email already exists in org
    if user_data.email:
        existing = await db.execute(
            select(User).where(
                User.org_id == current_user.org_id,
                User.email == user_data.email,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "USER_CONFLICT", "message": "Email already exists"},
            )

    # Check if external_id already exists in org
    if user_data.external_id:
        existing = await db.execute(
            select(User).where(
                User.org_id == current_user.org_id,
                User.external_id == user_data.external_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "USER_CONFLICT", "message": "External ID already exists"},
            )

    # Hash password if provided
    password_hash = None
    if user_data.password:
        password_hash = hash_password(user_data.password)

    # Create user
    user = User(
        org_id=current_user.org_id,
        name=user_data.name,
        email=user_data.email,
        external_id=user_data.external_id,
        department=user_data.department,
        role=user_data.role.value,
        password_hash=password_hash,
    )

    db.add(user)
    await commit_or_conflict(db)
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/import/preview", response_model=UserImportPreviewResponse)
async def preview_user_import(
    package: Annotated[
        UploadFile, File(description="ZIP package containing people.csv and face images")
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserImportPreviewResponse:
    parsed = await parse_import_upload(package)
    preview = await build_import_preview(parsed, db, current_user.org_id)
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
    initial_preview = await build_import_preview(parsed, db, current_user.org_id)
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

    final_preview = await build_import_preview(parsed, db, current_user.org_id)
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
        user.department = row.department
        user.enrolled_at = enrolled_at
        users_by_row[row.row] = user

    try:
        await db.flush()
        replacement_user_ids = list(final_replacements.values())
        if replacement_user_ids:
            await db.execute(
                delete(FaceEmbedding).where(FaceEmbedding.user_id.in_(replacement_user_ids))
            )
        embeddings_count = 0
        for row in final_rows:
            user = users_by_row[row.row]
            for index, analysis in enumerate(analyses_by_row[row.row]):
                db.add(
                    FaceEmbedding(
                        user_id=user.id,
                        embedding=analysis.embedding,
                        quality_score=analysis.quality_score,
                        is_primary=index == 0,
                    )
                )
                embeddings_count += 1
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

    return UserResponse.model_validate(user)


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

    # Update fields if provided
    update_data = user_data.model_dump(exclude_unset=True)
    if "role" in update_data and update_data["role"] is not None:
        role = update_data["role"]
        ensure_role_assignment_allowed(current_user, role.value)
        update_data["role"] = role.value

    # Check email uniqueness if being updated
    if "email" in update_data and update_data["email"]:
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
    if "external_id" in update_data and update_data["external_id"]:
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

    for field, value in update_data.items():
        setattr(user, field, value)

    await commit_or_conflict(db)
    await db.refresh(user)

    return UserResponse.model_validate(user)


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

    # Prevent deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    # Soft delete
    user.is_active = False
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

    await db.execute(delete(FaceEmbedding).where(FaceEmbedding.user_id == user.id))
    for index, analysis in enumerate(analyses):
        db.add(
            FaceEmbedding(
                user_id=user.id,
                embedding=analysis.embedding,
                quality_score=analysis.quality_score,
                is_primary=index == 0,
            )
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

    # Delete all embeddings for this user

    await db.execute(delete(FaceEmbedding).where(FaceEmbedding.user_id == user_id))

    # Clear enrollment timestamp
    user.enrolled_at = None
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    """
    Activate a user account.

    Admin only.
    """
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)

    user.is_active = True
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_operator)],
) -> UserResponse:
    """
    Deactivate a user account.

    Admin only.
    """
    user = await load_user(db, current_user.org_id, user_id)
    ensure_target_user_mutable(current_user, user)

    # Prevent deactivating self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


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

    user.password_hash = hash_password(request.new_password)
    await db.commit()

    return {"message": "Password reset successfully"}
