"""
PossKassa — Tahlil va Admin API router lari
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import io

from ..services.reports_service import ReportsService
from ....shared.python.auth.dependencies import RequireManager, RequireAdmin
from ....shared.python.db.base import get_tenant_session

router = APIRouter()


# ─── Sotuv xulosasi ──────────────────────────────────
@router.get("/reports/sales-summary")
async def sales_summary(
    token:        RequireManager,
    from_:        date = Query(..., alias="from"),
    to:           date = Query(...),
    warehouse_id: Optional[uuid.UUID] = None,
    cashier_id:   Optional[uuid.UUID] = None,
    group_by:     str  = Query("day", regex="^(day|week|month)$"),
):
    """Sotuv xulosasi — kunlik/oylik daromad grafigi"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = ReportsService(session, token.tenant_id)
        return await svc.sales_summary(from_, to, warehouse_id, cashier_id, group_by)


# ─── Eng ko'p sotiladigan mahsulotlar ────────────────
@router.get("/reports/top-products")
async def top_products(
    token:        RequireManager,
    from_:        date = Query(..., alias="from"),
    to:           date = Query(...),
    limit:        int  = Query(20, ge=1, le=100),
    warehouse_id: Optional[uuid.UUID] = None,
):
    """Eng ko'p sotiladigan va daromad keltiruvchi mahsulotlar"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = ReportsService(session, token.tenant_id)
        return await svc.top_products(from_, to, limit, warehouse_id)


# ─── ABC tahlil ───────────────────────────────────────
@router.get("/reports/abc-analysis")
async def abc_analysis(
    token: RequireManager,
    from_: date = Query(..., alias="from"),
    to:    date = Query(...),
):
    """
    ABC tahlil:
    A — daromadning 80%
    B — 15%
    C — 5%
    """
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = ReportsService(session, token.tenant_id)
        return await svc.abc_analysis(from_, to)


# ─── Marjinallik hisoboti ─────────────────────────────
@router.get("/reports/margin")
async def margin_report(
    token: RequireManager,
    from_: date = Query(..., alias="from"),
    to:    date = Query(...),
):
    """Mahsulotlar bo'yicha marjinallik tahlili"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = ReportsService(session, token.tenant_id)
        return await svc.margin_report(from_, to)


# ─── Kassir samaradorligi ─────────────────────────────
@router.get("/reports/cashier-performance")
async def cashier_performance(
    token: RequireAdmin,
    from_: date = Query(..., alias="from"),
    to:    date = Query(...),
):
    """Kassirlar samaradorligi hisoboti"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = ReportsService(session, token.tenant_id)
        return await svc.cashier_performance(from_, to)


# ─── Ombor qiymati ────────────────────────────────────
@router.get("/reports/stock-value")
async def stock_value(
    token:        RequireManager,
    warehouse_id: Optional[uuid.UUID] = None,
):
    """Ombor qiymati va potensial foyda hisoboti"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = ReportsService(session, token.tenant_id)
        return await svc.stock_value_report(warehouse_id)


# ─── Export ───────────────────────────────────────────
@router.post("/reports/export")
async def export_report(
    token:       RequireManager,
    report_type: str,
    from_:       date,
    to:          date,
    format_:     str = Query("excel", alias="format", regex="^(excel|csv)$"),
):
    """Hisobotni Excel yoki CSV ga eksport qilish"""
    import pandas as pd

    async for session in get_tenant_session(str(token.tenant_id)):
        svc = ReportsService(session, token.tenant_id)

        if report_type == "top_products":
            data = await svc.top_products(from_, to, limit=1000)
        elif report_type == "margin":
            result = await svc.margin_report(from_, to)
            data   = result.get("items", [])
        elif report_type == "cashier_performance":
            data = await svc.cashier_performance(from_, to)
        else:
            data = []

    df = pd.DataFrame(data)
    buf = io.BytesIO()

    if format_ == "excel":
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        filename = f"posskassa_{report_type}_{from_}_{to}.xlsx"
        media    = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        df.to_csv(buf, index=False)
        buf.seek(0)
        filename = f"posskassa_{report_type}_{from_}_{to}.csv"
        media    = "text/csv"

    return StreamingResponse(
        buf,
        media_type = media,
        headers    = {"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Audit jurnali ────────────────────────────────────
@router.get("/audit-log")
async def get_audit_log(
    token:       RequireAdmin,
    entity_type: Optional[str]       = None,
    entity_id:   Optional[uuid.UUID] = None,
    user_id:     Optional[uuid.UUID] = None,
    from_:       Optional[date]      = Query(None, alias="from"),
    to:          Optional[date]      = None,
    skip:        int                 = Query(0, ge=0),
    limit:       int                 = Query(50, ge=1, le=200),
):
    """Audit jurnali — barcha pul va zaxira amallari"""
    async for session in get_tenant_session(str(token.tenant_id)):
        svc = ReportsService(session, token.tenant_id)
        return await svc.get_audit_log(
            entity_type, entity_id, user_id, from_, to, skip, limit
        )


# ─── Dashboard (real-vaqt) ────────────────────────────
@router.get("/dashboard")
async def dashboard(token: RequireManager):
    """Bugungi ko'rsatkichlar — real-vaqt dashboard"""
    today = date.today()
    async for session in get_tenant_session(str(token.tenant_id)):
        svc     = ReportsService(session, token.tenant_id)
        summary = await svc.sales_summary(today, today)
        top5    = await svc.top_products(today, today, limit=5)

        return {
            "today": {
                "sales_count":   summary["total_sales"],
                "revenue":       summary["total_revenue"],
                "avg_check":     summary["avg_check"],
                "top_products":  top5,
            },
            "payment_breakdown": summary.get("payment_breakdown", []),
            "generated_at":      datetime.now(timezone.utc).isoformat(),
        }
