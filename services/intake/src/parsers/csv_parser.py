"""
PossKassa — CSV / Excel Tahlil qiluvchi
Yetkazuvchi shablonlari bilan ustun moslashtirish
"""
from __future__ import annotations

import io
from typing import Optional

import pandas as pd


# Standart ustun nomlari (tarjima jadval)
_KNOWN_HEADERS: dict[str, str] = {
    # O'zbek
    "nomi": "name", "mahsulot": "name", "tovar": "name", "mahsulot nomi": "name",
    "miqdor": "qty", "soni": "qty", "dona": "qty", "kg": "qty",
    "narx": "unit_cost", "narxi": "unit_cost", "birlik narxi": "unit_cost",
    "summa": "total_cost", "jami": "total_cost", "jami summa": "total_cost",
    "shtrix": "barcode", "shtrixkod": "barcode", "barcode": "barcode",
    "o'lchov": "unit", "birlik": "unit",
    "qqs": "vat_rate", "nds": "vat_rate",
    "yaroqlilik": "expiry_date", "muddat": "expiry_date",
    # Rus
    "наименование": "name", "товар": "name", "название": "name",
    "количество": "qty", "кол-во": "qty",
    "цена": "unit_cost", "цена за ед": "unit_cost",
    "сумма": "total_cost", "итого": "total_cost",
    "штрихкод": "barcode", "штрих": "barcode",
    "ед.изм": "unit", "единица": "unit",
    "ндс": "vat_rate", "ндс%": "vat_rate",
    "срок": "expiry_date", "годен до": "expiry_date",
}

_REQUIRED = {"name", "qty", "unit_cost"}


def parse_csv_bytes(
    content:        bytes,
    filename:       str,
    column_mapping: Optional[dict] = None,  # Yetkazuvchi shabloni
) -> list[dict]:
    """
    CSV yoki Excel faylini tahlil qilib mahsulot qatorlarini qaytaradi.

    column_mapping — yetkazuvchi uchun saqlangan mapping:
        {"A ustun": "name", "B ustun": "qty", "C ustun": "unit_cost"}
    """
    # Fayl turini aniqlash
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(content), dtype=str)
    else:
        # CSV — turli kodlashlarni sinash
        for enc in ("utf-8", "cp1251", "cp1252", "iso-8859-1"):
            try:
                df = pd.read_csv(io.BytesIO(content), dtype=str, encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("CSV fayl kodlashini aniqlab bo'lmadi")

    # Bo'sh ustunlar va qatorlarni olib tashlash
    df.dropna(how="all", inplace=True)
    df.columns = [str(c).strip() for c in df.columns]

    # Ustun moslashtirish
    mapping = _build_mapping(list(df.columns), column_mapping)
    if not mapping:
        raise ValueError("Ustunlar moslashtirilmadi. Iltimos, shablonni sozlang.")

    rows: list[dict] = []
    for _, row in df.iterrows():
        item: dict = {}
        for orig_col, std_col in mapping.items():
            val = str(row.get(orig_col, "")).strip()
            if val and val.lower() not in ("nan", "none", "-"):
                item[std_col] = val

        if "name" not in item or not item["name"]:
            continue  # Bo'sh qatorni o'tkazib yuborish

        rows.append(_normalize_csv_row(item))

    return rows


def _build_mapping(
    columns:        list[str],
    custom_mapping: Optional[dict] = None,
) -> dict[str, str]:
    """
    Ustun nomlarini standart nomlarga moslashtiradi.
    custom_mapping ustunlik qiladi, qolganlar avtomatik aniqlash.
    """
    result: dict[str, str] = {}

    # Avval shablonni qo'llash
    if custom_mapping:
        for orig, std in custom_mapping.items():
            if orig in columns:
                result[orig] = std

    # Avtomatik aniqlash (topilmagan ustunlar uchun)
    already_mapped = set(result.values())
    for col in columns:
        if col in result:
            continue
        key = col.lower().strip()
        if key in _KNOWN_HEADERS:
            std = _KNOWN_HEADERS[key]
            if std not in already_mapped:
                result[col] = std
                already_mapped.add(std)

    return result


def _normalize_csv_row(item: dict) -> dict:
    def _num(val, default=0.0):
        try:
            return float(str(val).replace(" ", "").replace(",", "."))
        except (ValueError, TypeError):
            return default

    qty       = _num(item.get("qty", 1), 1.0)
    unit_cost = _num(item.get("unit_cost", 0))
    total     = _num(item.get("total_cost", 0)) or (qty * unit_cost)

    return {
        "name":        item.get("name", "").strip()[:255],
        "barcode":     item.get("barcode", "").strip() or None,
        "qty":         max(0.001, qty),
        "unit":        item.get("unit", "pcs").lower()[:10] or "pcs",
        "unit_cost":   unit_cost,
        "total_cost":  total,
        "vat_rate":    _num(item.get("vat_rate", 12), 12.0),
        "expiry_date": item.get("expiry_date", "").strip() or None,
    }


def detect_column_mapping(content: bytes, filename: str) -> dict[str, str]:
    """
    Fayldan ustun nomlarini o'qib, avtomatik moslashtirishni qaytaradi.
    Yangi yetkazuvchi uchun shablon yaratishda ishlatiladi.
    """
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(content), nrows=0, dtype=str)
    else:
        df = pd.read_csv(io.BytesIO(content), nrows=0, dtype=str, encoding="utf-8")

    df.columns = [str(c).strip() for c in df.columns]
    return _build_mapping(list(df.columns))
