"""
PossKassa — ESF (Elektron Schet-Faktura) xizmati
didox.uz / Faktura.uz orqali ESF yaratish va yuborish
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from fastapi import HTTPException

from ....shared.python.utils.config import settings


class EsfService:
    """
    Elektron Schet-Faktura xizmati.
    B2B sotuvlar va tashkilotlarga savdo uchun ESF yaratiladi.
    """

    DIDOX_API = settings.DIDOX_API_URL

    def __init__(self, tenant_id: uuid.UUID, didox_token: str):
        self.tenant_id   = tenant_id
        self.didox_token = didox_token
        self._headers    = {
            "Authorization": f"Bearer {didox_token}",
            "Content-Type":  "application/json",
        }

    async def create_esf(self, invoice_data: dict) -> dict:
        """
        Yangi ESF yaratish va didox.uz ga yuborish.

        invoice_data:
          seller_tin, buyer_tin, buyer_name,
          items: [{name, catalog_code, qty, unit_id, price, vat_rate}],
          total, vat_total, invoice_date
        """
        payload = self._build_esf_payload(invoice_data)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.DIDOX_API}/invoices",
                json    = payload,
                headers = self._headers,
            )
            if resp.status_code == 422:
                raise HTTPException(status_code=422, detail=f"ESF xatosi: {resp.json()}")
            resp.raise_for_status()

        return resp.json()

    async def get_esf_status(self, invoice_id: str) -> dict:
        """ESF holati va tafsilotlari"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.DIDOX_API}/invoices/{invoice_id}",
                headers = self._headers,
            )
            resp.raise_for_status()
        return resp.json()

    async def cancel_esf(self, invoice_id: str, reason: str) -> dict:
        """ESF ni bekor qilish"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.DIDOX_API}/invoices/{invoice_id}/cancel",
                json    = {"reason": reason},
                headers = self._headers,
            )
            resp.raise_for_status()
        return resp.json()

    def _build_esf_payload(self, d: dict) -> dict:
        """didox.uz ESF format"""
        now = datetime.now(timezone.utc)
        return {
            "docNum":       d.get("doc_num", f"INV-{int(now.timestamp())}"),
            "docDate":      d.get("invoice_date", now.strftime("%d.%m.%Y")),
            "contractNum":  d.get("contract_num", ""),
            "contractDate": d.get("contract_date", ""),
            "seller": {
                "tin":      d["seller_tin"],
                "name":     d.get("seller_name", ""),
                "address":  d.get("seller_address", ""),
                "bankAccount": d.get("seller_bank_account", ""),
                "bankVAT":     d.get("seller_bank_vat", ""),
            },
            "buyer": {
                "tin":      d["buyer_tin"],
                "name":     d.get("buyer_name", ""),
                "address":  d.get("buyer_address", ""),
                "bankAccount": d.get("buyer_bank_account", ""),
            },
            "productList": {
                "products": [
                    {
                        "ordNo":        i + 1,
                        "name":         item["name"],
                        "catalogCode":  item.get("catalog_code", ""),
                        "catalogName":  item.get("catalog_name", item["name"]),
                        "measureId":    item.get("unit_id", "796"),
                        "count":        str(Decimal(str(item["qty"]))),
                        "summa":        str(int(Decimal(str(item["price"])) * 100)),
                        "vatRate":      item.get("vat_rate", 12),
                        "vatSumma":     str(int(
                            Decimal(str(item["price"])) * Decimal(str(item["qty"]))
                            * Decimal(str(item.get("vat_rate", 12))) / 100 * 100
                        )),
                        "deliverySum":  str(int(Decimal(str(item["price"])) * Decimal(str(item["qty"])) * 100)),
                    }
                    for i, item in enumerate(d.get("items", []))
                ],
                "totalSumma": str(int(Decimal(str(d.get("total", 0))) * 100)),
            },
        }
