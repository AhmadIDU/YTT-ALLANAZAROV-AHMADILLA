"""
PossKassa — Tovar Qabuli (Kirim) biznes mantiqi

Pipeline:
  Foto/CSV/ESF → Normalizatsiya → Mahsulot moslashtirish
  → INSON TEKSHIRUVI → Tasdiqlash → Stock yangilash
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import HTTPException, UploadFile
from sqlalchemy import and_, or_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.intake import IntakeDraft, IntakeSource, IntakeStatus, StockReceipt, StockReceiptItem, Supplier
from ..parsers.llm_parser  import extract_rows_from_image, extract_rows_from_text
from ..parsers.csv_parser  import parse_csv_bytes, detect_column_mapping
from ..parsers.esf_parser  import extract_rows_from_esf
from ....shared.python.utils.audit  import write_audit_log
from ....shared.python.utils.config import settings
from ....shared.python.events.publisher import publish_event, Events

import boto3
from botocore.config import Config as BotoConfig


class IntakeService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.session   = session
        self.tenant_id = tenant_id
        self.user_id   = user_id

    # ──────────────────────────────────────────────────────
    # 1. FOTO YUKLASH va LLM EXTRACTION
    # ──────────────────────────────────────────────────────
    async def start_photo_intake(
        self,
        file:         UploadFile,
        supplier_id:  Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> IntakeDraft:
        """
        Fotoni S3 ga yuklaydi va LLM orqali qatorlarni ajratadi.
        Darhol draft qaytaradi — extraction fon jarayonida tugaydi.
        """
        # 1. S3 ga yuklash
        content   = await file.read()
        file_url  = await self._upload_to_s3(content, file.filename or "intake.jpg", "image/")

        # 2. Draft yaratish
        draft = IntakeDraft(
            tenant_id    = self.tenant_id,
            created_by   = self.user_id,
            source       = IntakeSource.PHOTO,
            original_file_url = file_url,
            status       = IntakeStatus.EXTRACTING,
            supplier_id  = supplier_id,
            warehouse_id = warehouse_id,
        )
        self.session.add(draft)
        await self.session.flush()

        # 3. LLM orqali qatorlarni ajratish (sinxron — ishlab chiqarishda Celery bilan qilish)
        try:
            rows = await extract_rows_from_image(file_url)
            normalized = await self._match_products(rows)
            draft.raw_extracted  = rows
            draft.normalized_rows = normalized
            draft.status         = IntakeStatus.REVIEW_PENDING
        except Exception as exc:
            draft.status        = IntakeStatus.EXTRACTING  # qayta urinish uchun
            draft.error_message = str(exc)

        return draft

    # ──────────────────────────────────────────────────────
    # 2. CSV / EXCEL YUKLASH
    # ──────────────────────────────────────────────────────
    async def start_csv_intake(
        self,
        file:         UploadFile,
        supplier_id:  Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> IntakeDraft:
        content = await file.read()

        # Yetkazuvchi shablonini olish
        column_mapping = None
        if supplier_id:
            supplier = await self._get_supplier(supplier_id)
            column_mapping = supplier.column_mapping if supplier else None

        try:
            rows = parse_csv_bytes(content, file.filename or "intake.csv", column_mapping)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"CSV tahlil xatosi: {exc}")

        # S3 ga yuklash (asl faylni saqlash)
        file_url = await self._upload_to_s3(
            content, file.filename or "intake.csv", "text/"
        )

        normalized = await self._match_products(rows)

        draft = IntakeDraft(
            tenant_id         = self.tenant_id,
            created_by        = self.user_id,
            source            = IntakeSource.CSV,
            original_file_url = file_url,
            raw_extracted     = rows,
            normalized_rows   = normalized,
            status            = IntakeStatus.REVIEW_PENDING,
            supplier_id       = supplier_id,
            warehouse_id      = warehouse_id,
        )
        self.session.add(draft)
        await self.session.flush()
        return draft

    # ──────────────────────────────────────────────────────
    # 3. ESF PULL
    # ──────────────────────────────────────────────────────
    async def start_esf_intake(
        self,
        invoice_number: str,
        warehouse_id:   Optional[uuid.UUID] = None,
    ) -> IntakeDraft:
        """
        didox.uz dan ESF ni yuklab oladi.
        Bu eng toza yo'l — OCR yo'q, xato minimal.
        """
        # Tenant token ni olish
        tenant = await self._get_tenant_config()
        if not tenant.get("didox_token"):
            raise HTTPException(
                status_code=422,
                detail="didox.uz tokeni sozlanmagan. Admin panel > Integratsiyalar bo'limiga kiring."
            )

        try:
            rows, raw_invoice = await extract_rows_from_esf(
                invoice_number, tenant["didox_token"]
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"ESF yuklash xatosi: {exc}")

        normalized = await self._match_products(rows)

        # Yetkazuvchini INN bo'yicha aniqlash/yaratish
        supplier_id = await self._find_or_create_supplier_from_esf(raw_invoice)

        draft = IntakeDraft(
            tenant_id         = self.tenant_id,
            created_by        = self.user_id,
            source            = IntakeSource.ESF,
            raw_extracted     = raw_invoice,
            normalized_rows   = normalized,
            status            = IntakeStatus.REVIEW_PENDING,
            supplier_id       = supplier_id,
            warehouse_id      = warehouse_id,
        )
        self.session.add(draft)
        await self.session.flush()
        return draft

    # ──────────────────────────────────────────────────────
    # 4. MAHSULOT MOSLASHTIRISH ENGINE
    # ──────────────────────────────────────────────────────
    async def _match_products(self, rows: list[dict]) -> list[dict]:
        """
        Har bir qator uchun mavjud mahsulotga moslashtirish:
        - Barcode topildi → mavjud mahsulot, stock yangilash
        - Yangi barcode   → yangi mahsulot loyihasi yaratish
        - Barcode yo'q    → nom bo'yicha fuzzy qidirish, variantlar taklif etish
        """
        normalized = []
        for row in rows:
            result = dict(row)
            result["_match"] = {"action": "create_new", "candidates": []}

            barcode = row.get("barcode")
            if barcode:
                # Barcode bo'yicha qidirish (inventory xizmatiga so'rov)
                match = await self._find_product_by_barcode(barcode)
                if match:
                    result["_match"] = {
                        "action":     "update_stock",
                        "product_id": str(match["id"]),
                        "product_name": match["name"],
                        "confidence": 1.0,
                    }
                else:
                    result["_match"] = {
                        "action":     "create_new",
                        "candidates": [],
                        "barcode_new": True,
                    }
            else:
                # Fuzzy nom qidirish
                candidates = await self._fuzzy_search_products(row.get("name", ""))
                if candidates:
                    result["_match"] = {
                        "action":     "select_or_create",
                        "candidates": candidates[:5],
                    }

            normalized.append(result)
        return normalized

    async def _find_product_by_barcode(self, barcode: str) -> Optional[dict]:
        """Inventory xizmatiga barcode so'rovi"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"http://inventory-service:8002/api/v1/products/barcode/{barcode}",
                    headers={"X-Tenant-ID": str(self.tenant_id)},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    async def _fuzzy_search_products(self, name: str) -> list[dict]:
        """Inventory xizmatiga fuzzy qidirish so'rovi"""
        if not name or len(name) < 2:
            return []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "http://inventory-service:8002/api/v1/products",
                    params={"q": name[:50], "limit": 5},
                    headers={"X-Tenant-ID": str(self.tenant_id)},
                )
                if resp.status_code == 200:
                    return [
                        {"id": p["id"], "name": p["name"], "barcode": p.get("barcode")}
                        for p in resp.json()
                    ]
        except Exception:
            pass
        return []

    # ──────────────────────────────────────────────────────
    # 5. INSON TEKSHIRUVI — TASDIQLASH
    # ──────────────────────────────────────────────────────
    async def approve_draft(
        self,
        draft_id:      uuid.UUID,
        reviewed_rows: list[dict],   # Inson tomonidan tasdiqlangan qatorlar
        warehouse_id:  uuid.UUID,
        supplier_id:   Optional[uuid.UUID] = None,
        invoice_number:Optional[str] = None,
    ) -> StockReceipt:
        """
        ⚠️ MUHIM: Faqat inson tasdiqlagan so'ng ma'lumotlar bazasiga yoziladi!
        Bu yerda:
        1. Yangi mahsulotlar yaratiladi
        2. Mavjud mahsulotlar zaxirasi yangilanadi
        3. StockReceipt hujjati yaratiladi
        4. Tannarx yangilanadi
        """
        draft = await self._get_draft_or_404(draft_id)

        if draft.status not in (IntakeStatus.REVIEW_PENDING, IntakeStatus.EXTRACTING):
            raise HTTPException(status_code=409, detail="Bu loyiha allaqachon ko'rib chiqilgan")

        # Mahsulotlarni yaratish / stock yangilash
        receipt_items = []
        total_cost    = Decimal("0")

        for row in reviewed_rows:
            if not row.get("approved", True):
                continue  # Rad etilgan qatorni o'tkazib yuborish

            product_id = await self._upsert_product(row)

            qty       = Decimal(str(row.get("qty",       1)))
            unit_cost = Decimal(str(row.get("unit_cost", 0)))
            line_cost = qty * unit_cost
            total_cost += line_cost

            receipt_items.append({
                "product_id":  str(product_id),
                "quantity":    str(qty),
                "unit_cost":   str(unit_cost),
                "total_cost":  str(line_cost),
                "vat_rate":    str(row.get("vat_rate", 12)),
                "batch_number":row.get("batch_number"),
                "expiry_date": row.get("expiry_date"),
                "warehouse_id":str(warehouse_id),
            })

        # StockReceipt yaratish
        receipt_number = self._gen_receipt_number()
        receipt = StockReceipt(
            tenant_id      = self.tenant_id,
            supplier_id    = supplier_id or draft.supplier_id,
            warehouse_id   = warehouse_id,
            created_by     = self.user_id,
            receipt_number = receipt_number,
            invoice_number = invoice_number,
            total_cost     = total_cost,
            total_amount   = total_cost,
            source         = draft.source,
            draft_id       = draft.id,
        )
        self.session.add(receipt)
        await self.session.flush()

        for item_data in receipt_items:
            item = StockReceiptItem(
                tenant_id    = self.tenant_id,
                receipt_id   = receipt.id,
                product_id   = uuid.UUID(item_data["product_id"]) if item_data.get("product_id") else None,
                quantity     = Decimal(item_data["quantity"]),
                unit_cost    = Decimal(item_data["unit_cost"]),
                total_cost   = Decimal(item_data["total_cost"]),
                vat_rate     = Decimal(item_data["vat_rate"]),
                batch_number = item_data.get("batch_number"),
                expiry_date  = item_data.get("expiry_date"),
            )
            self.session.add(item)

        # Zaxirani yangilash (Inventory xizmati orqali)
        await publish_event(Events.INTAKE_APPROVED, {
            "receipt_id":  str(receipt.id),
            "tenant_id":   str(self.tenant_id),
            "warehouse_id":str(warehouse_id),
            "items":       receipt_items,
        })

        # Draft ni tasdiqlangan deb belgilash
        draft.status      = IntakeStatus.APPROVED
        draft.reviewed_at = datetime.now(timezone.utc)
        draft.review_result = {"approved_rows": len(receipt_items), "total_cost": str(total_cost)}

        await write_audit_log(
            self.session, self.tenant_id, self.user_id,
            "stock_receipt", receipt.id, "created",
            after={"source": draft.source, "total_cost": str(total_cost), "items": len(receipt_items)},
        )
        return receipt

    async def reject_draft(self, draft_id: uuid.UUID, reason: str) -> None:
        draft = await self._get_draft_or_404(draft_id)
        draft.status        = IntakeStatus.REJECTED
        draft.reviewed_at   = datetime.now(timezone.utc)
        draft.review_result = {"reason": reason}

    async def update_draft_rows(self, draft_id: uuid.UUID, rows: list[dict]) -> IntakeDraft:
        """Tekshiruv vaqtida qatorlarni tahrirlash"""
        draft = await self._get_draft_or_404(draft_id)
        draft.normalized_rows = rows
        return draft

    # ──────────────────────────────────────────────────────
    # Yetkazuvchilar
    # ──────────────────────────────────────────────────────
    async def list_suppliers(self) -> list[Supplier]:
        from sqlalchemy import select
        result = await self.session.execute(
            select(Supplier).where(
                and_(Supplier.tenant_id == self.tenant_id, Supplier.is_active.is_(True))
            )
        )
        return list(result.scalars().all())

    async def create_supplier(self, data: dict) -> Supplier:
        supplier = Supplier(tenant_id=self.tenant_id, **data)
        self.session.add(supplier)
        await self.session.flush()
        return supplier

    async def save_column_mapping(self, supplier_id: uuid.UUID, mapping: dict) -> None:
        supplier = await self._get_supplier(supplier_id)
        if supplier:
            supplier.column_mapping = mapping

    # ──────────────────────────────────────────────────────
    # Kirimlar ro'yxati
    # ──────────────────────────────────────────────────────
    async def list_drafts(self, status: Optional[str] = None) -> list[IntakeDraft]:
        from sqlalchemy import select, desc
        q = select(IntakeDraft).where(IntakeDraft.tenant_id == self.tenant_id).order_by(desc(IntakeDraft.created_at))
        if status:
            q = q.where(IntakeDraft.status == status)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_draft(self, draft_id: uuid.UUID) -> IntakeDraft:
        return await self._get_draft_or_404(draft_id)

    # ──────────────────────────────────────────────────────
    # Yordamchilar
    # ──────────────────────────────────────────────────────
    async def _upsert_product(self, row: dict) -> uuid.UUID:
        """Mahsulotni yaratish yoki mavjudini topish"""
        match    = row.get("_match", {})
        action   = match.get("action", "create_new")
        prod_id  = match.get("product_id")

        if action == "update_stock" and prod_id:
            # Tannarxni yangilash (inventory xizmatiga)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.put(
                        f"http://inventory-service:8002/api/v1/products/{prod_id}",
                        json={"cost_price": row.get("unit_cost", 0)},
                        headers={"X-Tenant-ID": str(self.tenant_id)},
                    )
            except Exception:
                pass
            return uuid.UUID(prod_id)

        # Yangi mahsulot yaratish (inventory xizmatiga)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "http://inventory-service:8002/api/v1/products",
                    json={
                        "name":       row.get("name", "Noma'lum"),
                        "barcode":    row.get("barcode"),
                        "unit":       row.get("unit", "pcs"),
                        "price":      row.get("unit_cost", 0),
                        "cost_price": row.get("unit_cost", 0),
                        "vat_rate":   row.get("vat_rate", 12),
                    },
                    headers={"X-Tenant-ID": str(self.tenant_id)},
                )
                if resp.status_code == 201:
                    return uuid.UUID(resp.json()["id"])
        except Exception:
            pass
        return uuid.uuid4()  # fallback

    async def _get_draft_or_404(self, draft_id: uuid.UUID) -> IntakeDraft:
        from sqlalchemy import select
        result = await self.session.execute(
            select(IntakeDraft).where(
                and_(IntakeDraft.id == draft_id, IntakeDraft.tenant_id == self.tenant_id)
            )
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise HTTPException(status_code=404, detail="Kirim loyihasi topilmadi")
        return draft

    async def _get_supplier(self, supplier_id: uuid.UUID) -> Optional[Supplier]:
        from sqlalchemy import select
        result = await self.session.execute(
            select(Supplier).where(
                and_(Supplier.id == supplier_id, Supplier.tenant_id == self.tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def _get_tenant_config(self) -> dict:
        """Tenant konfiguratsiyasini olish"""
        from sqlalchemy import text
        result = await self.session.execute(
            text("SELECT ofd_token, didox_token, eimzo_cert FROM tenants WHERE id = :tid"),
            {"tid": str(self.tenant_id)},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else {}

    async def _find_or_create_supplier_from_esf(self, invoice: dict) -> Optional[uuid.UUID]:
        seller = invoice.get("seller", invoice.get("sellerInfo", {}))
        inn    = seller.get("tin", seller.get("inn", ""))
        name   = seller.get("name", "")
        if not inn:
            return None
        # INN bo'yicha qidirish
        from sqlalchemy import select
        result = await self.session.execute(
            select(Supplier).where(
                and_(Supplier.tenant_id == self.tenant_id, Supplier.inn == inn)
            )
        )
        supplier = result.scalar_one_or_none()
        if not supplier:
            supplier = Supplier(tenant_id=self.tenant_id, inn=inn, name=name)
            self.session.add(supplier)
            await self.session.flush()
        return supplier.id

    async def _upload_to_s3(self, content: bytes, filename: str, content_type_prefix: str) -> str:
        """MinIO/S3 ga fayl yuklash"""
        import aioboto3
        session = aioboto3.Session()
        key     = f"intake/{self.tenant_id}/{uuid.uuid4()}/{filename}"
        async with session.client(
            "s3",
            endpoint_url         = settings.S3_ENDPOINT,
            aws_access_key_id    = settings.S3_ACCESS_KEY,
            aws_secret_access_key= settings.S3_SECRET_KEY,
        ) as s3:
            await s3.put_object(
                Bucket      = settings.S3_BUCKET,
                Key         = key,
                Body        = content,
                ContentType = content_type_prefix + "octet-stream",
            )
        return f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{key}"

    @staticmethod
    def _gen_receipt_number() -> str:
        import random
        from datetime import date
        d = date.today().strftime("%Y%m%d")
        n = random.randint(1000, 9999)
        return f"KRM-{d}-{n}"
