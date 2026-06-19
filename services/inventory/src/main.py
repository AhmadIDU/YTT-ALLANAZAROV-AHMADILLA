"""PossKassa — Tovar va Ombor Xizmati"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.products import router
from ...shared.python.utils.config import settings

app = FastAPI(title="PossKassa — Tovar Xizmati", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1/products", tags=["Mahsulotlar"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "inventory"}
