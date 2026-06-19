"""
PossKassa — Tovar Qabuli API router lari
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from ..services.intake_service import IntakeService
from ....shared.python.auth.dependencies import RequireManager, RequireAdmin
from ....shared.python.db.base import get_tenant_session

router = APIRouter()


# ── Sxemalar ───────────────────────────────────────
class ApproveRequest(BaseModel):
    reviewed_rows:  list[dict]
    warehouse_id:   uuid.UUID
    supplier_id:    Optional[uuid.UUID] = None
    invoice_number: Optional[str]       = None


class RejectRequest(BaseModel):
    reason: str


class SupplierCreate(BaseModel):
    name:    str
    inn:     Optional[str] = None
    phone:   Optional[str] = None
    email:   Optional[str] = None
    address: Optional[str] = None


# ── Foto orqali kirim ───────────────────────────────
@router.post("/photo", status_code=201)
async def start_photo_intake(
    token:        RequireManager,
    file:         UploadFile = File(..., description="Yetkazuvchi ro'yxati rasmi"),
    supplier_id:  Optional[uuid.UUID] = Form(None),
    warehouse_id: Optional[uuid.UUID] = Form(None),
):
    """
    Rasm yuklash va Claude Vision LLM orqali mahsulotlarni ajratib olish.
    Natija tekshiruv uchun /drafts/{id} endpointidan olinadi.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Faqat rasm fayllari qabul qilinadi (JPEG, PNG, WEBP)")

    async for session in get_tenant_session(str(token.tenant_id)):
        svc   = IntakeService(session, token.tenant_id, token.user_id)
        draft = await svc.start_photo_intake(file, supplier_id, warehouse_id)
        return {
            "draft_id": str(draft.id),
            "status":   draft.status,
            "message":  "Rasm qayta ishlanmoqda. Natijani GET /intake/drafts/{id} orqali oling.",
        }


# ── CSV/Excel orqali kirim ──────────────────────────
@router.post("/csv", status_code=201)
async def start_csv_intake(
    token:        RequireManager,
    file:         UploadFile = File(..., description="CSV yoki Excel fayli"),
    supplier_id:  Optional[uuid.UUID] = Form(None),
    warehouse_id: Optional[uuid.UUID] = Form(None),
):
    """CSV yoki Excel faylini yuklash va mahsulotlarni ajratib olish."""
    allowed_types = (
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=422, detail="Faqat CSV yoki Excel fayllari qabul qilinadi")

    async for session in get_tenant_session(str(token.tenant_id)):
        svc   = IntakeService(session, token.tenant_id, token.user_id)
        draft = await svc.start_csv_intake(file, supplier_id, warehouse_id)
        return {
            "draft_id":   str(draft.id),
            "status":     draft.status,
            "rows_count": len(draft.normalized_rows or []),
            "message":    "Fayl muvaffaqiyatli tahlil qilindi. Tekshiruv uchun GET /intake/drafts/{id}",
        }


# ── ESF orqali kirim ────────────────────────────────
@router.post("/esf", status_code=201)
async def start_esf_intake(
    token:          RequireManager,
    invoice_number: str,
    warehouse_id:   Optional[uuid.UUID] = None,
):
    """
    didox.uz / Faktura.uz dan ESF raqami orqali yetkazma ma'lumotlarini olish.
    Bu eng aniq va ishonchli usul — OCR va qo'lda kiritish shart emas.
    """
    async for session in get_tenant_session(str(token.tenant_id)):
        svc   = IntakeService(session, token.tenant_id, token.user_id)
        draft = await svc.start_esf_intake(invoice_number, warehouse_id)
        return {
            "draft_id":   str(draft.id),
            "status":     draft.status,
            "rows_count": len(draft.normalized_rows or []),
            "source":     "esf",
        }


# ── Loyihalar (Drafts) ──────────────────────────────
@router.get("/drafts")
async def list_drafts(
    token:  RequireManager,
    status: Optional[str] = Query(None, description="Filterlash: extracting|review_pending|approved|rejected"),
):
    """Kirim loyihalari ro'yxati"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc    = IntakeService(session, token.tenant_id, token.user_id)
        drafts = await svc.list_drafts(status)
        return [
            {
                "id":          str(d.id),
                "source":      d.source,
                "status":      d.status,
                "rows_count":  len(d.normalized_rows or []),
                "created_at":  d.created_at.isoformat(),
                "reviewed_at": d.reviewed_at.isoformat() if d.reviewed_at else None,
            }
            for d in drafts
        ]


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: uuid.UUID, token: RequireManager):
    """
    Kirim loyihasini tekshiruv uchun olish.
    normalized_rows: har bir qatorda _match.candidates ham bor — inson tanlov qiladi.
    """
    async for session in get_tenant_session(str(token.tenant_id)):
        svc   = IntakeService(session, token.tenant_id, token.user_id)
        draft = await svc.get_draft(draft_id)
        return {
            "id":              str(draft.id),
            "source":          draft.source,
            "status":          draft.status,
            "original_file_url": draft.original_file_url,
            "rows":            draft.normalized_rows or [],
            "error":           draft.error_message,
            "created_at":      draft.created_at.isoformat(),
        }


@router.put("/drafts/{draft_id}/rows")
async def update_draft_rows(
    draft_id: uuid.UUID,
    rows:     list[dict],
    token:    RequireManager,
):
    """Tekshiruv vaqtida qatorlarni tahrirlash (narx, miqdor, mahsulot tanlash)"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc   = IntakeService(session, token.tenant_id, token.user_id)
        draft = await svc.update_draft_rows(draft_id, rows)
        return {"draft_id": str(draft.id), "rows_count": len(rows), "status": draft.status}


@router.post("/drafts/{draft_id}/approve", status_code=201)
async def approve_draft(
    draft_id: uuid.UUID,
    data:     ApproveRequest,
    token:    RequireManager,
):
    """
    ✅ INSON TASDIQLASH — Faqat shu so'rov keyin ma'lumotlar bazasiga yoziladi.
    reviewed_rows: inson tasdiqlagan (va tahrirlagan) qatorlar.
    approved=false bo'lgan qatorlar saqlanmaydi.
    """
    async for session in get_tenant_session(str(token.tenant_id)):
        svc     = IntakeService(session, token.tenant_id, token.user_id)
        receipt = await svc.approve_draft(
            draft_id, data.reviewed_rows,
            data.warehouse_id, data.supplier_id, data.invoice_number,
        )
        return {
            "receipt_id":     str(receipt.id),
            "receipt_number": receipt.receipt_number,
            "total_cost":     str(receipt.total_cost),
            "items_count":    len(receipt.items),
            "message":        "Kirim muvaffaqiyatli tasdiqlandi va zaxira yangilandi.",
        }


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(draft_id: uuid.UUID, data: RejectRequest, token: RequireManager):
    """❌ Kirim loyihasini rad etish"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = IntakeService(session, token.tenant_id, token.user_id)
        await svc.reject_draft(draft_id, data.reason)
        return {"message": "Kirim rad etildi"}


# ── Yetkazuvchilar ──────────────────────────────────
@router.get("/suppliers")
async def list_suppliers(token: RequireManager):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc   = IntakeService(session, token.tenant_id, token.user_id)
        supps = await svc.list_suppliers()
        return [
            {"id": str(s.id), "name": s.name, "inn": s.inn, "phone": s.phone}
            for s in supps
        ]


@router.post("/suppliers", status_code=201)
async def create_supplier(data: SupplierCreate, token: RequireManager):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc  = IntakeService(session, token.tenant_id, token.user_id)
        supp = await svc.create_supplier(data.model_dump(exclude_none=True))
        return {"id": str(supp.id), "name": supp.name}


@router.put("/suppliers/{supplier_id}/column-mapping")
async def save_column_mapping(
    supplier_id: uuid.UUID,
    mapping:     dict,
    token:       RequireManager,
):
    """Yetkazuvchi CSV ustun shablonini saqlash"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = IntakeService(session, token.tenant_id, token.user_id)
        await svc.save_column_mapping(supplier_id, mapping)
        return {"message": "Shablon saqlandi"}
