"""
PossKassa — Sotuv API router lari
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.sale import (
    SaleCreate, SaleResponse, SaleSyncBatch, SaleSyncResponse,
    ShiftOpen, ShiftClose, ShiftResponse, RefundCreate,
)
from ..services.sale_service import SaleService
from ....shared.python.auth.dependencies import RequireCashier, RequireManager, TokenData
from ....shared.python.db.base import get_tenant_session

router = APIRouter()


def get_sale_service(
    token:   TokenData = Depends(RequireCashier.__class__),
    session: AsyncSession = Depends(lambda: None),  # overridden below
) -> SaleService:
    return SaleService(session, token.tenant_id, token.user_id)


# ──────────────────────────────────────────────────
# Smena endpointlari
# ──────────────────────────────────────────────────
@router.post("/shifts/open", response_model=ShiftResponse, status_code=201)
async def open_shift(
    data:    ShiftOpen,
    token:   RequireCashier,
    request: Request,
):
    """Yangi smena ochish"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc    = SaleService(session, token.tenant_id, token.user_id)
        shift  = await svc.open_shift(data)
        return ShiftResponse.model_validate(shift)


@router.post("/shifts/{shift_id}/close", response_model=ShiftResponse)
async def close_shift(
    shift_id: uuid.UUID,
    data:     ShiftClose,
    token:    RequireCashier,
):
    """Smenani yopish"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc   = SaleService(session, token.tenant_id, token.user_id)
        shift = await svc.close_shift(shift_id, data)
        return ShiftResponse.model_validate(shift)


@router.get("/shifts/current", response_model=Optional[ShiftResponse])
async def get_current_shift(token: RequireCashier):
    """Joriy ochiq smenani olish"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc   = SaleService(session, token.tenant_id, token.user_id)
        shift = await svc.get_current_shift()
        return ShiftResponse.model_validate(shift) if shift else None


# ──────────────────────────────────────────────────
# Sotuv endpointlari
# ──────────────────────────────────────────────────
@router.post("", response_model=SaleResponse, status_code=201)
async def create_sale(data: SaleCreate, token: RequireCashier):
    """Yangi sotuv yaratish"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc  = SaleService(session, token.tenant_id, token.user_id)
        sale = await svc.create_sale(data)
        return SaleResponse.model_validate(sale)


@router.post("/sync", response_model=SaleSyncResponse)
async def sync_sales(batch: SaleSyncBatch, token: RequireCashier):
    """Oflayn sotuvlar paketini sinxronlash"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc    = SaleService(session, token.tenant_id, token.user_id)
        result = await svc.sync_batch(batch)
        return result


@router.get("", response_model=list[SaleResponse])
async def list_sales(
    token:    RequireCashier,
    skip:     int = Query(0, ge=0),
    limit:    int = Query(50, ge=1, le=200),
    shift_id: Optional[uuid.UUID] = None,
    from_:    Optional[datetime]  = Query(None, alias="from"),
    to:       Optional[datetime]  = None,
):
    """Sotuvlar ro'yxati"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc   = SaleService(session, token.tenant_id, token.user_id)
        sales = await svc.list_sales(skip, limit, shift_id, from_, to)
        return [SaleResponse.model_validate(s) for s in sales]


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(sale_id: uuid.UUID, token: RequireCashier):
    """Sotuv tafsilotlari"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc  = SaleService(session, token.tenant_id, token.user_id)
        sale = await svc.get_sale(sale_id)
        return SaleResponse.model_validate(sale)


@router.post("/{sale_id}/refund", response_model=dict, status_code=201)
async def refund_sale(
    sale_id: uuid.UUID,
    data:    RefundCreate,
    token:   RequireManager,
):
    """To'liq qaytarish (menejer va yuqori)"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = SaleService(session, token.tenant_id, token.user_id)
        ret = await svc.create_refund(sale_id, data)
        return {"id": str(ret.id), "message": "Qaytarish muvaffaqiyatli amalga oshirildi"}
