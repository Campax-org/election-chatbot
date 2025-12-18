"""Documentation logging service for tracking generation and update operations."""

from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class DocumentationLogService:
    """Service for logging documentation generation and update operations."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    async def log_generation(
        self,
        category: str,
        action: str,
        status: str,
        components_affected: int = 0,
        duration_ms: float | None = None,
        error_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Log a documentation generation or update operation."""
        from app.auth.models import DocumentationLog
        
        async with self.session_maker() as session:
            log_entry = DocumentationLog(
                timestamp=datetime.now(timezone.utc),
                category=category,
                action=action,
                status=status,
                components_affected=components_affected,
                duration_ms=duration_ms,
                error_message=error_message,
                details=details or {},
            )
            session.add(log_entry)
            await session.commit()
            await session.refresh(log_entry)
            
            return {
                "id": str(log_entry.id),
                "timestamp": log_entry.timestamp.isoformat(),
                "category": log_entry.category,
                "action": log_entry.action,
                "status": log_entry.status,
                "components_affected": log_entry.components_affected,
                "duration_ms": log_entry.duration_ms,
                "error_message": log_entry.error_message,
            }

    async def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        category: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve documentation logs with optional filtering."""
        from app.auth.models import DocumentationLog
        
        async with self.session_maker() as session:
            query = select(DocumentationLog).order_by(desc(DocumentationLog.timestamp))
            
            if category:
                query = query.where(DocumentationLog.category == category)
            if status:
                query = query.where(DocumentationLog.status == status)
            
            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            logs = result.scalars().all()
            
            return [
                {
                    "id": str(log.id),
                    "timestamp": log.timestamp.isoformat(),
                    "category": log.category,
                    "action": log.action,
                    "status": log.status,
                    "components_affected": log.components_affected,
                    "duration_ms": log.duration_ms,
                    "error_message": log.error_message,
                    "details": log.details,
                }
                for log in logs
            ]

    async def get_statistics(self, hours: int = 24) -> dict[str, Any]:
        """Get documentation generation statistics for the last N hours."""
        from app.auth.models import DocumentationLog
        
        async with self.session_maker() as session:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Total operations
            total_query = select(func.count(DocumentationLog.id)).where(
                DocumentationLog.timestamp >= since
            )
            total_result = await session.execute(total_query)
            total = total_result.scalar() or 0
            
            # Successful operations
            success_query = select(func.count(DocumentationLog.id)).where(
                DocumentationLog.timestamp >= since,
                DocumentationLog.status == "success"
            )
            success_result = await session.execute(success_query)
            successful = success_result.scalar() or 0
            
            # Failed operations
            failed_query = select(func.count(DocumentationLog.id)).where(
                DocumentationLog.timestamp >= since,
                DocumentationLog.status == "failed"
            )
            failed_result = await session.execute(failed_query)
            failed = failed_result.scalar() or 0
            
            # Average duration
            avg_duration_query = select(func.avg(DocumentationLog.duration_ms)).where(
                DocumentationLog.timestamp >= since,
                DocumentationLog.duration_ms.isnot(None)
            )
            avg_duration_result = await session.execute(avg_duration_query)
            avg_duration = avg_duration_result.scalar() or 0
            
            # Total components affected
            components_query = select(func.sum(DocumentationLog.components_affected)).where(
                DocumentationLog.timestamp >= since
            )
            components_result = await session.execute(components_query)
            total_components = components_result.scalar() or 0
            
            # By category
            category_query = select(
                DocumentationLog.category,
                func.count(DocumentationLog.id)
            ).where(
                DocumentationLog.timestamp >= since
            ).group_by(DocumentationLog.category)
            category_result = await session.execute(category_query)
            by_category = {row[0]: row[1] for row in category_result.all()}
            
            # Last generation time
            last_gen_query = select(DocumentationLog.timestamp).where(
                DocumentationLog.action == "complete",
                DocumentationLog.status == "success"
            ).order_by(desc(DocumentationLog.timestamp)).limit(1)
            last_gen_result = await session.execute(last_gen_query)
            last_gen = last_gen_result.scalar()
            
            return {
                "period_hours": hours,
                "total_operations": total,
                "successful": successful,
                "failed": failed,
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "average_duration_ms": round(avg_duration, 2) if avg_duration else 0,
                "total_components_affected": total_components,
                "by_category": by_category,
                "last_successful_generation": last_gen.isoformat() if last_gen else None,
            }

    async def get_recent_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent error logs."""
        from app.auth.models import DocumentationLog
        
        async with self.session_maker() as session:
            query = select(DocumentationLog).where(
                DocumentationLog.status == "failed"
            ).order_by(desc(DocumentationLog.timestamp)).limit(limit)
            
            result = await session.execute(query)
            logs = result.scalars().all()
            
            return [
                {
                    "id": str(log.id),
                    "timestamp": log.timestamp.isoformat(),
                    "category": log.category,
                    "action": log.action,
                    "error_message": log.error_message,
                    "details": log.details,
                }
                for log in logs
            ]
