"""
User management endpoints for FaceLogix.

Provides CRUD operations for users and face enrollment functionality.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.config import settings
from app.core.security import hash_password
from app.models.face_embedding import FaceEmbedding
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import (
    FaceEnrollmentRequest,
    FaceStatusResponse,
    ResetPasswordRequest,
    UserCreate,
    UserEnrollResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    department: Optional[str] = Query(None, description="Filter by department"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
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
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Calculate pagination
    pages = (total + page_size - 1) // page_size if total > 0 else 1
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new user in the organization.
    
    Admin only.
    """
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this external ID already exists",
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
        role=user_data.role,
        password_hash=password_hash,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get a user by ID.
    
    Admin only.
    """
    user = await db.get(User, user_id)
    
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update user details.
    
    Admin only.
    """
    user = await db.get(User, user_id)
    
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update fields if provided
    update_data = user_data.model_dump(exclude_unset=True)
    
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this external ID already exists",
            )
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Soft delete a user (sets is_active=False).
    
    Admin only.
    """
    user = await db.get(User, user_id)
    
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prevent deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    # Soft delete
    user.is_active = False
    await db.commit()


@router.post("/{user_id}/enroll", response_model=UserEnrollResponse)
async def enroll_user_face(
    user_id: UUID,
    request: FaceEnrollmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Enroll face embeddings for a user.
    
    Accepts 1-5 base64 encoded face images for enrollment. The images are processed 
    through the face service to generate embeddings which are stored for recognition.
    
    Request body:
    {
        "images": ["data:image/jpeg;base64,...", "data:image/jpeg;base64,..."]
    }
    
    Admin only.
    """
    # Verify user exists and belongs to org
    user = await db.get(User, user_id)
    
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enroll inactive user",
        )
    
    # Decode base64 images to bytes
    try:
        image_bytes_list = request.get_image_bytes_list()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Process images through face service
    import httpx
    
    embeddings_stored = 0
    
    async with httpx.AsyncClient(timeout=settings.FACE_SERVICE_TIMEOUT) as client:
        for idx, content in enumerate(image_bytes_list):
            try:
                response = await client.post(
                    f"{settings.FACE_SERVICE_URL}/api/v1/embed",
                    files={"image": ("face.jpg", content, "image/jpeg")},
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = result.get("embedding")
                    quality_score = result.get("quality_score")
                    
                    if embedding:
                        # Store embedding
                        face_embedding = FaceEmbedding(
                            user_id=user_id,
                            embedding=embedding,
                            quality_score=quality_score,
                            is_primary=(idx == 0 and embeddings_stored == 0),
                        )
                        db.add(face_embedding)
                        embeddings_stored += 1
                elif response.status_code == 400:
                    # No face detected in this image, continue with others
                    continue
                else:
                    # Face service error
                    continue
                    
            except httpx.TimeoutException:
                continue
            except httpx.RequestError:
                continue
    
    if embeddings_stored == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid faces detected in the provided images",
        )
    
    # Update user enrollment timestamp
    user.enrolled_at = datetime.utcnow()
    await db.commit()
    
    return UserEnrollResponse(
        user_id=user.id,
        embeddings_count=embeddings_stored,
        enrolled_at=user.enrolled_at,
    )


# Alias for frontend compatibility - same as /enroll
@router.post("/{user_id}/enroll-face", response_model=UserEnrollResponse)
async def enroll_user_face_alias(
    user_id: UUID,
    request: FaceEnrollmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Alias for /enroll endpoint for frontend compatibility.
    
    Request body:
    {
        "images": ["data:image/jpeg;base64,...", "data:image/jpeg;base64,..."]
    }
    """
    return await enroll_user_face(user_id, request, db, current_user)


@router.get("/{user_id}/face-status", response_model=FaceStatusResponse)
async def get_face_status(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get face enrollment status for a user.
    
    Returns whether the user has face embeddings and the count.
    Admin only.
    """
    user = await db.get(User, user_id)
    
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete all face embeddings for a user.
    
    Admin only.
    """
    user = await db.get(User, user_id)
    
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Delete all embeddings for this user
    from sqlalchemy import delete
    await db.execute(
        delete(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
    )
    
    # Clear enrollment timestamp
    user.enrolled_at = None
    await db.commit()


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Activate a user account.
    
    Admin only.
    """
    user = await db.get(User, user_id)
    
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Deactivate a user account.
    
    Admin only.
    """
    user = await db.get(User, user_id)
    
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Reset a user's password (admin action).
    
    Admin only.
    """
    user = await db.get(User, user_id)
    
    if not user or user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.password_hash = hash_password(request.new_password)
    await db.commit()
    
    return {"message": "Password reset successfully"}
