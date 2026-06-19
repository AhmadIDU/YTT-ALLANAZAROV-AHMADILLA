"""
PossKassa — Hisobotlar va Tahlil xizmati
Kunlik/oylik daromad, ABC tahlil, marjinallik, kassirlar samaradorligi
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, select, text, desc
from sqlalchemy.ext.asyncio import AsyncSession


class ReportsService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session   = session
        self.tenant_id = tenant_id

    # ─── Sotuv xulosasi ──────────────────────────────
    async def sales_summary(
        self,
        date_from:    date,
        date_to:      date,
        warehouse_id: Optional[uuid.UUID] = None,
        cashier_id:   Optional[uuid.UUID] = None,
        group_by:     str = "day",          # day | week | month
    ) -> dict:
        """
        Kunlik/oylik sotuv xulosasi.
        """
        group_expr = {
            "day":   "DATE(sale_time AT TIME ZONE 'Asia/Tashkent')",
            "week":  "DATE_TRUNC('week', sale_time AT TIME ZONE 'Asia/Tashkent')",
            "month": "DATE_TRUNC('month', sale_time AT TIME ZONE 'Asia/Tashkent')",
        }.get(group_by, "DATE(sale_time AT TIME ZONE 'Asia/Tashkent')")

        filters = [
            f"tenant_id = '{self.tenant_id}'",
            f"sale_time >= '{date_from}'::date",
            f"sale_time <  '{date_to}'::date + INTERVAL '1 day'",
            "status != 'refunded'",
        ]
        if warehouse_id:
            filters.append(f"warehouse_id = '{warehouse_id}'")
        if cashier_id:
            filters.append(f"cashier_id = '{cashier_id}'")

        where = " AND ".join(filters)

        # Asosiy xulosalar
        totals_row = await self.session.execute(text(f"""
            SELECT
                COUNT(*)                AS total_sales,
                COALESCE(SUM(total_amount), 0)    AS total_revenue,
                COALESCE(SUM(discount_amount), 0) AS total_discount,
                COALESCE(SUM(vat_amount), 0)      AS total_vat,
                COALESCE(AVG(total_amount), 0)    AS avg_check
            FROM sales
            WHERE {where}
        """))
        totals = dict(totals_row.fetchone()._mapping)

        # Davr bo'yicha guruhlash
        series_rows = await self.session.execute(text(f"""
            SELECT
                {group_expr}                          AS period,
                COUNT(*)                              AS sales_count,
                COALESCE(SUM(total_amount), 0)        AS revenue,
                COALESCE(AVG(total_amount), 0)        AS avg_check
            FROM sales
            WHERE {where}
            GROUP BY 1
            ORDER BY 1
        """))
        series = [dict(r._mapping) for r in series_rows.fetchall()]

        # To'lov usullari bo'yicha
        pay_rows = await self.session.execute(text(f"""
            SELECT
                p.method,
                COUNT(*)                       AS count,
                COALESCE(SUM(p.amount), 0)     AS total
            FROM payments p
            JOIN sales s ON p.sale_id = s.id
            WHERE s.{where.replace('tenant_id', 's.tenant_id')
                         .replace('sale_time', 's.sale_time')
                         .replace('status', 's.status')
                         .replace('warehouse_id', 's.warehouse_id')
                         .replace('cashier_id', 's.cashier_id')}
            GROUP BY p.method
            ORDER BY total DESC
        """))
        payment_breakdown = [dict(r._mapping) for r in pay_rows.fetchall()]

        return {
            "period":             {"from": str(date_from), "to": str(date_to)},
            "total_sales":        int(totals["total_sales"]),
            "total_revenue":      str(totals["total_revenue"]),
            "total_discount":     str(totals["total_discount"]),
            "total_vat":          str(totals["total_vat"]),
            "avg_check":          str(round(Decimal(str(totals["avg_check"])), 0)),
            "series":             [
                {
                    "period":      str(r["period"]),
                    "sales_count": int(r["sales_count"]),
                    "revenue":     str(r["revenue"]),
                    "avg_check":   str(round(Decimal(str(r["avg_check"])), 0)),
                }
                for r in series
            ],
            "payment_breakdown":  payment_breakdown,
        }

    # ─── Eng ko'p sotiladigan mahsulotlar ────────────
    async def top_products(
        self,
        date_from:    date,
        date_to:      date,
        limit:        int  = 20,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> list[dict]:
        wh_filter = f"AND s.warehouse_id = '{warehouse_id}'" if warehouse_id else ""

        rows = await self.session.execute(text(f"""
            SELECT
                si.product_id,
                p.name                             AS product_name,
                p.barcode,
                p.unit,
                SUM(si.quantity)                   AS total_qty,
                SUM(si.total_price)                AS total_revenue,
                SUM(si.quantity * p.cost_price)    AS total_cost,
                SUM(si.total_price) - SUM(si.quantity * p.cost_price) AS gross_profit,
                COUNT(DISTINCT s.id)               AS sale_count
            FROM sale_items si
            JOIN sales s     ON si.sale_id  = s.id
            JOIN products p  ON si.product_id = p.id
            WHERE si.tenant_id = '{self.tenant_id}'
              AND s.sale_time >= '{date_from}'::date
              AND s.sale_time <  '{date_to}'::date + INTERVAL '1 day'
              AND s.status != 'refunded'
              {wh_filter}
            GROUP BY si.product_id, p.name, p.barcode, p.unit
            ORDER BY total_revenue DESC
            LIMIT {limit}
        """))
        return [dict(r._mapping) for r in rows.fetchall()]

    # ─── ABC tahlil ───────────────────────────────────
    async def abc_analysis(self, date_from: date, date_to: date) -> dict:
        """
        ABC tahlil:
        A — daromadning 80% ini tashkil etadigan mahsulotlar
        B — keyingi 15%
        C — oxirgi 5%
        """
        all_products = await self.top_products(date_from, date_to, limit=1000)

        total_rev  = sum(Decimal(str(p["total_revenue"])) for p in all_products)
        if total_rev == 0:
            return {"A": [], "B": [], "C": []}

        cumulative   = Decimal("0")
        result: dict = {"A": [], "B": [], "C": []}

        for p in all_products:
            rev   = Decimal(str(p["total_revenue"]))
            cumulative += rev
            pct = (cumulative / total_rev * 100)

            if pct <= 80:
                group = "A"
            elif pct <= 95:
                group = "B"
            else:
                group = "C"

            result[group].append({
                **p,
                "revenue_pct":    str(round(rev / total_rev * 100, 2)),
                "cumulative_pct": str(round(pct, 2)),
            })

        return {
            "A": {"count": len(result["A"]), "items": result["A"]},
            "B": {"count": len(result["B"]), "items": result["B"]},
            "C": {"count": len(result["C"]), "items": result["C"]},
            "total_revenue": str(total_rev),
        }

    # ─── Marjinallik hisoboti ─────────────────────────
    async def margin_report(self, date_from: date, date_to: date) -> dict:
        rows = await self.session.execute(text(f"""
            SELECT
                p.id                                                   AS product_id,
                p.name                                                 AS product_name,
                p.category_id,
                SUM(si.total_price)                                    AS revenue,
                SUM(si.quantity * p.cost_price)                       AS cost,
                SUM(si.total_price) - SUM(si.quantity * p.cost_price) AS profit,
                CASE
                    WHEN SUM(si.total_price) > 0
                    THEN ROUND(
                        (SUM(si.total_price) - SUM(si.quantity * p.cost_price))
                        / SUM(si.total_price) * 100, 2)
                    ELSE 0
                END AS margin_pct
            FROM sale_items si
            JOIN sales    s  ON si.sale_id   = s.id
            JOIN products p  ON si.product_id = p.id
            WHERE si.tenant_id = '{self.tenant_id}'
              AND s.sale_time >= '{date_from}'::date
              AND s.sale_time <  '{date_to}'::date + INTERVAL '1 day'
              AND s.status != 'refunded'
            GROUP BY p.id, p.name, p.category_id
            ORDER BY margin_pct DESC
        """))
        items = [dict(r._mapping) for r in rows.fetchall()]

        # Umumiy marjinallik
        total_rev    = sum(Decimal(str(i["revenue"])) for i in items)
        total_cost   = sum(Decimal(str(i["cost"]))    for i in items)
        total_profit = total_rev - total_cost
        avg_margin   = (total_profit / total_rev * 100) if total_rev > 0 else Decimal("0")

        return {
            "summary": {
                "total_revenue": str(total_rev),
                "total_cost":    str(total_cost),
                "total_profit":  str(total_profit),
                "avg_margin_pct":str(round(avg_margin, 2)),
            },
            "items": items,
        }

    # ─── Kassir samaradorligi ─────────────────────────
    async def cashier_performance(self, date_from: date, date_to: date) -> list[dict]:
        rows = await self.session.execute(text(f"""
            SELECT
                s.cashier_id,
                u.full_name                      AS cashier_name,
                COUNT(s.id)                      AS total_sales,
                COALESCE(SUM(s.total_amount), 0) AS total_revenue,
                COALESCE(AVG(s.total_amount), 0) AS avg_check,
                COUNT(DISTINCT DATE(s.sale_time AT TIME ZONE 'Asia/Tashkent'))
                                                 AS working_days
            FROM sales s
            JOIN users u ON s.cashier_id = u.id
            WHERE s.tenant_id = '{self.tenant_id}'
              AND s.sale_time >= '{date_from}'::date
              AND s.sale_time <  '{date_to}'::date + INTERVAL '1 day'
              AND s.status != 'refunded'
            GROUP BY s.cashier_id, u.full_name
            ORDER BY total_revenue DESC
        """))
        return [dict(r._mapping) for r in rows.fetchall()]

    # ─── Ombor qiymati hisoboti ───────────────────────
    async def stock_value_report(self, warehouse_id: Optional[uuid.UUID] = None) -> dict:
        wh_filter = f"AND st.warehouse_id = '{warehouse_id}'" if warehouse_id else ""

        rows = await self.session.execute(text(f"""
            SELECT
                p.id                                         AS product_id,
                p.name,
                p.barcode,
                p.unit,
                st.quantity,
                p.cost_price,
                p.price                                      AS selling_price,
                st.quantity * p.cost_price                  AS stock_cost_value,
                st.quantity * p.price                       AS stock_retail_value,
                (p.price - p.cost_price) * st.quantity      AS potential_profit,
                w.name                                       AS warehouse_name
            FROM stock st
            JOIN products  p  ON st.product_id   = p.id
            JOIN warehouses w ON st.warehouse_id  = w.id
            WHERE st.tenant_id = '{self.tenant_id}'
              AND p.is_active   = TRUE
              AND st.quantity   > 0
              {wh_filter}
            ORDER BY stock_cost_value DESC
        """))
        items = [dict(r._mapping) for r in rows.fetchall()]

        total_cost   = sum(Decimal(str(i["stock_cost_value"]))   for i in items)
        total_retail = sum(Decimal(str(i["stock_retail_value"])) for i in items)

        return {
            "summary": {
                "total_items":        len(items),
                "total_cost_value":   str(total_cost),
                "total_retail_value": str(total_retail),
                "potential_profit":   str(total_retail - total_cost),
            },
            "items": items,
        }

    # ─── Audit jurnali ───────────────────────────────
    async def get_audit_log(
        self,
        entity_type: Optional[str]      = None,
        entity_id:   Optional[uuid.UUID]= None,
        user_id:     Optional[uuid.UUID]= None,
        date_from:   Optional[date]     = None,
        date_to:     Optional[date]     = None,
        skip:        int                = 0,
        limit:       int                = 50,
    ) -> list[dict]:
        filters = [f"tenant_id = '{self.tenant_id}'"]
        if entity_type:
            filters.append(f"entity_type = '{entity_type}'")
        if entity_id:
            filters.append(f"entity_id = '{entity_id}'")
        if user_id:
            filters.append(f"user_id = '{user_id}'")
        if date_from:
            filters.append(f"created_at >= '{date_from}'::date")
        if date_to:
            filters.append(f"created_at < '{date_to}'::date + INTERVAL '1 day'")

        where = " AND ".join(filters)
        rows  = await self.session.execute(text(f"""
            SELECT
                al.id, al.user_id, u.full_name AS user_name,
                al.entity_type, al.entity_id,
                al.action, al.before_state, al.after_state,
                al.ip_address, al.created_at
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE {where}
            ORDER BY al.created_at DESC
            OFFSET {skip} LIMIT {limit}
        """))
        return [dict(r._mapping) for r in rows.fetchall()]
