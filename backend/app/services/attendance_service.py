from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, and_, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.exceptions import FaceServiceError, NotFoundError
from app.models import AttendanceLog, Device, FaceEmbedding, User
from app.schemas.attendance import (
    AttendanceQuery,
    CheckInResponse,
    DailySummary,
)
from app.services.face_client import FaceServiceClient


class AttendanceService:
    """Service for handling attendance operations."""

    def __init__(
        self,
        db: AsyncSession,
        face_client: Optional[FaceServiceClient] = None
    ):
        self.db = db
        self.face_client = face_client or FaceServiceClient()

    async def process_check_in(
        self,
        org_id: UUID,
        device_id: UUID,
        image_base64: str,
        threshold: Optional[float] = None
    ) -> CheckInResponse:
        """
        Process a check-in request using face recognition.
        
        Args:
            org_id: Organization ID
            device_id: Device ID making the request
            image_base64: Base64 encoded face image
            threshold: Optional recognition threshold
        
        Returns:
            CheckInResponse with recognition result
        """
        return await self._process_attendance(
            org_id=org_id,
            device_id=device_id,
            image_base64=image_base64,
            action="check_in",
            threshold=threshold
        )

    async def process_check_out(
        self,
        org_id: UUID,
        device_id: UUID,
        image_base64: str,
        threshold: Optional[float] = None
    ) -> CheckInResponse:
        """
        Process a check-out request using face recognition.
        
        Args:
            org_id: Organization ID
            device_id: Device ID making the request
            image_base64: Base64 encoded face image
            threshold: Optional recognition threshold
        
        Returns:
            CheckInResponse with recognition result
        """
        return await self._process_attendance(
            org_id=org_id,
            device_id=device_id,
            image_base64=image_base64,
            action="check_out",
            threshold=threshold
        )

    async def _process_attendance(
        self,
        org_id: UUID,
        device_id: UUID,
        image_base64: str,
        action: str,
        threshold: Optional[float] = None
    ) -> CheckInResponse:
        """
        Process an attendance request (check-in or check-out).
        """
        threshold = threshold or settings.DEFAULT_RECOGNITION_THRESHOLD
        timestamp = datetime.utcnow()

        try:
            # Step 1: Check liveness
            liveness_result = await self.face_client.detect_liveness(image_base64)
            
            if not liveness_result.get("is_live", False):
                # Log failed attempt
                attendance_log = AttendanceLog(
                    org_id=org_id,
                    device_id=device_id,
                    ts=timestamp,
                    type=action,
                    status="failed",
                    meta={"reason": "liveness_check_failed"}
                )
                self.db.add(attendance_log)
                await self.db.commit()

                return CheckInResponse(
                    status="failed",
                    message="Liveness check failed. Please ensure you are looking at the camera.",
                    timestamp=timestamp
                )

            # Step 2: Generate embedding
            embed_result = await self.face_client.generate_embedding(image_base64)
            query_embedding = embed_result.get("embedding")
            quality_score = embed_result.get("quality_score")

            if not query_embedding:
                attendance_log = AttendanceLog(
                    org_id=org_id,
                    device_id=device_id,
                    ts=timestamp,
                    type=action,
                    status="failed",
                    meta={"reason": "no_face_detected"}
                )
                self.db.add(attendance_log)
                await self.db.commit()

                return CheckInResponse(
                    status="failed",
                    message="No face detected in the image. Please try again.",
                    timestamp=timestamp
                )

            # Step 3: Search for matching face using pgvector
            match_result = await self._find_matching_user(
                org_id=org_id,
                query_embedding=query_embedding,
                threshold=threshold
            )

            if not match_result:
                # No match found
                attendance_log = AttendanceLog(
                    org_id=org_id,
                    device_id=device_id,
                    ts=timestamp,
                    type=action,
                    status="unknown",
                    meta={
                        "reason": "no_match_found",
                        "quality_score": quality_score
                    }
                )
                self.db.add(attendance_log)
                await self.db.commit()
                await self.db.refresh(attendance_log)

                return CheckInResponse(
                    status="unknown",
                    message="Face not recognized. Please contact an administrator if you believe this is an error.",
                    attendance_id=attendance_log.id,
                    timestamp=timestamp
                )

            user, confidence_score = match_result

            # Step 4: Log successful attendance
            attendance_log = AttendanceLog(
                org_id=org_id,
                user_id=user.id,
                device_id=device_id,
                ts=timestamp,
                type=action,
                status="success",
                confidence_score=confidence_score,
                meta={
                    "quality_score": quality_score,
                    "liveness_confidence": liveness_result.get("confidence")
                }
            )
            self.db.add(attendance_log)
            await self.db.commit()
            await self.db.refresh(attendance_log)

            action_word = "checked in" if action == "check_in" else "checked out"
            return CheckInResponse(
                status="success",
                message=f"Welcome, {user.name}! You have successfully {action_word}.",
                user_id=user.id,
                user_name=user.name,
                user_department=user.department,
                confidence_score=confidence_score,
                attendance_id=attendance_log.id,
                timestamp=timestamp
            )

        except FaceServiceError as e:
            # Log service error
            attendance_log = AttendanceLog(
                org_id=org_id,
                device_id=device_id,
                ts=timestamp,
                type=action,
                status="failed",
                meta={"reason": "face_service_error", "error": str(e)}
            )
            self.db.add(attendance_log)
            await self.db.commit()

            return CheckInResponse(
                status="failed",
                message="Face recognition service is temporarily unavailable. Please try again later.",
                timestamp=timestamp
            )

    async def _find_matching_user(
        self,
        org_id: UUID,
        query_embedding: List[float],
        threshold: float
    ) -> Optional[Tuple[User, float]]:
        """
        Find a matching user using vector similarity search.
        
        Uses pgvector's cosine distance operator for efficient similarity search.
        
        Returns:
            Tuple of (user, confidence_score) if match found, None otherwise
        """
        # Convert threshold to distance (cosine distance = 1 - similarity)
        max_distance = 1 - threshold

        # Query using pgvector cosine distance
        # Join with users to filter by org_id and get user details
        query = text("""
            SELECT 
                fe.user_id,
                1 - (fe.embedding <=> :query_embedding::vector) as similarity
            FROM face_embeddings fe
            JOIN users u ON fe.user_id = u.id
            WHERE u.org_id = :org_id
              AND u.is_active = true
              AND (fe.embedding <=> :query_embedding::vector) < :max_distance
            ORDER BY fe.embedding <=> :query_embedding::vector
            LIMIT 1
        """)

        result = await self.db.execute(
            query,
            {
                "query_embedding": query_embedding,
                "org_id": str(org_id),
                "max_distance": max_distance
            }
        )
        row = result.first()

        if not row:
            return None

        user_id, similarity = row

        # Fetch the full user object
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return None

        return user, float(similarity)

    async def list_attendance(
        self,
        org_id: UUID,
        query: AttendanceQuery
    ) -> Tuple[List[AttendanceLog], int]:
        """
        List attendance logs with filters and pagination.
        
        Returns:
            Tuple of (attendance_logs, total_count)
        """
        base_query = select(AttendanceLog).where(AttendanceLog.org_id == org_id)

        # Apply filters
        if query.user_id:
            base_query = base_query.where(AttendanceLog.user_id == query.user_id)

        if query.device_id:
            base_query = base_query.where(AttendanceLog.device_id == query.device_id)

        if query.status:
            base_query = base_query.where(AttendanceLog.status == query.status)

        if query.type:
            base_query = base_query.where(AttendanceLog.type == query.type)

        if query.start_date:
            start_datetime = datetime.combine(query.start_date, datetime.min.time())
            base_query = base_query.where(AttendanceLog.ts >= start_datetime)

        if query.end_date:
            end_datetime = datetime.combine(query.end_date, datetime.max.time())
            base_query = base_query.where(AttendanceLog.ts <= end_datetime)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        offset = (query.page - 1) * query.page_size
        base_query = (
            base_query
            .options(joinedload(AttendanceLog.user), joinedload(AttendanceLog.device))
            .order_by(AttendanceLog.ts.desc())
            .offset(offset)
            .limit(query.page_size)
        )

        result = await self.db.execute(base_query)
        logs = list(result.scalars().unique().all())

        return logs, total

    async def get_daily_summary(
        self,
        org_id: UUID,
        target_date: date
    ) -> DailySummary:
        """
        Get attendance summary for a specific day.
        """
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        # Base filter
        base_filter = and_(
            AttendanceLog.org_id == org_id,
            AttendanceLog.ts >= start_datetime,
            AttendanceLog.ts <= end_datetime
        )

        # Total check-ins
        check_ins_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.type == "check_in"
            )
        )
        total_check_ins = check_ins_result.scalar() or 0

        # Total check-outs
        check_outs_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.type == "check_out"
            )
        )
        total_check_outs = check_outs_result.scalar() or 0

        # Unique users
        unique_users_result = await self.db.execute(
            select(func.count(func.distinct(AttendanceLog.user_id))).where(
                base_filter,
                AttendanceLog.user_id.isnot(None)
            )
        )
        unique_users = unique_users_result.scalar() or 0

        # Successful recognitions
        successful_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.status == "success"
            )
        )
        successful_recognitions = successful_result.scalar() or 0

        # Failed recognitions
        failed_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.status == "failed"
            )
        )
        failed_recognitions = failed_result.scalar() or 0

        # Average confidence
        avg_confidence_result = await self.db.execute(
            select(func.avg(AttendanceLog.confidence_score)).where(
                base_filter,
                AttendanceLog.confidence_score.isnot(None)
            )
        )
        average_confidence = avg_confidence_result.scalar()

        return DailySummary(
            date=target_date,
            total_check_ins=total_check_ins,
            total_check_outs=total_check_outs,
            unique_users=unique_users,
            successful_recognitions=successful_recognitions,
            failed_recognitions=failed_recognitions,
            average_confidence=float(average_confidence) if average_confidence else None
        )

    async def get_attendance_by_id(
        self,
        org_id: UUID,
        attendance_id: UUID
    ) -> AttendanceLog:
        """
        Get a specific attendance log by ID.
        
        Raises:
            NotFoundError: If attendance log not found
        """
        result = await self.db.execute(
            select(AttendanceLog)
            .options(joinedload(AttendanceLog.user), joinedload(AttendanceLog.device))
            .where(
                AttendanceLog.id == attendance_id,
                AttendanceLog.org_id == org_id
            )
        )
        log = result.scalar_one_or_none()

        if not log:
            raise NotFoundError(
                message="Attendance log not found",
                resource_type="AttendanceLog",
                resource_id=str(attendance_id)
            )

        return log
