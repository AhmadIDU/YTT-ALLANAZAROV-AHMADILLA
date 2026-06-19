"""
PossKassa — API Gateway / BFF
Autentifikatsiya, tenant aniqlash, tezlik cheklash, yo'naltirish
"""
from __future__ import annotations

import httpx
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import jwt  # PyJWT

from .routers import auth_router
from ...shared.python.utils.config import settings

app = FastAPI(
    title="PossKassa API Gateway",
    description="PossKassa tizimi uchun API Gateway",
    version="1.0.0",
)

# ─── CORS ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Xizmatlar manzillari ────────────────────────
SERVICE_URLS = {
    "sales":       "http://sales-service:8001",
    "inventory":   "http://inventory-service:8002",
    "compliance":  "http://compliance-service:8003",
    "intake":      "http://intake-service:8004",
    "analytics":   "http://analytics-service:8005",
    "notifications":"http://notifications-service:8006",
}

# ─── Auth router ─────────────────────────────────
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Autentifikatsiya"])


# ─── Asosiy proxy ────────────────────────────────
@app.api_route(
    "/api/v1/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy(request: Request, service: str, path: str):
    """Barcha so'rovlarni tegishli xizmatga yo'naltiradi"""
    if service not in SERVICE_URLS:
        raise HTTPException(status_code=404, detail=f"'{service}' xizmati topilmadi")

    # JWT dan tenant_id ni olish va forward qilish
    auth_header = request.headers.get("Authorization", "")
    tenant_id   = ""
    if auth_header.startswith("Bearer "):
        try:
            token   = auth_header.split(" ", 1)[1]
            payload = jwt.decode(token, options={"verify_signature": False})
            tenant_id = payload.get("tenant_id", "")
        except Exception:
            pass

    # So'rovni yuborish
    target_url = f"{SERVICE_URLS[service]}/api/v1/{path}"
    headers    = dict(request.headers)
    headers["X-Tenant-ID"]    = tenant_id
    headers["X-Forwarded-For"] = request.client.host if request.client else ""

    body = await request.body()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method  = request.method,
            url     = target_url,
            headers = headers,
            content = body,
            params  = dict(request.query_params),
        )

    return Response(
        content     = response.content,
        status_code = response.status_code,
        headers     = dict(response.headers),
        media_type  = response.headers.get("content-type"),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}
