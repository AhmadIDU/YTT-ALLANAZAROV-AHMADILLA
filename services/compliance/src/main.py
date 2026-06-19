"""PossKassa — Muvofiqlik Xizmati (OFD, ESF, E-IMZO)"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.compliance import router
from ...shared.python.utils.config import settings

app = FastAPI(title="PossKassa — Muvofiqlik Xizmati", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1/compliance", tags=["Muvofiqlik"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "compliance"}
