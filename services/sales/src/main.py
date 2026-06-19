"""
PossKassa — Sotuv va To'lovlar Xizmati
FastAPI ilovasi
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.sales import router as sales_router
from ...shared.python.utils.config import settings

app = FastAPI(
    title="PossKassa — Sotuv Xizmati",
    description="Sotuvlar, smenalar, to'lovlar va qaytarishlarni boshqarish",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routerlarni ulash
app.include_router(sales_router, prefix="/api/v1/sales", tags=["Sotuvlar"])
app.include_router(sales_router, prefix="/api/v1/shifts", tags=["Smenalar"], include_in_schema=False)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "sales"}
