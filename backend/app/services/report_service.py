import csv
import io
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import AttendanceLog, User


class ReportService:
    """Service for generating attendance reports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_attendance_csv(
        self,
        org_id: UUID,
        start_date: date,
        end_date: date,
        user_id: Optional[UUID] = None,
        department: Optional[str] = None
    ) -> str:
        """
        Generate a CSV report of attendance logs.
        
        Args:
            org_id: Organization ID
            start_date: Start date for the report
            end_date: End date for the report
            user_id: Optional filter by user
            department: Optional filter by department
        
        Returns:
            CSV content as a string
        """
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Build query
        query = (
            select(AttendanceLog)
            .options(joinedload(AttendanceLog.user), joinedload(AttendanceLog.device))
            .where(
                AttendanceLog.org_id == org_id,
                AttendanceLog.ts >= start_datetime,
                AttendanceLog.ts <= end_datetime
            )
        )

        if user_id:
            query = query.where(AttendanceLog.user_id == user_id)

        if department:
            query = query.join(User).where(User.department == department)

        query = query.order_by(AttendanceLog.ts.desc())

        result = await self.db.execute(query)
        logs = result.scalars().unique().all()

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Date",
            "Time",
            "User ID",
            "User Name",
            "Department",
            "Type",
            "Status",
            "Confidence Score",
            "Device",
            "Device Location"
        ])

        # Data rows
        for log in logs:
            user_name = log.user.name if log.user else "Unknown"
            department_name = log.user.department if log.user else ""
            device_name = log.device.name if log.device else ""
            device_location = log.device.location if log.device else ""

            writer.writerow([
                log.ts.strftime("%Y-%m-%d"),
                log.ts.strftime("%H:%M:%S"),
                str(log.user_id) if log.user_id else "",
                user_name,
                department_name,
                log.type,
                log.status,
                f"{log.confidence_score:.2f}" if log.confidence_score else "",
                device_name,
                device_location
            ])

        return output.getvalue()

    async def get_weekly_summary(
        self,
        org_id: UUID,
        week_start: date
    ) -> Dict:
        """
        Get attendance summary for a week.
        
        Args:
            org_id: Organization ID
            week_start: Start date of the week (Monday)
        
        Returns:
            Dict with weekly summary data
        """
        week_end = week_start + timedelta(days=6)
        start_datetime = datetime.combine(week_start, datetime.min.time())
        end_datetime = datetime.combine(week_end, datetime.max.time())

        base_filter = and_(
            AttendanceLog.org_id == org_id,
            AttendanceLog.ts >= start_datetime,
            AttendanceLog.ts <= end_datetime
        )

        # Daily breakdown
        daily_stats = []
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            day_filter = and_(
                AttendanceLog.org_id == org_id,
                AttendanceLog.ts >= day_start,
                AttendanceLog.ts <= day_end
            )

            # Check-ins count
            check_ins_result = await self.db.execute(
                select(func.count()).where(
                    day_filter,
                    AttendanceLog.type == "check_in"
                )
            )
            check_ins = check_ins_result.scalar() or 0

            # Check-outs count
            check_outs_result = await self.db.execute(
                select(func.count()).where(
                    day_filter,
                    AttendanceLog.type == "check_out"
                )
            )
            check_outs = check_outs_result.scalar() or 0

            # Unique users
            unique_users_result = await self.db.execute(
                select(func.count(func.distinct(AttendanceLog.user_id))).where(
                    day_filter,
                    AttendanceLog.user_id.isnot(None)
                )
            )
            unique_users = unique_users_result.scalar() or 0

            daily_stats.append({
                "date": current_date.isoformat(),
                "day_name": current_date.strftime("%A"),
                "check_ins": check_ins,
                "check_outs": check_outs,
                "unique_users": unique_users
            })

        # Weekly totals
        total_check_ins_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.type == "check_in"
            )
        )
        total_check_ins = total_check_ins_result.scalar() or 0

        total_check_outs_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.type == "check_out"
            )
        )
        total_check_outs = total_check_outs_result.scalar() or 0

        total_unique_users_result = await self.db.execute(
            select(func.count(func.distinct(AttendanceLog.user_id))).where(
                base_filter,
                AttendanceLog.user_id.isnot(None)
            )
        )
        total_unique_users = total_unique_users_result.scalar() or 0

        successful_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.status == "success"
            )
        )
        successful = successful_result.scalar() or 0

        failed_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.status == "failed"
            )
        )
        failed = failed_result.scalar() or 0

        unknown_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.status == "unknown"
            )
        )
        unknown = unknown_result.scalar() or 0

        avg_confidence_result = await self.db.execute(
            select(func.avg(AttendanceLog.confidence_score)).where(
                base_filter,
                AttendanceLog.confidence_score.isnot(None)
            )
        )
        avg_confidence = avg_confidence_result.scalar()

        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "daily_breakdown": daily_stats,
            "totals": {
                "check_ins": total_check_ins,
                "check_outs": total_check_outs,
                "unique_users": total_unique_users,
                "successful_recognitions": successful,
                "failed_recognitions": failed,
                "unknown_recognitions": unknown,
                "average_confidence": float(avg_confidence) if avg_confidence else None
            }
        }

    async def get_user_attendance_summary(
        self,
        org_id: UUID,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Get attendance summary for a specific user.
        
        Args:
            org_id: Organization ID
            user_id: User ID
            start_date: Start date
            end_date: End date
        
        Returns:
            Dict with user attendance summary
        """
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        base_filter = and_(
            AttendanceLog.org_id == org_id,
            AttendanceLog.user_id == user_id,
            AttendanceLog.ts >= start_datetime,
            AttendanceLog.ts <= end_datetime
        )

        # Get user info
        user_result = await self.db.execute(
            select(User).where(User.id == user_id, User.org_id == org_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return {"error": "User not found"}

        # Total check-ins
        check_ins_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.type == "check_in",
                AttendanceLog.status == "success"
            )
        )
        total_check_ins = check_ins_result.scalar() or 0

        # Total check-outs
        check_outs_result = await self.db.execute(
            select(func.count()).where(
                base_filter,
                AttendanceLog.type == "check_out",
                AttendanceLog.status == "success"
            )
        )
        total_check_outs = check_outs_result.scalar() or 0

        # Days present (unique dates with successful check-in)
        days_present_result = await self.db.execute(
            select(func.count(func.distinct(func.date(AttendanceLog.ts)))).where(
                base_filter,
                AttendanceLog.type == "check_in",
                AttendanceLog.status == "success"
            )
        )
        days_present = days_present_result.scalar() or 0

        # Average confidence
        avg_confidence_result = await self.db.execute(
            select(func.avg(AttendanceLog.confidence_score)).where(
                base_filter,
                AttendanceLog.confidence_score.isnot(None)
            )
        )
        avg_confidence = avg_confidence_result.scalar()

        # First and last attendance in period
        first_attendance_result = await self.db.execute(
            select(AttendanceLog.ts).where(base_filter)
            .order_by(AttendanceLog.ts.asc())
            .limit(1)
        )
        first_attendance = first_attendance_result.scalar()

        last_attendance_result = await self.db.execute(
            select(AttendanceLog.ts).where(base_filter)
            .order_by(AttendanceLog.ts.desc())
            .limit(1)
        )
        last_attendance = last_attendance_result.scalar()

        # Calculate total days in period
        total_days = (end_date - start_date).days + 1
        # Exclude weekends for attendance rate calculation
        weekdays = sum(1 for i in range(total_days) 
                      if (start_date + timedelta(days=i)).weekday() < 5)
        
        attendance_rate = (days_present / weekdays * 100) if weekdays > 0 else 0

        return {
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "department": user.department
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_days": total_days,
                "weekdays": weekdays
            },
            "statistics": {
                "days_present": days_present,
                "total_check_ins": total_check_ins,
                "total_check_outs": total_check_outs,
                "attendance_rate": round(attendance_rate, 2),
                "average_confidence": float(avg_confidence) if avg_confidence else None
            },
            "first_attendance": first_attendance.isoformat() if first_attendance else None,
            "last_attendance": last_attendance.isoformat() if last_attendance else None
        }

    async def get_department_summary(
        self,
        org_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Get attendance summary grouped by department.
        
        Returns:
            List of department summaries
        """
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Get all departments with users
        departments_result = await self.db.execute(
            select(User.department)
            .where(User.org_id == org_id, User.department.isnot(None))
            .distinct()
        )
        departments = [d[0] for d in departments_result.all()]

        summaries = []
        for department in departments:
            # Get users in department
            users_result = await self.db.execute(
                select(func.count()).where(
                    User.org_id == org_id,
                    User.department == department,
                    User.is_active == True
                )
            )
            total_users = users_result.scalar() or 0

            # Get attendance stats
            dept_filter = and_(
                AttendanceLog.org_id == org_id,
                AttendanceLog.ts >= start_datetime,
                AttendanceLog.ts <= end_datetime,
                AttendanceLog.user_id.in_(
                    select(User.id).where(
                        User.org_id == org_id,
                        User.department == department
                    )
                )
            )

            check_ins_result = await self.db.execute(
                select(func.count()).where(
                    dept_filter,
                    AttendanceLog.type == "check_in",
                    AttendanceLog.status == "success"
                )
            )
            check_ins = check_ins_result.scalar() or 0

            unique_users_result = await self.db.execute(
                select(func.count(func.distinct(AttendanceLog.user_id))).where(
                    dept_filter,
                    AttendanceLog.status == "success"
                )
            )
            unique_users = unique_users_result.scalar() or 0

            participation_rate = (unique_users / total_users * 100) if total_users > 0 else 0

            summaries.append({
                "department": department,
                "total_users": total_users,
                "users_with_attendance": unique_users,
                "total_check_ins": check_ins,
                "participation_rate": round(participation_rate, 2)
            })

        # Sort by participation rate descending
        summaries.sort(key=lambda x: x["participation_rate"], reverse=True)

        return summaries
