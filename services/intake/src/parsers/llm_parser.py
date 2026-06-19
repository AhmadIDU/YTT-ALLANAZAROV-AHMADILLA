"""
PossKassa — Claude Vision LLM bilan foto/rasm tahlil qilish
Yetkazuvchi ro'yxati yoki hisob-fakturadan mahsulot qatorlarini ajratib olish
"""
from __future__ import annotations

import base64
import json
import re
from typing import Optional

import anthropic
import httpx

from ....shared.python.utils.config import settings

# Bir marta yaratish — thread-safe
_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


# ────────────────────────────────────────────────────────────────
# Asosiy tahlil funksiyasi
# ────────────────────────────────────────────────────────────────
async def extract_rows_from_image(image_url: str) -> list[dict]:
    """
    Rasm URL dan mahsulot qatorlarini JSON formatida ajratib oladi.

    Qaytaradi:
        [
          {
            "name": "Non Obi 500g",
            "barcode": "4600000123456",   # mavjud bo'lsa
            "qty": 24,
            "unit": "pcs",
            "unit_cost": 3500,
            "total_cost": 84000,
            "vat_rate": 12,
            "expiry_date": "2025-06-01"   # mavjud bo'lsa
          },
          ...
        ]
    """
    # Rasmni base64 ga aylantirish
    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.get(image_url)
        resp.raise_for_status()
        image_data   = base64.standard_b64encode(resp.content).decode("utf-8")
        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]

    prompt = """Bu rasm yetkazuvchining keltirgani ro'yxati yoki hisob-fakturasi.
Rasmdan barcha mahsulot qatorlarini ajratib ol va FAQAT JSON array qaytardir.

Har bir element:
{
  "name": "mahsulot nomi (o'zbek yoki rus tilida, xuddi rasmdagi kabi)",
  "barcode": "shtrixkod (mavjud bo'lsa, aks holda null)",
  "qty": miqdor (raqam),
  "unit": "o'lchov birligi: pcs/kg/l/m/box",
  "unit_cost": bir dona narxi (so'mda, raqam),
  "total_cost": jami narx (qty × unit_cost, raqam),
  "vat_rate": QQS foizi (odatda 12, aks holda 0),
  "expiry_date": "YYYY-MM-DD (agar mavjud bo'lsa, aks holda null)"
}

MUHIM QOIDALAR:
- Faqat JSON array qaytardir, hech qanday izoh yoki markdown yo'q
- Raqamlardan faqat raqam (vergul va bo'sh joy yo'q, masalan: 3500 emas "3 500")
- O'qib bo'lmaydigan yoki noaniq qatorlarni o'tkazib yubor
- Agar jami narx ko'rsatilmagan bo'lsa, qty × unit_cost dan hisoblash

JSON array:"""

    client = _get_client()
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type":       "base64",
                            "media_type": content_type,
                            "data":       image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    raw_text = message.content[0].text.strip()
    return _parse_json_response(raw_text)


async def extract_rows_from_text(text: str) -> list[dict]:
    """
    Oddiy matn (vaqtinchalik hujjat, nusxa ko'chirish) dan qatorlarni ajratish.
    OCR matnini tuzatish uchun ham ishlatiladi.
    """
    prompt = f"""Quyidagi yetkazuvchi ro'yxati matnidan mahsulot qatorlarini ajratib, JSON array qaytardir.

FORMAT:
[{{"name":"...", "barcode":null, "qty":1, "unit":"pcs", "unit_cost":0, "total_cost":0, "vat_rate":12, "expiry_date":null}}]

MATN:
{text}

JSON array:"""

    client = _get_client()
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = message.content[0].text.strip()
    return _parse_json_response(raw_text)


# ────────────────────────────────────────────────────────────────
# JSON tahlil qilish (xavfsiz)
# ────────────────────────────────────────────────────────────────
def _parse_json_response(text: str) -> list[dict]:
    """LLM javobidan JSON ni xavfsiz tahlil qilish"""
    # Markdown code block larni tozalash
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = text.rstrip("`").strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [_validate_row(row) for row in data if isinstance(row, dict)]
        if isinstance(data, dict) and "items" in data:
            return [_validate_row(r) for r in data["items"] if isinstance(r, dict)]
    except json.JSONDecodeError:
        # Birinchi [ dan oxirgi ] gacha kesib olish
        start = text.find("[")
        end   = text.rfind("]")
        if start != -1 and end != -1:
            try:
                data = json.loads(text[start:end + 1])
                if isinstance(data, list):
                    return [_validate_row(r) for r in data if isinstance(r, dict)]
            except json.JSONDecodeError:
                pass

    return []


def _validate_row(row: dict) -> dict:
    """Bir qatorni tekshirish va standartlashtirish"""
    def _num(val, default=0):
        try:
            return float(str(val).replace(" ", "").replace(",", "."))
        except (ValueError, TypeError):
            return default

    qty       = _num(row.get("qty", 1), 1)
    unit_cost = _num(row.get("unit_cost", 0))
    total     = _num(row.get("total_cost", 0)) or (qty * unit_cost)

    return {
        "name":        str(row.get("name", "")).strip()[:255],
        "barcode":     str(row.get("barcode", "")).strip() or None,
        "qty":         max(0.001, qty),
        "unit":        str(row.get("unit", "pcs")).lower()[:10],
        "unit_cost":   unit_cost,
        "total_cost":  total,
        "vat_rate":    _num(row.get("vat_rate", 12), 12),
        "expiry_date": str(row.get("expiry_date", "")).strip() or None,
    }
