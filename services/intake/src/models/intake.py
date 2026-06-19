"""
PossKassa — Tovar Qabuli (Kirim) modellari
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ....shared.python.db.base import TenantBase


class IntakeSource(str, PyEnum):
    PHOTO  = "photo"
    CSV    = "csv"
    ESF    = "esf"
    MANUAL = "manual"


class IntakeStatus(str, PyEnum):
    EXTRACTING     = "extracting"
    REVIEW_PENDING = "review_pending"
    APPROVED       = "approved"
    REJECTED       = "rejected"


class ReceiptStatus(str, PyEnum):
    DRAFT     = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Supplier(TenantBase):
    __tablename__ = "suppliers"

    name:           Mapped[str]            = mapped_column(String(255), nullable=False)
    inn:            Mapped[Optional[str]]  = mapped_column(String(20))
    phone:          Mapped[Optional[str]]  = mapped_column(String(20))
    email:          Mapped[Optional[str]]  = mapped_column(String(255))
    address:        Mapped[Optional[str]]  = mapped_column(Text)
    column_mapping: Mapped[Optional[dict]] = mapped_column(JSONB)  # CSV ustun shabloni
    is_active:      Mapped[bool]           = mapped_column(Boolean, default=True)

    receipts: Mapped[list["StockReceipt"]] = relationship("StockReceipt", back_populates="supplier")


class IntakeDraft(TenantBase):
    """
    OCR / Import loyihasi — INSON TEKSHIRUVIGACHA bazaga saqlanmaydi.
    Tasdiqlangandan keyingina StockReceipt yaratiladi.
    """
    __tablename__ = "intake_drafts"

    created_by:      Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), nullable=False)
    source:          Mapped[IntakeSource]       = mapped_column(String(20), nullable=False)
    original_file_url: Mapped[Optional[str]]   = mapped_column(Text)
    raw_extracted:   Mapped[Optional[dict]]    = mapped_column(JSONB)   # LLM / parser xom natijasi
    normalized_rows: Mapped[Optional[list]]    = mapped_column(JSONB)   # Normallashtirilgan qatorlar
    review_result:   Mapped[Optional[dict]]    = mapped_column(JSONB)   # Inson tekshiruvi natijalari
    status:          Mapped[IntakeStatus]      = mapped_column(String(30), default=IntakeStatus.EXTRACTING)
    reviewed_at:     Mapped[Optional[datetime]]= mapped_column(DateTime(timezone=True))
    supplier_id:     Mapped[Optional[uuid.UUID]]= mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    warehouse_id:    Mapped[Optional[uuid.UUID]]= mapped_column(UUID(as_uuid=True))
    error_message:   Mapped[Optional[str]]     = mapped_column(Text)


class StockReceipt(TenantBase):
    """Tasdiqlangan kirim hujjati"""
    __tablename__ = "stock_receipts"

    supplier_id:    Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    warehouse_id:   Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by:     Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), nullable=False)
    receipt_number: Mapped[str]                 = mapped_column(String(50), nullable=False)
    invoice_number: Mapped[Optional[str]]       = mapped_column(String(100))
    total_amount:   Mapped[Decimal]             = mapped_column(Numeric(15, 2), default=0)
    total_cost:     Mapped[Decimal]             = mapped_column(Numeric(15, 2), default=0)
    status:         Mapped[ReceiptStatus]       = mapped_column(String(20), default=ReceiptStatus.CONFIRMED)
    source:         Mapped[IntakeSource]        = mapped_column(String(20), default=IntakeSource.MANUAL)
    esf_number:     Mapped[Optional[str]]       = mapped_column(String(100))
    receipt_date:   Mapped[datetime]            = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    draft_id:       Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    supplier: Mapped[Optional["Supplier"]]          = relationship("Supplier", back_populates="receipts")
    items:    Mapped[list["StockReceiptItem"]]       = relationship("StockReceiptItem", back_populates="receipt", cascade="all, delete-orphan")


class StockReceiptItem(TenantBase):
    __tablename__ = "stock_receipt_items"

    receipt_id:   Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("stock_receipts.id", ondelete="CASCADE"), nullable=False)
    product_id:   Mapped[Optional[uuid.UUID]]= mapped_column(UUID(as_uuid=True))
    quantity:     Mapped[Decimal]           = mapped_column(Numeric(15, 3), nullable=False)
    unit_cost:    Mapped[Decimal]           = mapped_column(Numeric(15, 2), nullable=False)
    total_cost:   Mapped[Decimal]           = mapped_column(Numeric(15, 2), nullable=False)
    vat_rate:     Mapped[Decimal]           = mapped_column(Numeric(5, 2), default=12)
    batch_number: Mapped[Optional[str]]     = mapped_column(String(100))
    expiry_date:  Mapped[Optional[str]]     = mapped_column(String(20))

    receipt: Mapped["StockReceipt"] = relationship("StockReceipt", back_populates="items")
