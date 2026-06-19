"""
PossKassa — Umumiy ma'lumotlar bazasi konfiguratsiyasi
SQLAlchemy 2.0 async engine + multi-tenant RLS
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from ..utils.config import settings


# ─────────────────────────────────────────
# Async engine
# ─────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ─────────────────────────────────────────
# Asosiy model sinfi
# ─────────────────────────────────────────
class Base(AsyncAttrs, DeclarativeBase):
    """Barcha modellar uchun asosiy sinf"""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TenantBase(Base):
    """Multi-tenant modellar uchun asosiy sinf"""
    __abstract__ = True

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )


# ─────────────────────────────────────────
# Multi-tenant session (RLS o'rnatish)
# ─────────────────────────────────────────
async def get_tenant_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Tenant ID bilan PostgreSQL RLS ni o'rnatgan holda session beradi.
    Barcha xizmat endpoint lari shu session ni ishlatishi kerak.
    """
    async with AsyncSessionLocal() as session:
        # PostgreSQL RLS uchun tenant ID ni o'rnatish
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, TRUE)"),
            {"tid": str(tenant_id)},
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Oddiy (RLS siz) session — faqat tenant-independent operatsiyalar uchun"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
