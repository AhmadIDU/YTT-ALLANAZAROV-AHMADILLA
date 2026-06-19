"""PossKassa — Tovar Qabuli (Kirim) Xizmati"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.intake import router
from ...shared.python.utils.config import settings

app = FastAPI(title="PossKassa — Kirim Xizmati", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1/intake", tags=["Tovar Qabuli"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "intake"}
