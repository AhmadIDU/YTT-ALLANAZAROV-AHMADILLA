"""
PossKassa — Tovar va Ombor modellari
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ....shared.python.db.base import TenantBase


class Unit(str, PyEnum):
    PCS = "pcs"   # dona
    KG  = "kg"    # kilogramm
    L   = "l"     # litr
    M   = "m"     # metr
    BOX = "box"   # quti


class Category(TenantBase):
    __tablename__ = "categories"

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    name:      Mapped[str]                 = mapped_column(String(255), nullable=False)
    name_uz:   Mapped[Optional[str]]       = mapped_column(String(255))
    name_ru:   Mapped[Optional[str]]       = mapped_column(String(255))
    icon:      Mapped[Optional[str]]       = mapped_column(String(100))

    products:  Mapped[list["Product"]]     = relationship("Product", back_populates="category")
    children:  Mapped[list["Category"]]    = relationship("Category", back_populates="parent")
    parent:    Mapped[Optional["Category"]]= relationship("Category", back_populates="children", remote_side="Category.id")


class Product(TenantBase):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "barcode", name="uq_product_barcode_tenant"),
    )

    category_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    name:         Mapped[str]                  = mapped_column(String(255), nullable=False)
    name_uz:      Mapped[Optional[str]]        = mapped_column(String(255))
    name_ru:      Mapped[Optional[str]]        = mapped_column(String(255))
    sku:          Mapped[Optional[str]]        = mapped_column(String(100), index=True)
    barcode:      Mapped[Optional[str]]        = mapped_column(String(100), index=True)
    unit:         Mapped[Unit]                 = mapped_column(String(10), default=Unit.PCS)
    price:        Mapped[Decimal]              = mapped_column(Numeric(15, 2), default=0, nullable=False)
    cost_price:   Mapped[Decimal]              = mapped_column(Numeric(15, 2), default=0)
    vat_rate:     Mapped[Decimal]              = mapped_column(Numeric(5, 2), default=12)
    is_active:    Mapped[bool]                 = mapped_column(Boolean, default=True)
    track_stock:  Mapped[bool]                 = mapped_column(Boolean, default=True)
    image_url:    Mapped[Optional[str]]        = mapped_column(Text)

    category:     Mapped[Optional["Category"]] = relationship("Category", back_populates="products")
    stock_levels: Mapped[list["Stock"]]        = relationship("Stock", back_populates="product", cascade="all, delete-orphan")


class Warehouse(TenantBase):
    __tablename__ = "warehouses"

    name:       Mapped[str]  = mapped_column(String(255), nullable=False)
    address:    Mapped[Optional[str]] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    stock_levels: Mapped[list["Stock"]] = relationship("Stock", back_populates="warehouse")


class Stock(TenantBase):
    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_stock_product_warehouse"),
    )

    product_id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    warehouse_id:        Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    quantity:            Mapped[Decimal]   = mapped_column(Numeric(15, 3), default=0)
    reserved_quantity:   Mapped[Decimal]   = mapped_column(Numeric(15, 3), default=0)
    low_stock_threshold: Mapped[Decimal]   = mapped_column(Numeric(15, 3), default=5)

    product:   Mapped["Product"]   = relationship("Product",   back_populates="stock_levels")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="stock_levels")
