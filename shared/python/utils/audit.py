"""
PossKassa — Audit Jurnali yozuvchi
Barcha pul va zaxiraga ta'sir qiluvchi amallar loglanadi
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def write_audit_log(
    session:     AsyncSession,
    tenant_id:   uuid.UUID,
    user_id:     uuid.UUID | None,
    entity_type: str,
    entity_id:   uuid.UUID | None,
    action:      str,
    before:      Any = None,
    after:       Any = None,
    ip_address:  str | None = None,
) -> None:
    """
    Audit jurnali yozadi.

    Misol:
        await write_audit_log(
            session, tenant_id, user_id,
            entity_type="sale",
            entity_id=sale.id,
            action="created",
            after={"total": 50000},
        )
    """
    import json

    def _serialize(obj: Any) -> str | None:
        if obj is None:
            return None
        if isinstance(obj, str):
            return obj
        try:
            return json.dumps(obj, default=str)
        except Exception:
            return str(obj)

    await session.execute(
        text("""
            INSERT INTO audit_logs
                (id, tenant_id, user_id, entity_type, entity_id,
                 action, before_state, after_state, ip_address, created_at)
            VALUES
                (:id, :tenant_id, :user_id, :entity_type, :entity_id,
                 :action, :before_state::jsonb, :after_state::jsonb, :ip_address, :created_at)
        """),
        {
            "id":           str(uuid.uuid4()),
            "tenant_id":    str(tenant_id),
            "user_id":      str(user_id) if user_id else None,
            "entity_type":  entity_type,
            "entity_id":    str(entity_id) if entity_id else None,
            "action":       action,
            "before_state": _serialize(before),
            "after_state":  _serialize(after),
            "ip_address":   ip_address,
            "created_at":   datetime.now(timezone.utc),
        },
    )
