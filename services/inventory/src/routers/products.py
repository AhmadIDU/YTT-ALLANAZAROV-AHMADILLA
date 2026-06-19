"""
PossKassa — Tovar va Ombor API router lari
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.product import (
    CategoryCreate, CategoryResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    WarehouseCreate, WarehouseResponse,
    StockAdjust, StockResponse, ProductSyncResponse,
)
from ..services.inventory_service import InventoryService
from ....shared.python.auth.dependencies import RequireCashier, RequireManager, RequireAdmin
from ....shared.python.db.base import get_tenant_session

router = APIRouter()


# ── Kategoriyalar ──────────────────────────────────
@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(token: RequireCashier):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc  = InventoryService(session, token.tenant_id, token.user_id)
        cats = await svc.list_categories()
        return [CategoryResponse.model_validate(c) for c in cats]


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(data: CategoryCreate, token: RequireManager):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = InventoryService(session, token.tenant_id, token.user_id)
        cat = await svc.create_category(data)
        return CategoryResponse.model_validate(cat)


# ── Mahsulotlar ────────────────────────────────────
@router.get("", response_model=list[ProductResponse])
async def list_products(
    token:       RequireCashier,
    q:           Optional[str]       = Query(None, description="Qidirish: nom yoki barcode"),
    category_id: Optional[uuid.UUID] = None,
    active_only: bool                = True,
    skip:        int                 = Query(0, ge=0),
    limit:       int                 = Query(50, ge=1, le=200),
):
    """Mahsulotlar ro'yxati — qidirish va filtrlash bilan"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc      = InventoryService(session, token.tenant_id, token.user_id)
        products = await svc.list_products(q, category_id, active_only, skip, limit)
        return [_enrich_product(p) for p in products]


@router.get("/sync", response_model=ProductSyncResponse)
async def sync_products(
    token:         RequireCashier,
    updated_after: Optional[datetime] = Query(None, description="Delta sinxronizatsiya"),
):
    """POS terminal uchun mahsulotlar delta sinxronizatsiyasi"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc      = InventoryService(session, token.tenant_id, token.user_id)
        products = await svc.get_products_for_sync(updated_after)
        return ProductSyncResponse(
            products    = [_enrich_product(p) for p in products],
            last_sync   = datetime.utcnow().isoformat(),
            total_count = len(products),
        )


@router.get("/barcode/{barcode}", response_model=ProductResponse)
async def get_by_barcode(barcode: str, token: RequireCashier):
    """Shtrixkod bo'yicha mahsulot topish"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = InventoryService(session, token.tenant_id, token.user_id)
        p   = await svc.get_product_by_barcode(barcode)
        return _enrich_product(p)


@router.get("/low-stock", response_model=list[dict])
async def get_low_stock(token: RequireManager):
    """Kam zaxirali mahsulotlar ro'yxati"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc  = InventoryService(session, token.tenant_id, token.user_id)
        return await svc.get_low_stock()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: uuid.UUID, token: RequireCashier):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = InventoryService(session, token.tenant_id, token.user_id)
        p   = await svc._get_product_or_404(product_id)
        return _enrich_product(p)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, token: RequireManager):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = InventoryService(session, token.tenant_id, token.user_id)
        p   = await svc.create_product(data)
        return _enrich_product(p)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: uuid.UUID, data: ProductUpdate, token: RequireManager):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = InventoryService(session, token.tenant_id, token.user_id)
        p   = await svc.update_product(product_id, data)
        return _enrich_product(p)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: uuid.UUID, token: RequireAdmin):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = InventoryService(session, token.tenant_id, token.user_id)
        await svc.delete_product(product_id)


# ── Zaxira ─────────────────────────────────────────
@router.get("/{product_id}/stock", response_model=list[StockResponse])
async def get_product_stock(product_id: uuid.UUID, token: RequireManager):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc    = InventoryService(session, token.tenant_id, token.user_id)
        stocks = await svc.get_stock(product_id)
        return [
            StockResponse(
                warehouse_id        = s.warehouse_id,
                warehouse_name      = s.warehouse.name,
                quantity            = s.quantity,
                reserved_quantity   = s.reserved_quantity,
                available           = s.quantity - s.reserved_quantity,
                low_stock_threshold = s.low_stock_threshold,
                is_low              = s.quantity <= s.low_stock_threshold,
            )
            for s in stocks
        ]


@router.post("/stock/adjust", response_model=dict)
async def adjust_stock(data: StockAdjust, token: RequireAdmin):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = InventoryService(session, token.tenant_id, token.user_id)
        await svc.adjust_stock(data)
        return {"message": "Zaxira muvaffaqiyatli moslashtirildi"}


# ── Omborxonalar ───────────────────────────────────
@router.get("/warehouses", response_model=list[WarehouseResponse])
async def list_warehouses(token: RequireCashier):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = InventoryService(session, token.tenant_id, token.user_id)
        whs = await svc.list_warehouses()
        return [WarehouseResponse.model_validate(w) for w in whs]


@router.post("/warehouses", response_model=WarehouseResponse, status_code=201)
async def create_warehouse(data: WarehouseCreate, token: RequireAdmin):
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = InventoryService(session, token.tenant_id, token.user_id)
        wh  = await svc.create_warehouse(data)
        return WarehouseResponse.model_validate(wh)


# ── Yordamchi funksiya ─────────────────────────────
def _enrich_product(p) -> ProductResponse:
    """Mahsulotga margin foizini qo'shib qaytarish"""
    from decimal import Decimal as D
    margin = None
    if p.price and p.cost_price and p.price > 0:
        margin = ((p.price - p.cost_price) / p.price * 100).quantize(D("0.01"))

    stock_list = []
    for s in (p.stock_levels or []):
        stock_list.append(StockResponse(
            warehouse_id        = s.warehouse_id,
            warehouse_name      = s.warehouse.name if s.warehouse else "—",
            quantity            = s.quantity,
            reserved_quantity   = s.reserved_quantity,
            available           = s.quantity - s.reserved_quantity,
            low_stock_threshold = s.low_stock_threshold,
            is_low              = s.quantity <= s.low_stock_threshold,
        ))

    return ProductResponse(
        id          = p.id,
        category_id = p.category_id,
        name        = p.name,
        name_uz     = p.name_uz,
        name_ru     = p.name_ru,
        sku         = p.sku,
        barcode     = p.barcode,
        unit        = p.unit,
        price       = p.price,
        cost_price  = p.cost_price,
        vat_rate    = p.vat_rate,
        is_active   = p.is_active,
        track_stock = p.track_stock,
        image_url   = p.image_url,
        margin_pct  = margin,
        stock_levels= stock_list,
    )
