from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.auth import create_jwt, verify_ha_credentials

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 28800  # 8 horas en segundos


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    ok = await verify_ha_credentials(body.username, body.password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    token = create_jwt(body.username)
    return LoginResponse(access_token=token)
