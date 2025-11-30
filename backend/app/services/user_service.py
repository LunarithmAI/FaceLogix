from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models import FaceEmbedding, User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for handling user operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        org_id: UUID,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        department: Optional[str] = None,
        is_active: Optional[bool] = None,
        role: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """
        List users for an organization with pagination and filters.
        
        Returns:
            Tuple of (users, total_count)
        """
        query = select(User).where(User.org_id == org_id)

        # Apply filters
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (User.name.ilike(search_pattern)) |
                (User.email.ilike(search_pattern)) |
                (User.external_id.ilike(search_pattern))
            )

        if department:
            query = query.where(User.department == department)

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        if role:
            query = query.where(User.role == role)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(User.name).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def create_user(self, org_id: UUID, data: UserCreate) -> User:
        """
        Create a new user.
        
        Raises:
            ConflictError: If email or external_id already exists
        """
        # Check for existing email
        if data.email:
            existing = await self.db.execute(
                select(User).where(
                    User.org_id == org_id,
                    User.email == data.email
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(
                    message="A user with this email already exists",
                    code="EMAIL_EXISTS"
                )

        # Check for existing external_id
        if data.external_id:
            existing = await self.db.execute(
                select(User).where(
                    User.org_id == org_id,
                    User.external_id == data.external_id
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(
                    message="A user with this external ID already exists",
                    code="EXTERNAL_ID_EXISTS"
                )

        # Create user
        user = User(
            org_id=org_id,
            email=data.email,
            name=data.name,
            external_id=data.external_id,
            role=data.role,
            department=data.department,
            is_active=True
        )

        if data.password:
            user.password_hash = hash_password(data.password)

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_user(self, org_id: UUID, user_id: UUID) -> User:
        """
        Get a user by ID.
        
        Raises:
            NotFoundError: If user not found
        """
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.org_id == org_id
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError(
                message="User not found",
                resource_type="User",
                resource_id=str(user_id)
            )

        return user

    async def get_user_with_embeddings(
        self, org_id: UUID, user_id: UUID
    ) -> Tuple[User, int]:
        """
        Get a user with their face embeddings count.
        
        Returns:
            Tuple of (user, embeddings_count)
        """
        user = await self.get_user(org_id, user_id)

        # Get embeddings count
        count_result = await self.db.execute(
            select(func.count()).where(FaceEmbedding.user_id == user_id)
        )
        embeddings_count = count_result.scalar() or 0

        return user, embeddings_count

    async def update_user(
        self, org_id: UUID, user_id: UUID, data: UserUpdate
    ) -> User:
        """
        Update a user.
        
        Raises:
            NotFoundError: If user not found
            ConflictError: If email or external_id already exists
        """
        user = await self.get_user(org_id, user_id)

        # Check for email conflict
        if data.email and data.email != user.email:
            existing = await self.db.execute(
                select(User).where(
                    User.org_id == org_id,
                    User.email == data.email,
                    User.id != user_id
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(
                    message="A user with this email already exists",
                    code="EMAIL_EXISTS"
                )

        # Check for external_id conflict
        if data.external_id and data.external_id != user.external_id:
            existing = await self.db.execute(
                select(User).where(
                    User.org_id == org_id,
                    User.external_id == data.external_id,
                    User.id != user_id
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(
                    message="A user with this external ID already exists",
                    code="EXTERNAL_ID_EXISTS"
                )

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        
        if "password" in update_data:
            password = update_data.pop("password")
            if password:
                user.password_hash = hash_password(password)

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def delete_user(self, org_id: UUID, user_id: UUID) -> bool:
        """
        Delete a user.
        
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_user(org_id, user_id)

        await self.db.delete(user)
        await self.db.commit()

        return True

    async def store_embeddings(
        self,
        user_id: UUID,
        embeddings: List[List[float]],
        quality_scores: Optional[List[float]] = None,
        replace_existing: bool = False
    ) -> int:
        """
        Store face embeddings for a user.
        
        Args:
            user_id: The user ID
            embeddings: List of embedding vectors
            quality_scores: Optional list of quality scores for each embedding
            replace_existing: If True, delete existing embeddings first
        
        Returns:
            Number of embeddings stored
        """
        if replace_existing:
            # Delete existing embeddings
            result = await self.db.execute(
                select(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
            )
            existing = result.scalars().all()
            for emb in existing:
                await self.db.delete(emb)

        # Store new embeddings
        for i, embedding in enumerate(embeddings):
            quality_score = quality_scores[i] if quality_scores and i < len(quality_scores) else None
            is_primary = (i == 0)  # First embedding is primary

            face_embedding = FaceEmbedding(
                user_id=user_id,
                embedding=embedding,
                quality_score=quality_score,
                is_primary=is_primary
            )
            self.db.add(face_embedding)

        # Update user's enrolled_at timestamp
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user and not user.enrolled_at:
            user.enrolled_at = datetime.utcnow()

        await self.db.commit()

        return len(embeddings)

    async def get_user_embeddings(self, user_id: UUID) -> List[FaceEmbedding]:
        """Get all face embeddings for a user."""
        result = await self.db.execute(
            select(FaceEmbedding)
            .where(FaceEmbedding.user_id == user_id)
            .order_by(FaceEmbedding.is_primary.desc(), FaceEmbedding.created_at)
        )
        return list(result.scalars().all())

    async def delete_embeddings(self, user_id: UUID) -> int:
        """
        Delete all face embeddings for a user.
        
        Returns:
            Number of embeddings deleted
        """
        result = await self.db.execute(
            select(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
        )
        embeddings = result.scalars().all()

        count = len(embeddings)
        for emb in embeddings:
            await self.db.delete(emb)

        if count > 0:
            # Clear enrolled_at
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.enrolled_at = None

            await self.db.commit()

        return count
