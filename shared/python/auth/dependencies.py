"""
PossKassa — Auth va RBAC dependency lari
Keycloak JWT tokenlarini tekshirish va rol asosida ruxsat berish
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from ..utils.config import settings


# ─────────────────────────────────────────
# Rollar va ruxsatlar
# ─────────────────────────────────────────
class Role(str, Enum):
    CASHIER  = "cashier"
    MANAGER  = "manager"
    ADMIN    = "admin"
    OWNER    = "owner"

# Rol ierarxiyasi: yuqori raqam = katta huquq
ROLE_LEVEL: dict[Role, int] = {
    Role.CASHIER:  1,
    Role.MANAGER:  2,
    Role.ADMIN:    3,
    Role.OWNER:    4,
}


# ─────────────────────────────────────────
# Token ma'lumotlari
# ─────────────────────────────────────────
@dataclass(frozen=True)
class TokenData:
    user_id:   uuid.UUID
    tenant_id: uuid.UUID
    role:      Role
    full_name: str
    phone:     str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int
    user:          dict
    tenant_id:     str


# ─────────────────────────────────────────
# JWT ochiq kalitini Keycloak dan olish
# ─────────────────────────────────────────
_keycloak_public_key: str | None = None

async def _get_keycloak_public_key() -> str:
    global _keycloak_public_key
    if _keycloak_public_key:
        return _keycloak_public_key

    url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

    raw = data["public_key"]
    _keycloak_public_key = (
        f"-----BEGIN PUBLIC KEY-----\n{raw}\n-----END PUBLIC KEY-----"
    )
    return _keycloak_public_key


# ─────────────────────────────────────────
# Token tekshirish
# ─────────────────────────────────────────
bearer_scheme = HTTPBearer()

async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(bearer_scheme)],
) -> TokenData:
    """JWT tokenni tekshiradi va TokenData qaytaradi"""
    token = credentials.credentials

    try:
        public_key = await _get_keycloak_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz yoki muddati o'tgan",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Keycloak token tuzilmasi
    user_id   = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role_str  = payload.get("role", "cashier")

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token to'liq emas",
        )

    try:
        role = Role(role_str)
    except ValueError:
        role = Role.CASHIER

    return TokenData(
        user_id=uuid.UUID(user_id),
        tenant_id=uuid.UUID(tenant_id),
        role=role,
        full_name=payload.get("name", ""),
        phone=payload.get("preferred_username", ""),
    )


# ─────────────────────────────────────────
# RBAC dependency fabrikasi
# ─────────────────────────────────────────
def require_role(minimum_role: Role):
    """Minimal rol darajasini talab qiladigan dependency yaratadi"""
    async def checker(
        token: Annotated[TokenData, Depends(verify_token)],
    ) -> TokenData:
        if ROLE_LEVEL[token.role] < ROLE_LEVEL[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bu amal uchun kamida '{minimum_role.value}' roli talab etiladi",
            )
        return token
    return checker


# ─────────────────────────────────────────
# Tayyor dependency lari (endpointlarda ishlatish uchun)
# ─────────────────────────────────────────
RequireAuth    = Annotated[TokenData, Depends(verify_token)]
RequireCashier = Annotated[TokenData, Depends(require_role(Role.CASHIER))]
RequireManager = Annotated[TokenData, Depends(require_role(Role.MANAGER))]
RequireAdmin   = Annotated[TokenData, Depends(require_role(Role.ADMIN))]
RequireOwner   = Annotated[TokenData, Depends(require_role(Role.OWNER))]
