"""
PossKassa — ESF (didox.uz / Faktura.uz) integratsiyasi
Elektron hisob-fakturadan mahsulot qatorlarini olish
"""
from __future__ import annotations

import httpx

from ....shared.python.utils.config import settings


class DidoxClient:
    """didox.uz API mijozi"""

    BASE_URL = "https://api.didox.uz/v1"

    def __init__(self, token: str):
        self.token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

    async def get_invoice(self, invoice_number: str) -> dict:
        """ESF raqami bo'yicha hisob-fakturani olish"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/invoices/{invoice_number}",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_incoming_invoices(
        self,
        page: int = 1,
        size: int = 20,
        date_from: str | None = None,
    ) -> list[dict]:
        """Kiruvchi ESF lar ro'yxati"""
        params: dict = {"page": page, "size": size}
        if date_from:
            params["dateFrom"] = date_from

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/invoices/incoming",
                headers=self._headers,
                params=params,
            )
            resp.raise_for_status()
            return resp.json().get("items", [])


async def extract_rows_from_esf(
    invoice_number: str,
    didox_token:    str,
) -> tuple[list[dict], dict]:
    """
    ESF raqami bo'yicha mahsulot qatorlarini oladi.

    Qaytaradi:
        (normalized_rows, raw_invoice)
    """
    client  = DidoxClient(didox_token)
    invoice = await client.get_invoice(invoice_number)

    rows = []
    for item in invoice.get("items", invoice.get("productList", [])):
        rows.append({
            "name":        item.get("name", item.get("productName", "")),
            "barcode":     item.get("barcode", item.get("catalogCode", None)),
            "qty":         float(item.get("count",    item.get("quantity", 1))),
            "unit":        _map_unit(item.get("measureId", item.get("unit", "pcs"))),
            "unit_cost":   float(item.get("price",    item.get("unitPrice", 0))),
            "total_cost":  float(item.get("total",    item.get("totalPrice", 0))),
            "vat_rate":    float(item.get("vatRate",  12)),
            "expiry_date": item.get("expiryDate", None),
        })

    return rows, invoice


def _map_unit(unit_id) -> str:
    """didox birlik kodlarini standart birliklarga aylantirish"""
    mapping = {
        "796": "pcs",  # dona
        "166": "kg",   # kg
        "112": "l",    # litr
        "006": "m",    # metr
        "839": "box",  # quti
    }
    unit_str = str(unit_id).lower()
    return mapping.get(unit_str, unit_str if unit_str in ("pcs", "kg", "l", "m", "box") else "pcs")
