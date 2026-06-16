"""
auth.py — Lógica de autenticación y tokens JWT

JWT (JSON Web Token) funciona como un "pase de acceso" digital:
  1. Heinzbot envía usuario y contraseña al endpoint /auth/login
  2. El servidor verifica las credenciales y genera un JWT firmado
  3. Heinzbot guarda ese JWT y lo envía en cada llamada posterior
  4. El servidor verifica la firma del JWT sin necesitar base de datos

El JWT tiene fecha de expiración. Pasadas las 8 horas (o 1 año en el
caso del token que generamos manualmente para Heinzbot), el token
deja de ser válido y hay que generar uno nuevo.

Las credenciales se verifican contra el .env (MCP_USERNAME / MCP_PASSWORD),
no contra Home Assistant. Así el sistema funciona incluso si HA cambia
su método de autenticación.
"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from src.config import settings


def verify_credentials(username: str, password: str) -> bool:
    """
    Compara usuario y contraseña contra los valores del .env.

    Usamos secrets.compare_digest en lugar de == para evitar "timing attacks":
    un atacante no puede adivinar la contraseña midiendo cuánto tarda la comparación.
    """
    user_ok = secrets.compare_digest(username, settings.mcp_username)
    pass_ok = secrets.compare_digest(password, settings.mcp_password)
    return user_ok and pass_ok


def create_jwt(username: str) -> str:
    """
    Genera un JWT firmado con los datos del usuario.

    El payload contiene:
      - sub: el nombre de usuario (subject)
      - exp: fecha/hora de expiración
      - iat: fecha/hora de emisión (issued at)

    Se firma con JWT_SECRET usando el algoritmo HS256.
    Sin esa clave nadie puede fabricar un token válido.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    """
    Verifica la firma del JWT y lo decodifica.

    Si el token fue manipulado o ya expiró, lanza un error HTTP 401
    que FastAPI devuelve automáticamente al cliente.
    """
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
    """
    Extrae el nombre de usuario del Bearer token que viene en el header.

    Esta función se usa como "dependencia" en los endpoints de FastAPI:
    antes de ejecutar cualquier tool, FastAPI llama aquí para verificar
    que el token es válido. Si no lo es, la petición se rechaza.
    """
    payload = decode_jwt(credentials.credentials)
    return payload["sub"]
