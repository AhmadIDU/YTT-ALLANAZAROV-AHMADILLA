"""
PossKassa — Tovar va Ombor biznes mantiqi
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.product import Category, Product, Stock, Warehouse
from ..schemas.product import (
    CategoryCreate, ProductCreate, ProductUpdate,
    StockAdjust, WarehouseCreate,
)
from ....shared.python.utils.audit import write_audit_log
from ....shared.python.events.publisher import publish_event, Events


class InventoryService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.session   = session
        self.tenant_id = tenant_id
        self.user_id   = user_id

    # ── Kategoriyalar ────────────────────────────────
    async def list_categories(self) -> list[Category]:
        result = await self.session.execute(
            select(Category)
            .where(and_(Category.tenant_id == self.tenant_id, Category.parent_id.is_(None)))
            .options(selectinload(Category.children).selectinload(Category.children))
        )
        return list(result.scalars().all())

    async def create_category(self, data: CategoryCreate) -> Category:
        cat = Category(tenant_id=self.tenant_id, **data.model_dump())
        self.session.add(cat)
        await self.session.flush()
        await write_audit_log(self.session, self.tenant_id, self.user_id,
                              "category", cat.id, "created", after=data.model_dump())
        return cat

    # ── Mahsulotlar ──────────────────────────────────
    async def list_products(
        self,
        q:           Optional[str]       = None,
        category_id: Optional[uuid.UUID] = None,
        active_only: bool                = True,
        skip:        int                 = 0,
        limit:       int                 = 50,
    ) -> list[Product]:
        query = (
            select(Product)
            .options(selectinload(Product.stock_levels).selectinload(Stock.warehouse))
            .where(Product.tenant_id == self.tenant_id)
        )
        if active_only:
            query = query.where(Product.is_active.is_(True))
        if category_id:
            query = query.where(Product.category_id == category_id)
        if q:
            pattern = f"%{q.lower()}%"
            query = query.where(
                or_(
                    func.lower(Product.name).like(pattern),
                    Product.barcode.like(f"%{q}%"),
                    func.lower(Product.sku).like(pattern),
                )
            )
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().unique().all())

    async def get_product_by_barcode(self, barcode: str) -> Product:
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.stock_levels).selectinload(Stock.warehouse))
            .where(and_(Product.tenant_id == self.tenant_id, Product.barcode == barcode))
        )
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail=f"Shtrixkod {barcode!r} topilmadi")
        return p

    async def create_product(self, data: ProductCreate) -> Product:
        # Barcode takrorlanishini tekshirish
        if data.barcode:
            existing = await self.session.execute(
                select(Product).where(
                    and_(Product.tenant_id == self.tenant_id, Product.barcode == data.barcode)
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail=f"'{data.barcode}' shtrixkodli mahsulot allaqachon mavjud",
                )

        product = Product(tenant_id=self.tenant_id, **data.model_dump())
        self.session.add(product)
        await self.session.flush()

        # Standart ombor uchun zaxira yarish
        default_wh = await self._get_default_warehouse()
        if default_wh:
            stock = Stock(
                tenant_id    = self.tenant_id,
                product_id   = product.id,
                warehouse_id = default_wh.id,
                quantity     = Decimal("0"),
            )
            self.session.add(stock)

        await write_audit_log(self.session, self.tenant_id, self.user_id,
                              "product", product.id, "created", after=data.model_dump(mode="json"))
        return product

    async def update_product(self, product_id: uuid.UUID, data: ProductUpdate) -> Product:
        product = await self._get_product_or_404(product_id)
        before  = {"price": str(product.price), "is_active": product.is_active}

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(product, field, value)

        await write_audit_log(self.session, self.tenant_id, self.user_id,
                              "product", product_id, "updated",
                              before=before, after=data.model_dump(exclude_none=True, mode="json"))
        return product

    async def delete_product(self, product_id: uuid.UUID) -> None:
        """Soft delete"""
        product = await self._get_product_or_404(product_id)
        product.is_active = False
        await write_audit_log(self.session, self.tenant_id, self.user_id,
                              "product", product_id, "deleted")

    # ── Zaxira ───────────────────────────────────────
    async def get_stock(self, product_id: uuid.UUID) -> list[Stock]:
        result = await self.session.execute(
            select(Stock)
            .options(selectinload(Stock.warehouse))
            .where(and_(Stock.tenant_id == self.tenant_id, Stock.product_id == product_id))
        )
        return list(result.scalars().all())

    async def get_low_stock(self) -> list[dict]:
        """Kam zaxirali mahsulotlar"""
        result = await self.session.execute(
            select(Stock, Product, Warehouse)
            .join(Product, Stock.product_id == Product.id)
            .join(Warehouse, Stock.warehouse_id == Warehouse.id)
            .where(
                and_(
                    Stock.tenant_id == self.tenant_id,
                    Product.is_active.is_(True),
                    Product.track_stock.is_(True),
                    Stock.quantity <= Stock.low_stock_threshold,
                )
            )
        )
        rows = result.all()
        return [
            {
                "product_id":   str(stock.product_id),
                "product_name": product.name,
                "warehouse":    warehouse.name,
                "quantity":     str(stock.quantity),
                "threshold":    str(stock.low_stock_threshold),
            }
            for stock, product, warehouse in rows
        ]

    async def adjust_stock(self, data: StockAdjust) -> Stock:
        """Zaxirani qo'lda moslashtirish (inventarizatsiya)"""
        result = await self.session.execute(
            select(Stock).where(
                and_(
                    Stock.tenant_id   == self.tenant_id,
                    Stock.product_id  == data.product_id,
                    Stock.warehouse_id== data.warehouse_id,
                )
            )
        )
        stock = result.scalar_one_or_none()

        if not stock:
            stock = Stock(
                tenant_id    = self.tenant_id,
                product_id   = data.product_id,
                warehouse_id = data.warehouse_id,
                quantity     = data.quantity,
            )
            self.session.add(stock)
        else:
            before_qty = stock.quantity
            stock.quantity = data.quantity
            await write_audit_log(
                self.session, self.tenant_id, self.user_id,
                "stock", stock.id, "adjusted",
                before={"quantity": str(before_qty)},
                after={"quantity": str(data.quantity), "reason": data.reason},
            )

        await self.session.flush()

        # Kam zaxira voqeasi
        if stock.quantity <= stock.low_stock_threshold:
            await publish_event(Events.STOCK_LOW, {
                "product_id":   str(data.product_id),
                "warehouse_id": str(data.warehouse_id),
                "quantity":     str(stock.quantity),
                "tenant_id":    str(self.tenant_id),
            })

        return stock

    async def deduct_stock_for_sale(
        self,
        items: list[dict],  # [{"product_id": ..., "quantity": ..., "warehouse_id": ...}]
    ) -> None:
        """Sotuv voqeasiga javoban zaxirani kamaytirish (RabbitMQ consumer chaqiradi)"""
        for item in items:
            await self.session.execute(
                update(Stock)
                .where(
                    and_(
                        Stock.tenant_id   == self.tenant_id,
                        Stock.product_id  == uuid.UUID(item["product_id"]),
                        Stock.warehouse_id== uuid.UUID(item.get("warehouse_id", str(uuid.uuid4()))),
                    )
                )
                .values(quantity=Stock.quantity - Decimal(str(item["quantity"])))
            )

    async def get_products_for_sync(self, updated_after: Optional[datetime] = None) -> list[Product]:
        """POS terminal uchun delta sinxronizatsiya"""
        query = (
            select(Product)
            .options(selectinload(Product.stock_levels).selectinload(Stock.warehouse))
            .where(and_(Product.tenant_id == self.tenant_id, Product.is_active.is_(True)))
        )
        if updated_after:
            query = query.where(Product.updated_at >= updated_after)
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    # ── Omborxonalar ─────────────────────────────────
    async def list_warehouses(self) -> list[Warehouse]:
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.tenant_id == self.tenant_id)
        )
        return list(result.scalars().all())

    async def create_warehouse(self, data: WarehouseCreate) -> Warehouse:
        if data.is_default:
            # Boshqa omborxonalardan standart belgisini olib tashlash
            await self.session.execute(
                update(Warehouse)
                .where(Warehouse.tenant_id == self.tenant_id)
                .values(is_default=False)
            )
        wh = Warehouse(tenant_id=self.tenant_id, **data.model_dump())
        self.session.add(wh)
        await self.session.flush()
        return wh

    # ── Yordamchilar ─────────────────────────────────
    async def _get_product_or_404(self, product_id: uuid.UUID) -> Product:
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.stock_levels).selectinload(Stock.warehouse))
            .where(and_(Product.id == product_id, Product.tenant_id == self.tenant_id))
        )
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
        return p

    async def _get_default_warehouse(self) -> Optional[Warehouse]:
        result = await self.session.execute(
            select(Warehouse).where(
                and_(Warehouse.tenant_id == self.tenant_id, Warehouse.is_default.is_(True))
            )
        )
        return result.scalar_one_or_none()
