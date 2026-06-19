"""PossKassa — Tahlil va Admin Xizmati"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.analytics import router
from ...shared.python.utils.config import settings

app = FastAPI(title="PossKassa — Tahlil Xizmati", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1", tags=["Hisobotlar", "Audit"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "analytics"}
