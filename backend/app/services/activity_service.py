from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.models.user import ActivityLog, User


def get_request_access_details(request: Request | None) -> dict:
    if request is None:
        return {}

    forwarded_for = request.headers.get("x-forwarded-for", "")
    ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else None
    ip_address = ip_address or request.headers.get("x-real-ip") or (request.client.host if request.client else "")

    city = request.headers.get("x-vercel-ip-city") or request.headers.get("cf-ipcity") or ""
    region = request.headers.get("x-vercel-ip-country-region") or request.headers.get("cf-region") or ""
    country = request.headers.get("x-vercel-ip-country") or request.headers.get("cf-ipcountry") or ""
    location = ", ".join(part for part in (city, region, country) if part) or "Unknown"

    return {
        "ip_address": ip_address or "Unknown",
        "location": location,
        "user_agent": request.headers.get("user-agent", "Unknown"),
        "referer": request.headers.get("referer", ""),
    }


async def log_activity(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    description: str,
    actor: User | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
) -> ActivityLog:
    entry = ActivityLog(
        actor_id=actor.id if actor else None,
        actor_name=actor.username if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        details=details or {},
    )
    db.add(entry)
    return entry
