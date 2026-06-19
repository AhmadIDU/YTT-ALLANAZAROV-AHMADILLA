"""
PossKassa — Sotuv modellari (SQLAlchemy)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Numeric, String, Text, UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ....shared.python.db.base import TenantBase, Base


class SaleStatus(str, PyEnum):
    COMPLETED       = "completed"
    REFUNDED        = "refunded"
    PARTIAL_REFUND  = "partial_refund"


class SyncStatus(str, PyEnum):
    PENDING = "pending"
    SYNCED  = "synced"
    FAILED  = "failed"


class PaymentMethod(str, PyEnum):
    CASH   = "cash"
    UZCARD = "uzcard"
    HUMO   = "humo"
    PAYME  = "payme"
    CLICK  = "click"
    UZUM   = "uzum"
    CREDIT = "credit"


class ShiftStatus(str, PyEnum):
    OPEN   = "open"
    CLOSED = "closed"


# ──────────────────────────────────────────────────────
# Smena
# ──────────────────────────────────────────────────────
class Shift(TenantBase):
    __tablename__ = "shifts"

    cashier_id:      Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    warehouse_id:    Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), nullable=False)
    opening_cash:    Mapped[Decimal]             = mapped_column(Numeric(15, 2), default=0)
    closing_cash:    Mapped[Optional[Decimal]]   = mapped_column(Numeric(15, 2))
    expected_cash:   Mapped[Optional[Decimal]]   = mapped_column(Numeric(15, 2))
    status:          Mapped[ShiftStatus]         = mapped_column(String(10), default=ShiftStatus.OPEN)
    opened_at:       Mapped[datetime]            = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    closed_at:       Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True))
    notes:           Mapped[Optional[str]]       = mapped_column(Text)

    # Munosabatlar
    sales:           Mapped[list["Sale"]]        = relationship("Sale", back_populates="shift")


# ──────────────────────────────────────────────────────
# Sotuv
# ──────────────────────────────────────────────────────
class Sale(TenantBase):
    __tablename__ = "sales"

    shift_id:       Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("shifts.id"))
    cashier_id:     Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id:    Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    warehouse_id:   Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), nullable=False)
    receipt_number: Mapped[str]                 = mapped_column(String(50), nullable=False)
    subtotal:       Mapped[Decimal]             = mapped_column(Numeric(15, 2), default=0)
    discount_amount:Mapped[Decimal]             = mapped_column(Numeric(15, 2), default=0)
    vat_amount:     Mapped[Decimal]             = mapped_column(Numeric(15, 2), default=0)
    total_amount:   Mapped[Decimal]             = mapped_column(Numeric(15, 2), nullable=False)
    status:         Mapped[SaleStatus]          = mapped_column(String(20), default=SaleStatus.COMPLETED)
    sync_status:    Mapped[SyncStatus]          = mapped_column(String(10), default=SyncStatus.PENDING, index=True)
    local_id:       Mapped[Optional[str]]       = mapped_column(String(100), unique=True, index=True)
    fiscal_sign:    Mapped[Optional[str]]       = mapped_column(String(255))
    fiscal_url:     Mapped[Optional[str]]       = mapped_column(Text)
    sale_time:      Mapped[datetime]            = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    synced_at:      Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True))

    # Munosabatlar
    shift:    Mapped[Optional["Shift"]]      = relationship("Shift", back_populates="sales")
    items:    Mapped[list["SaleItem"]]       = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]]        = relationship("Payment", back_populates="sale", cascade="all, delete-orphan")
    returns:  Mapped[list["Return"]]         = relationship("Return", back_populates="original_sale")


# ──────────────────────────────────────────────────────
# Sotuv qatori
# ──────────────────────────────────────────────────────
class SaleItem(TenantBase):
    __tablename__ = "sale_items"

    sale_id:        Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    product_id:     Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    quantity:       Mapped[Decimal]    = mapped_column(Numeric(15, 3), nullable=False)
    unit_price:     Mapped[Decimal]    = mapped_column(Numeric(15, 2), nullable=False)
    discount_amount:Mapped[Decimal]    = mapped_column(Numeric(15, 2), default=0)
    vat_amount:     Mapped[Decimal]    = mapped_column(Numeric(15, 2), default=0)
    total_price:    Mapped[Decimal]    = mapped_column(Numeric(15, 2), nullable=False)

    # Munosabatlar
    sale: Mapped["Sale"] = relationship("Sale", back_populates="items")


# ──────────────────────────────────────────────────────
# To'lov
# ──────────────────────────────────────────────────────
class Payment(TenantBase):
    __tablename__ = "payments"

    sale_id:          Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False)
    method:           Mapped[PaymentMethod]       = mapped_column(String(20), nullable=False)
    amount:           Mapped[Decimal]             = mapped_column(Numeric(15, 2), nullable=False)
    transaction_id:   Mapped[Optional[str]]       = mapped_column(String(255))
    status:           Mapped[str]                 = mapped_column(String(20), default="completed")
    provider_response:Mapped[Optional[dict]]      = mapped_column(JSONB)
    paid_at:          Mapped[datetime]            = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Munosabatlar
    sale: Mapped["Sale"] = relationship("Sale", back_populates="payments")


# ──────────────────────────────────────────────────────
# Qaytarish
# ──────────────────────────────────────────────────────
class Return(TenantBase):
    __tablename__ = "returns"

    original_sale_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False)
    cashier_id:       Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    reason:           Mapped[str]        = mapped_column(Text)
    refund_amount:    Mapped[Decimal]    = mapped_column(Numeric(15, 2), nullable=False)
    refund_method:    Mapped[str]        = mapped_column(String(20), default="cash")

    # Munosabatlar
    original_sale: Mapped["Sale"] = relationship("Sale", back_populates="returns")
