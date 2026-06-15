from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from src.config import settings
from src.ha.client import ha_client


async def verify_ha_credentials(username: str, password: str) -> bool:
    """Verifica usuario/contraseña contra Home Assistant usando su API de auth."""
    import aiohttp

    url = f"{settings.ha_url.rstrip('/')}/api/auth/token"
    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": "http://localhost/",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                return resp.status == 200
    except Exception:
        return False


def create_jwt(username: str) -> str:
    """Crea un JWT firmado con los datos del usuario."""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    """Verifica y decodifica un JWT. Lanza HTTPException si es inválido o expiró."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )


def get_current_user(credentials: HTTPAuthorizationCredentials) -> str:
    """Extrae el usuario del Bearer token. Usado como dependencia en los endpoints."""
    payload = decode_jwt(credentials.credentials)
    return payload["sub"]
