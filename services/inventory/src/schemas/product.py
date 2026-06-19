"""
PossKassa — Tovar Pydantic sxemalari
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ── Kategoriya ─────────────────────────────────────
class CategoryCreate(BaseModel):
    parent_id: Optional[uuid.UUID] = None
    name:      str = Field(min_length=1, max_length=255)
    name_uz:   Optional[str] = None
    name_ru:   Optional[str] = None
    icon:      Optional[str] = None


class CategoryResponse(BaseModel):
    id:        uuid.UUID
    parent_id: Optional[uuid.UUID]
    name:      str
    name_uz:   Optional[str]
    name_ru:   Optional[str]
    icon:      Optional[str]
    children:  list["CategoryResponse"] = []
    model_config = {"from_attributes": True}

CategoryResponse.model_rebuild()


# ── Mahsulot ────────────────────────────────────────
class ProductCreate(BaseModel):
    category_id:  Optional[uuid.UUID] = None
    name:         str = Field(min_length=1, max_length=255)
    name_uz:      Optional[str] = None
    name_ru:      Optional[str] = None
    sku:          Optional[str] = None
    barcode:      Optional[str] = None
    unit:         str = "pcs"
    price:        Decimal = Field(ge=0)
    cost_price:   Decimal = Field(ge=0, default=0)
    vat_rate:     Decimal = Field(ge=0, le=100, default=12)
    is_active:    bool = True
    track_stock:  bool = True
    image_url:    Optional[str] = None


class ProductUpdate(BaseModel):
    name:       Optional[str]            = None
    price:      Optional[Decimal]        = Field(None, ge=0)
    cost_price: Optional[Decimal]        = Field(None, ge=0)
    barcode:    Optional[str]            = None
    is_active:  Optional[bool]           = None
    category_id:Optional[uuid.UUID]      = None
    image_url:  Optional[str]            = None


class StockResponse(BaseModel):
    warehouse_id:        uuid.UUID
    warehouse_name:      str
    quantity:            Decimal
    reserved_quantity:   Decimal
    available:           Decimal
    low_stock_threshold: Decimal
    is_low:              bool
    model_config = {"from_attributes": True}


class ProductResponse(BaseModel):
    id:           uuid.UUID
    category_id:  Optional[uuid.UUID]
    name:         str
    name_uz:      Optional[str]
    name_ru:      Optional[str]
    sku:          Optional[str]
    barcode:      Optional[str]
    unit:         str
    price:        Decimal
    cost_price:   Decimal
    vat_rate:     Decimal
    is_active:    bool
    track_stock:  bool
    image_url:    Optional[str]
    margin_pct:   Optional[Decimal] = None
    stock_levels: list[StockResponse] = []
    model_config = {"from_attributes": True}


# ── Ombor ────────────────────────────────────────────
class WarehouseCreate(BaseModel):
    name:       str = Field(min_length=1, max_length=255)
    address:    Optional[str] = None
    is_default: bool = False


class WarehouseResponse(BaseModel):
    id:         uuid.UUID
    name:       str
    address:    Optional[str]
    is_default: bool
    model_config = {"from_attributes": True}


# ── Zaxira moslashtirish ────────────────────────────
class StockAdjust(BaseModel):
    product_id:   uuid.UUID
    warehouse_id: uuid.UUID
    quantity:     Decimal
    reason:       str = Field(min_length=3)


# ── Delta sinxronizatsiya (POS uchun) ──────────────
class ProductSyncResponse(BaseModel):
    products:    list[ProductResponse]
    last_sync:   str
    total_count: int
