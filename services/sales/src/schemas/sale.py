"""
PossKassa — Sotuv Pydantic sxemalari (request/response)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────────────
# Sotuv yaratish (Request)
# ──────────────────────────────────────────────────────
class SaleItemCreate(BaseModel):
    product_id:     uuid.UUID
    quantity:       Decimal = Field(gt=0)
    unit_price:     Decimal = Field(ge=0)
    discount_amount:Decimal = Field(ge=0, default=0)


class PaymentCreate(BaseModel):
    method: str
    amount: Decimal = Field(gt=0)
    transaction_id: Optional[str] = None


class SaleCreate(BaseModel):
    shift_id:       Optional[uuid.UUID] = None
    warehouse_id:   uuid.UUID
    customer_id:    Optional[uuid.UUID] = None
    local_id:       str  # Idempotency kaliti (terminal UUID)
    items:          list[SaleItemCreate] = Field(min_length=1)
    payments:       list[PaymentCreate] = Field(min_length=1)
    discount_amount:Decimal = Field(ge=0, default=0)
    sale_time:      Optional[datetime] = None  # Oflayn sotuv vaqti

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v):
        if not v:
            raise ValueError("Kamida bitta mahsulot bo'lishi kerak")
        return v


# ──────────────────────────────────────────────────────
# Paketli sinxronlash (Oflayn → Server)
# ──────────────────────────────────────────────────────
class SaleSyncBatch(BaseModel):
    sales: list[SaleCreate] = Field(min_length=1, max_length=100)


class SyncResult(BaseModel):
    local_id:   str
    remote_id:  Optional[str] = None
    success:    bool
    fiscal_url: Optional[str] = None
    error:      Optional[str] = None


class SaleSyncResponse(BaseModel):
    results: list[SyncResult]
    synced:  int
    failed:  int


# ──────────────────────────────────────────────────────
# Sotuv javobi (Response)
# ──────────────────────────────────────────────────────
class SaleItemResponse(BaseModel):
    id:             uuid.UUID
    product_id:     uuid.UUID
    quantity:       Decimal
    unit_price:     Decimal
    discount_amount:Decimal
    vat_amount:     Decimal
    total_price:    Decimal

    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    id:             uuid.UUID
    method:         str
    amount:         Decimal
    transaction_id: Optional[str]
    status:         str
    paid_at:        datetime

    model_config = {"from_attributes": True}


class SaleResponse(BaseModel):
    id:             uuid.UUID
    shift_id:       Optional[uuid.UUID]
    cashier_id:     uuid.UUID
    customer_id:    Optional[uuid.UUID]
    warehouse_id:   uuid.UUID
    receipt_number: str
    subtotal:       Decimal
    discount_amount:Decimal
    vat_amount:     Decimal
    total_amount:   Decimal
    status:         str
    sync_status:    str
    local_id:       Optional[str]
    fiscal_url:     Optional[str]
    sale_time:      datetime
    items:          list[SaleItemResponse]
    payments:       list[PaymentResponse]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────
# Smena sxemalari
# ──────────────────────────────────────────────────────
class ShiftOpen(BaseModel):
    warehouse_id: uuid.UUID
    opening_cash: Decimal = Field(ge=0, default=0)


class ShiftClose(BaseModel):
    closing_cash: Decimal = Field(ge=0)
    notes:        Optional[str] = None


class ShiftResponse(BaseModel):
    id:           uuid.UUID
    cashier_id:   uuid.UUID
    warehouse_id: uuid.UUID
    opening_cash: Decimal
    closing_cash: Optional[Decimal]
    expected_cash:Optional[Decimal]
    status:       str
    opened_at:    datetime
    closed_at:    Optional[datetime]
    total_sales:  Optional[int]      = None
    total_revenue:Optional[Decimal]  = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────
# Qaytarish sxemalari
# ──────────────────────────────────────────────────────
class RefundCreate(BaseModel):
    reason:        str = Field(min_length=3)
    refund_amount: Decimal = Field(gt=0)
    refund_method: str = "cash"
    items:         Optional[list[dict]] = None  # Qisman qaytarish uchun
