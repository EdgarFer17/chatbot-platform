from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.platform.models import ConversationSession, Tenant, UsageEvent


def current_month_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or datetime.now(timezone.utc)
    start = datetime(current.year, current.month, 1, tzinfo=timezone.utc)
    end = datetime(current.year + 1, 1, 1, tzinfo=timezone.utc) if current.month == 12 else datetime(current.year, current.month + 1, 1, tzinfo=timezone.utc)
    return start, end


def interactions_used(database: Session, tenant_id, environment_id=None) -> int:
    start, end = current_month_window()
    query = select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(UsageEvent.tenant_id == tenant_id, UsageEvent.created_at >= start, UsageEvent.created_at < end)
    if environment_id:
        query = query.where(UsageEvent.environment_id == environment_id)
    return int(database.scalar(query) or 0)


def usage_summary(database: Session, tenant: Tenant, environment_id=None) -> dict:
    start, end = current_month_window()
    used = interactions_used(database, tenant.id, environment_id)
    total_used = interactions_used(database, tenant.id)
    sessions_query = select(func.count(ConversationSession.id)).where(ConversationSession.tenant_id == tenant.id, ConversationSession.created_at >= start, ConversationSession.created_at < end)
    if environment_id:
        sessions_query = sessions_query.where(ConversationSession.environment_id == environment_id)
    sessions = int(database.scalar(sessions_query) or 0)
    limit = tenant.monthly_message_limit
    return {"tenant_id": tenant.id, "environment_id": environment_id, "period_start": start, "period_end": end, "interactions_used": used, "total_interactions_used": total_used, "monthly_limit": limit, "remaining": max(0, limit - total_used), "usage_percentage": round(min(100, total_used / limit * 100), 2), "sessions_created": sessions}
