"""
PossKassa — Muvofiqlik API router lari
OFD fiskallashtirish, ESF, E-IMZO
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from ..services.ofd_service   import OfdService
from ..services.esf_service   import EsfService
from ..services.eimzo_service import EimzoService
from ....shared.python.auth.dependencies import RequireCashier, RequireManager, RequireAdmin
from ....shared.python.db.base import get_tenant_session

router = APIRouter()


# ─── OFD / Fiskallashtirish ──────────────────────────
class FiscalizeRequest(BaseModel):
    sale_id:           str
    receipt_number:    str
    cashier_tin:       str = ""
    warehouse_address: str = ""
    sale_time:         str
    items: list[dict]
    payments: list[dict]
    total:    float
    vat_total:float = 0.0
    customer_phone: str = ""


@router.post("/fiscalize", status_code=201)
async def fiscalize_sale(data: FiscalizeRequest, token: RequireCashier):
    """
    Sotuvni OFD orqali fiskallash.
    Internet bo'lmasa oflayn stub qaytaradi va keyinroq qayta yuboradi.
    """
    async for session in get_tenant_session(str(token.tenant_id)):
        # Tenant OFD tokenini olish
        cfg = await session.execute(
            text("SELECT ofd_token FROM tenants WHERE id = :tid"),
            {"tid": str(token.tenant_id)},
        )
        row = cfg.fetchone()
        ofd_token = row.ofd_token if row else ""

        svc    = OfdService(session, token.tenant_id, ofd_token or "")
        result = await svc.fiscalize_sale(data.model_dump())
        return result


@router.get("/receipts/{sale_id}")
async def get_fiscal_receipt(sale_id: str, token: RequireCashier):
    """Sotuvning fiskal chekini olish"""
    async for session in get_tenant_session(str(token.tenant_id)):
        cfg = await session.execute(
            text("SELECT ofd_token FROM tenants WHERE id = :tid"),
            {"tid": str(token.tenant_id)},
        )
        row = cfg.fetchone()
        svc    = OfdService(session, token.tenant_id, row.ofd_token if row else "")
        result = await svc.get_fiscal_receipt(sale_id)
        if not result:
            raise HTTPException(status_code=404, detail="Fiskal chek topilmadi")
        return result


# ─── ESF ────────────────────────────────────────────
class EsfCreateRequest(BaseModel):
    seller_tin:      str
    buyer_tin:       str
    buyer_name:      str
    items:           list[dict]
    total:           float
    vat_total:       float = 0.0
    invoice_date:    Optional[str] = None
    contract_num:    Optional[str] = None
    contract_date:   Optional[str] = None


@router.post("/esf/create", status_code=201)
async def create_esf(data: EsfCreateRequest, token: RequireManager):
    """B2B sotuv uchun ESF yaratish"""
    async for session in get_tenant_session(str(token.tenant_id)):
        cfg = await session.execute(
            text("SELECT didox_token FROM tenants WHERE id = :tid"),
            {"tid": str(token.tenant_id)},
        )
        row = cfg.fetchone()
        if not row or not row.didox_token:
            raise HTTPException(
                status_code=422,
                detail="didox.uz tokeni sozlanmagan. Admin > Integratsiyalar bo'limiga kiring."
            )

        svc    = EsfService(token.tenant_id, row.didox_token)
        result = await svc.create_esf(data.model_dump())
        return result


@router.get("/esf/{invoice_id}")
async def get_esf_status(invoice_id: str, token: RequireManager):
    """ESF holati"""
    async for session in get_tenant_session(str(token.tenant_id)):
        cfg = await session.execute(
            text("SELECT didox_token FROM tenants WHERE id = :tid"),
            {"tid": str(token.tenant_id)},
        )
        row = cfg.fetchone()
        svc = EsfService(token.tenant_id, row.didox_token if row else "")
        return await svc.get_esf_status(invoice_id)


@router.post("/esf/{invoice_id}/cancel")
async def cancel_esf(invoice_id: str, reason: str, token: RequireManager):
    """ESF ni bekor qilish"""
    async for session in get_tenant_session(str(token.tenant_id)):
        cfg = await session.execute(
            text("SELECT didox_token FROM tenants WHERE id = :tid"),
            {"tid": str(token.tenant_id)},
        )
        row = cfg.fetchone()
        svc = EsfService(token.tenant_id, row.didox_token if row else "")
        return await svc.cancel_esf(invoice_id, reason)


# ─── E-IMZO ─────────────────────────────────────────
class SignRequest(BaseModel):
    document: dict


@router.post("/eimzo/sign")
async def sign_document(data: SignRequest, token: RequireAdmin):
    """Hujjatni E-IMZO raqamli imzo bilan imzolash"""
    async for session in get_tenant_session(str(token.tenant_id)):
        cfg = await session.execute(
            text("SELECT eimzo_cert FROM tenants WHERE id = :tid"),
            {"tid": str(token.tenant_id)},
        )
        row = cfg.fetchone()
        if not row or not row.eimzo_cert:
            raise HTTPException(
                status_code=422,
                detail="E-IMZO sertifikati sozlanmagan. Admin > Integratsiyalar bo'limiga kiring."
            )

        svc    = EimzoService(row.eimzo_cert)
        result = await svc.sign_document(data.document)
        return result


@router.get("/eimzo/cert-info")
async def get_cert_info(token: RequireAdmin):
    """E-IMZO sertifikat ma'lumotlari"""
    async for session in get_tenant_session(str(token.tenant_id)):
        cfg = await session.execute(
            text("SELECT eimzo_cert FROM tenants WHERE id = :tid"),
            {"tid": str(token.tenant_id)},
        )
        row = cfg.fetchone()
        if not row or not row.eimzo_cert:
            return {"valid": False, "message": "Sertifikat sozlanmagan"}

        svc = EimzoService(row.eimzo_cert)
        return svc.get_cert_info()
