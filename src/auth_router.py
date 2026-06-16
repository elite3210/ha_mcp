"""
auth_router.py — Endpoint de login: POST /auth/login

Este módulo define el único endpoint de autenticación del servidor.
Funciona como el "portero": recibe usuario y contraseña, verifica que
sean correctos, y entrega un JWT que sirve como pase de acceso.

Flujo completo:
  Heinzbot → POST /auth/login {username, password}
           ← {access_token: "eyJ...", token_type: "bearer", expires_in: 28800}

En producción, Heinzbot guarda el access_token y lo envía en el header
Authorization de cada llamada a /mcp.

Nota: en la versión actual este endpoint NO se usa porque Heinzbot
solo acepta tokens preconfigurados. Lo dejamos implementado para cuando
Heinzbot soporte el flujo de login completo.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.auth import create_jwt, verify_credentials

# Prefijo /auth — todas las rutas de este router empiezan con /auth
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Cuerpo de la petición de login."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Respuesta exitosa del login — contiene el token JWT."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 28800  # 8 horas expresadas en segundos


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """
    Verifica las credenciales y devuelve un JWT.

    Si las credenciales son incorrectas devuelve HTTP 401.
    Si son correctas genera el JWT y lo devuelve.
    """
    ok = verify_credentials(body.username, body.password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    token = create_jwt(body.username)
    return LoginResponse(access_token=token)
