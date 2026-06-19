"""
PossKassa — OFD / soliq.uz Fiskallashtirish xizmati
O'zbekiston Davlat Soliq Qo'mitasi OFD integratsiyasi
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ....shared.python.utils.config import settings
from ....shared.python.utils.audit import write_audit_log
from ....shared.python.events.publisher import publish_event, Events


class OfdService:
    """
    OFD (Online Fiskal Device) integratsiyasi.
    soliq.uz API orqali fiskal cheklar ro'yxatdan o'tkaziladi.
    """

    OFD_API = settings.OFD_API_URL

    def __init__(
        self,
        session:   AsyncSession,
        tenant_id: uuid.UUID,
        ofd_token: str,
    ):
        self.session   = session
        self.tenant_id = tenant_id
        self.ofd_token = ofd_token

    # ─────────────────────────────────────────────────
    # Sotuvni fiskallash
    # ─────────────────────────────────────────────────
    async def fiscalize_sale(self, sale_data: dict) -> dict:
        """
        Sotuvni OFD ga yuboradi va fiskal chek raqamini oladi.

        sale_data:
          sale_id, receipt_number, cashier_tin, warehouse_address,
          items: [{name, qty, unit, price, vat_rate, total}],
          payments: [{type, amount}],
          total, vat_total, sale_time
        """
        payload = self._build_ofd_payload(sale_data)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.OFD_API}/receipt",
                    json    = payload,
                    headers = {
                        "Authorization": f"Bearer {self.ofd_token}",
                        "Content-Type":  "application/json",
                    },
                )
                resp.raise_for_status()
                result = resp.json()
        except httpx.TimeoutException:
            # Internet yo'q yoki OFD server ishlamaydi — oflayn rejim
            return self._offline_fiscal_stub(sale_data)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code >= 500:
                # Server xatosi — oflayn stub
                return self._offline_fiscal_stub(sale_data)
            raise HTTPException(
                status_code = 422,
                detail      = f"OFD xatosi: {exc.response.text[:200]}",
            )

        # Fiskal chekni DB ga saqlash
        fiscal_data = {
            "sale_id":       sale_data["sale_id"],
            "fiscal_number": result.get("fiscalNumber", result.get("receiptId", "")),
            "fiscal_sign":   result.get("fiscalSign",   result.get("signature",  "")),
            "ofd_receipt_id":result.get("id",           result.get("receiptId",  "")),
            "receipt_url":   result.get("receiptUrl",   ""),
            "qr_url":        result.get("qrUrl",        result.get("qrCode",     "")),
            "status":        "confirmed",
            "ofd_response":  result,
        }
        await self._save_fiscal_receipt(fiscal_data)
        await publish_event(Events.FISCAL_CONFIRMED, {
            "sale_id":       sale_data["sale_id"],
            "fiscal_number": fiscal_data["fiscal_number"],
            "tenant_id":     str(self.tenant_id),
        })
        return fiscal_data

    async def get_fiscal_receipt(self, sale_id: str) -> Optional[dict]:
        """Sotuvga tegishli fiskal chekni olish"""
        result = await self.session.execute(
            text("""
                SELECT fiscal_number, fiscal_sign, receipt_url, qr_url, status, confirmed_at
                FROM fiscal_receipts
                WHERE sale_id = :sale_id AND tenant_id = :tenant_id
                ORDER BY created_at DESC LIMIT 1
            """),
            {"sale_id": sale_id, "tenant_id": str(self.tenant_id)},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    # ─────────────────────────────────────────────────
    # OFD payload yasash
    # ─────────────────────────────────────────────────
    def _build_ofd_payload(self, s: dict) -> dict:
        """soliq.uz OFD API formatiga mos payload yasash"""
        # To'lov turlarini OFD kodlariga aylantirish
        payment_map = {
            "cash":   1,  # Naqd
            "uzcard": 2,  # Plastik (Uzcard)
            "humo":   2,  # Plastik (Humo)
            "payme":  4,  # QR/Online
            "click":  4,
            "uzum":   4,
            "credit": 3,  # Kredit
        }

        return {
            "receiptType":    0,  # 0 = sotuv, 1 = qaytarish
            "cashboxId":      s.get("cashbox_id", ""),
            "time":           s.get("sale_time", datetime.now(timezone.utc).isoformat()),
            "taxPayerTin":    s.get("cashier_tin", ""),
            "location":       s.get("warehouse_address", ""),
            "receiptItems":   [
                {
                    "name":     item["name"],
                    "barcode":  item.get("barcode", ""),
                    "labels":   [],
                    "vatPercent": int(item.get("vat_rate", 12)),
                    "price":    int(Decimal(str(item["price"])) * 100),  # tiyin
                    "amount":   int(Decimal(str(item["qty"])) * Decimal(str(item["price"])) * 100),
                    "discount": int(Decimal(str(item.get("discount", 0))) * 100),
                    "other":    int(0),
                    "packageCode": item.get("package_code", ""),
                    "commissionInfo": {"tIN": "", "pinfl": ""},
                }
                for item in s.get("items", [])
            ],
            "receivedCash":   int(sum(
                Decimal(str(p["amount"])) for p in s.get("payments", [])
                if p.get("type", p.get("method", "")) == "cash"
            ) * 100),
            "receivedCard":   int(sum(
                Decimal(str(p["amount"])) for p in s.get("payments", [])
                if p.get("type", p.get("method", "")) in ("uzcard", "humo")
            ) * 100),
            "receivedOther":  int(sum(
                Decimal(str(p["amount"])) for p in s.get("payments", [])
                if p.get("type", p.get("method", "")) in ("payme", "click", "uzum")
            ) * 100),
            "extraInfo":      {"discountCard": s.get("customer_phone", "")},
        }

    def _offline_fiscal_stub(self, sale_data: dict) -> dict:
        """
        OFD mavjud bo'lmaganda oflayn fiskal stub yaratish.
        Internet qayta ulanganida qayta sinxronlanadi.
        """
        stub_sign = hmac.new(
            key     = self.ofd_token.encode()[:32].ljust(32, b"0"),
            msg     = sale_data["sale_id"].encode(),
            digestmod = hashlib.sha256,
        ).hexdigest()[:16].upper()

        return {
            "sale_id":       sale_data["sale_id"],
            "fiscal_number": f"OFFLINE-{stub_sign}",
            "fiscal_sign":   stub_sign,
            "ofd_receipt_id":None,
            "receipt_url":   None,
            "qr_url":        None,
            "status":        "pending",  # Keyinroq qayta yuboriladi
            "offline":       True,
        }

    async def _save_fiscal_receipt(self, data: dict) -> None:
        await self.session.execute(
            text("""
                INSERT INTO fiscal_receipts
                    (id, tenant_id, sale_id, fiscal_number, fiscal_sign,
                     ofd_receipt_id, receipt_url, qr_url, status, ofd_response,
                     sent_at, confirmed_at)
                VALUES
                    (:id, :tenant_id, :sale_id, :fiscal_number, :fiscal_sign,
                     :ofd_receipt_id, :receipt_url, :qr_url, :status, :ofd_response::jsonb,
                     now(), now())
                ON CONFLICT (sale_id) DO UPDATE SET
                    fiscal_number   = EXCLUDED.fiscal_number,
                    fiscal_sign     = EXCLUDED.fiscal_sign,
                    status          = EXCLUDED.status,
                    confirmed_at    = now()
            """),
            {
                "id":            str(uuid.uuid4()),
                "tenant_id":     str(self.tenant_id),
                "sale_id":       str(data["sale_id"]),
                "fiscal_number": data.get("fiscal_number", ""),
                "fiscal_sign":   data.get("fiscal_sign",   ""),
                "ofd_receipt_id":data.get("ofd_receipt_id", ""),
                "receipt_url":   data.get("receipt_url",   ""),
                "qr_url":        data.get("qr_url",        ""),
                "status":        data.get("status",        "pending"),
                "ofd_response":  json.dumps(data.get("ofd_response", {})),
            },
        )
