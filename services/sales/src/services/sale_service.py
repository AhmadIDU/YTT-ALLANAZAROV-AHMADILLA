"""
PossKassa — Sotuv biznes mantiqi
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from ..models.sale import Sale, SaleItem, Payment, Shift, Return, SaleStatus, SyncStatus
from ..schemas.sale import (
    SaleCreate, SaleSyncBatch, SaleSyncResponse, SyncResult,
    ShiftOpen, ShiftClose, RefundCreate,
)
from ....shared.python.utils.audit import write_audit_log
from ....shared.python.events.publisher import publish_event, Events


VAT_RATE = Decimal("12.0")  # O'zbekistonda standart QQS 12%


class SaleService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.session   = session
        self.tenant_id = tenant_id
        self.user_id   = user_id

    # ──────────────────────────────────────────────────
    # Smena amallari
    # ──────────────────────────────────────────────────
    async def open_shift(self, data: ShiftOpen) -> Shift:
        """Yangi smena ochish"""
        # Ochiq smena borligini tekshirish
        existing = await self.session.execute(
            select(Shift).where(
                and_(
                    Shift.tenant_id == self.tenant_id,
                    Shift.cashier_id == self.user_id,
                    Shift.status == "open",
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Siz uchun allaqachon ochiq smena mavjud",
            )

        shift = Shift(
            tenant_id    = self.tenant_id,
            cashier_id   = self.user_id,
            warehouse_id = data.warehouse_id,
            opening_cash = data.opening_cash,
            status       = "open",
        )
        self.session.add(shift)
        await self.session.flush()

        await write_audit_log(
            self.session, self.tenant_id, self.user_id,
            "shift", shift.id, "opened",
            after={"opening_cash": str(data.opening_cash)},
        )
        await publish_event(Events.SHIFT_OPENED, {
            "shift_id":    str(shift.id),
            "tenant_id":   str(self.tenant_id),
            "cashier_id":  str(self.user_id),
        })
        return shift

    async def close_shift(self, shift_id: uuid.UUID, data: ShiftClose) -> Shift:
        """Smenani yopish va kassa hisobotini yaratish"""
        shift = await self._get_shift_or_404(shift_id)

        if shift.status == "closed":
            raise HTTPException(status_code=409, detail="Smena allaqachon yopilgan")

        # Smena davomidagi naqd sotuvlar yig'indisi
        cash_sales = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                and_(
                    Payment.tenant_id == self.tenant_id,
                    Payment.method    == "cash",
                    Sale.shift_id     == shift_id,
                )
            ).join(Sale, Payment.sale_id == Sale.id)
        )
        expected = (shift.opening_cash or 0) + (cash_sales.scalar() or 0)

        shift.closing_cash = data.closing_cash
        shift.expected_cash = expected
        shift.status        = "closed"
        shift.closed_at     = datetime.now(timezone.utc)
        shift.notes         = data.notes

        await write_audit_log(
            self.session, self.tenant_id, self.user_id,
            "shift", shift.id, "closed",
            after={
                "closing_cash": str(data.closing_cash),
                "expected_cash": str(expected),
                "difference": str(data.closing_cash - expected),
            },
        )
        await publish_event(Events.SHIFT_CLOSED, {"shift_id": str(shift_id)})
        return shift

    async def get_current_shift(self) -> Optional[Shift]:
        result = await self.session.execute(
            select(Shift).where(
                and_(
                    Shift.tenant_id == self.tenant_id,
                    Shift.cashier_id == self.user_id,
                    Shift.status == "open",
                )
            )
        )
        return result.scalar_one_or_none()

    # ──────────────────────────────────────────────────
    # Sotuv amallari
    # ──────────────────────────────────────────────────
    async def create_sale(self, data: SaleCreate) -> Sale:
        """Yangi sotuv yaratish"""
        # Idempotency tekshiruvi
        existing = await self.session.execute(
            select(Sale).where(
                and_(Sale.tenant_id == self.tenant_id, Sale.local_id == data.local_id)
            )
        )
        if (existing_sale := existing.scalar_one_or_none()):
            return existing_sale  # Ikki marta yuborilgan — mavjud sotuvni qaytarish

        # Hisob-kitob
        subtotal       = sum(i.unit_price * i.quantity for i in data.items)
        discount_total = sum(i.discount_amount for i in data.items)
        vat_total      = sum(
            (i.unit_price * i.quantity - i.discount_amount) * VAT_RATE / (100 + VAT_RATE)
            for i in data.items
        )
        total = subtotal - discount_total

        # To'lov yig'indisi tekshiruvi
        paid = sum(p.amount for p in data.payments)
        if paid < total:
            raise HTTPException(
                status_code=422,
                detail=f"To'lov yetarli emas: kerak {total}, to'langan {paid}",
            )

        sale = Sale(
            tenant_id      = self.tenant_id,
            shift_id       = data.shift_id,
            cashier_id     = self.user_id,
            customer_id    = data.customer_id,
            warehouse_id   = data.warehouse_id,
            receipt_number = self._gen_receipt_number(),
            subtotal       = subtotal,
            discount_amount= discount_total,
            vat_amount     = vat_total,
            total_amount   = total,
            local_id       = data.local_id,
            status         = SaleStatus.COMPLETED,
            sync_status    = SyncStatus.SYNCED,
            sale_time      = data.sale_time or datetime.now(timezone.utc),
            synced_at      = datetime.now(timezone.utc),
        )
        self.session.add(sale)
        await self.session.flush()

        # Sotuv qatorlari
        for item_data in data.items:
            item = SaleItem(
                tenant_id      = self.tenant_id,
                sale_id        = sale.id,
                product_id     = item_data.product_id,
                quantity       = item_data.quantity,
                unit_price     = item_data.unit_price,
                discount_amount= item_data.discount_amount,
                vat_amount     = (item_data.unit_price * item_data.quantity - item_data.discount_amount) * VAT_RATE / (100 + VAT_RATE),
                total_price    = item_data.unit_price * item_data.quantity - item_data.discount_amount,
            )
            self.session.add(item)

        # To'lovlar
        for pay_data in data.payments:
            payment = Payment(
                tenant_id      = self.tenant_id,
                sale_id        = sale.id,
                method         = pay_data.method,
                amount         = pay_data.amount,
                transaction_id = pay_data.transaction_id,
                status         = "completed",
            )
            self.session.add(payment)

        await self.session.flush()

        # Audit
        await write_audit_log(
            self.session, self.tenant_id, self.user_id,
            "sale", sale.id, "created",
            after={"total": str(total), "items_count": len(data.items)},
        )

        # Voqea nashr etish (Inventory zaxirani kamaytiradi, Compliance fiskallaydi)
        await publish_event(Events.SALE_CREATED, {
            "sale_id":    str(sale.id),
            "tenant_id":  str(self.tenant_id),
            "total":      str(total),
            "items":      [{"product_id": str(i.product_id), "qty": str(i.quantity)} for i in data.items],
        })

        return sale

    async def sync_batch(self, batch: SaleSyncBatch) -> SaleSyncResponse:
        """Oflayn sotuvlar paketini sinxronlash"""
        results: list[SyncResult] = []

        for sale_data in batch.sales:
            try:
                sale = await self.create_sale(sale_data)
                results.append(SyncResult(
                    local_id   = sale_data.local_id,
                    remote_id  = str(sale.id),
                    success    = True,
                    fiscal_url = sale.fiscal_url,
                ))
            except Exception as exc:
                results.append(SyncResult(
                    local_id = sale_data.local_id,
                    success  = False,
                    error    = str(exc),
                ))

        synced = sum(1 for r in results if r.success)
        return SaleSyncResponse(results=results, synced=synced, failed=len(results) - synced)

    async def create_refund(self, sale_id: uuid.UUID, data: RefundCreate) -> Return:
        """Qaytarish yaratish"""
        sale = await self._get_sale_or_404(sale_id)

        if sale.status == SaleStatus.REFUNDED:
            raise HTTPException(status_code=409, detail="Sotuv allaqachon qaytarilgan")

        if data.refund_amount > sale.total_amount:
            raise HTTPException(
                status_code=422,
                detail="Qaytarish summasi sotuv summasidan oshib ketdi",
            )

        ret = Return(
            tenant_id       = self.tenant_id,
            original_sale_id= sale_id,
            cashier_id      = self.user_id,
            reason          = data.reason,
            refund_amount   = data.refund_amount,
            refund_method   = data.refund_method,
        )
        self.session.add(ret)

        # Sotuv holatini yangilash
        is_full_refund = data.refund_amount >= sale.total_amount
        sale.status = SaleStatus.REFUNDED if is_full_refund else SaleStatus.PARTIAL_REFUND

        await write_audit_log(
            self.session, self.tenant_id, self.user_id,
            "sale", sale_id, "refunded",
            before={"status": sale.status, "total": str(sale.total_amount)},
            after={"refund_amount": str(data.refund_amount), "reason": data.reason},
        )
        await publish_event(Events.SALE_REFUNDED, {
            "sale_id":      str(sale_id),
            "refund_amount": str(data.refund_amount),
        })
        return ret

    # ──────────────────────────────────────────────────
    # Yordamchi usullar
    # ──────────────────────────────────────────────────
    async def get_sale(self, sale_id: uuid.UUID) -> Sale:
        return await self._get_sale_or_404(sale_id)

    async def list_sales(
        self, skip: int = 0, limit: int = 50,
        shift_id: Optional[uuid.UUID] = None,
        from_time: Optional[datetime] = None,
        to_time:   Optional[datetime] = None,
    ) -> list[Sale]:
        q = (
            select(Sale)
            .options(selectinload(Sale.items), selectinload(Sale.payments))
            .where(Sale.tenant_id == self.tenant_id)
            .order_by(Sale.sale_time.desc())
        )
        if shift_id:
            q = q.where(Sale.shift_id == shift_id)
        if from_time:
            q = q.where(Sale.sale_time >= from_time)
        if to_time:
            q = q.where(Sale.sale_time <= to_time)
        result = await self.session.execute(q.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def _get_sale_or_404(self, sale_id: uuid.UUID) -> Sale:
        result = await self.session.execute(
            select(Sale)
            .options(selectinload(Sale.items), selectinload(Sale.payments))
            .where(and_(Sale.id == sale_id, Sale.tenant_id == self.tenant_id))
        )
        sale = result.scalar_one_or_none()
        if not sale:
            raise HTTPException(status_code=404, detail="Sotuv topilmadi")
        return sale

    async def _get_shift_or_404(self, shift_id: uuid.UUID) -> Shift:
        result = await self.session.execute(
            select(Shift).where(
                and_(Shift.id == shift_id, Shift.tenant_id == self.tenant_id)
            )
        )
        shift = result.scalar_one_or_none()
        if not shift:
            raise HTTPException(status_code=404, detail="Smena topilmadi")
        return shift

    @staticmethod
    def _gen_receipt_number() -> str:
        import random
        from datetime import date
        d = date.today().strftime("%Y%m%d")
        n = random.randint(1000, 9999)
        return f"PK-{d}-{n}"
