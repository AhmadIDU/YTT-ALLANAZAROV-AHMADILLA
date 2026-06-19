"""
PossKassa — E-IMZO Raqamli Imzo xizmati
O'zbekiston E-IMZO integratsiyasi (hujjatlarni imzolash)
"""
from __future__ import annotations

import base64
import hashlib
import json
import uuid
from typing import Optional

import httpx
from fastapi import HTTPException

from ....shared.python.utils.config import settings


class EimzoService:
    """
    E-IMZO raqamli imzo xizmati.
    ESF va boshqa rasmiy hujjatlarni imzolash uchun ishlatiladi.
    """

    EIMZO_API = settings.EIMZO_API_URL

    def __init__(self, cert_pem: str):
        """
        cert_pem: PEM formatdagi E-IMZO sertifikat (tenant sozlamalaridan)
        """
        self.cert_pem = cert_pem

    async def sign_document(self, document_json: dict) -> dict:
        """
        Hujjatni E-IMZO bilan imzolash.

        Qaytaradi:
          {"signature": "...", "cert_serial": "...", "signed_at": "..."}
        """
        doc_str  = json.dumps(document_json, ensure_ascii=False, sort_keys=True)
        doc_hash = hashlib.sha256(doc_str.encode()).hexdigest()

        # E-IMZO server ga yuborish
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.EIMZO_API}/sign",
                    json = {
                        "data":        base64.b64encode(doc_str.encode()).decode(),
                        "certificate": self.cert_pem,
                    },
                    headers = {"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                result = resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code = 503,
                detail      = f"E-IMZO server bilan bog'lanishda xato: {exc}",
            )

        return {
            "signature":   result.get("signature", ""),
            "cert_serial": result.get("certSerial", ""),
            "doc_hash":    doc_hash,
            "signed_at":   result.get("signedAt", ""),
        }

    async def verify_signature(self, document_json: dict, signature: str) -> bool:
        """Imzoni tekshirish"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.EIMZO_API}/verify",
                    json = {
                        "data":      base64.b64encode(
                            json.dumps(document_json, ensure_ascii=False, sort_keys=True).encode()
                        ).decode(),
                        "signature": signature,
                    },
                )
                return resp.status_code == 200 and resp.json().get("valid", False)
        except Exception:
            return False

    def get_cert_info(self) -> dict:
        """Sertifikat ma'lumotlarini olish"""
        # Haqiqiy implementatsiyada sertifikatni tahlil qilish
        return {
            "subject": "CN=Test, O=Test Org, C=UZ",
            "valid":   True,
            "message": "Sertifikat faol",
        }
