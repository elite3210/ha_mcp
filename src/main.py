"""
main.py — Punto de entrada del servidor ha-mcp

Este es el primer archivo que se ejecuta cuando arranca el servidor.
Crea la aplicación FastAPI y le "conecta" los dos módulos principales:
  - auth_router: maneja el login (POST /auth/login)
  - mcp_router:  maneja las tool-calls de Heinzbot (POST /mcp)

FastAPI es el framework web que recibe las peticiones HTTPS que llegan
desde Nginx y las distribuye al código correcto.
"""

from fastapi import FastAPI

from src.auth_router import router as auth_router
from src.mcp.protocol import router as mcp_router

# La aplicación principal — uvicorn la arranca en el puerto 8002
app = FastAPI(
    title="ha-mcp",
    description="MCP server para Home Assistant — Heinzbot",
    version="1.0.0",
)

# Registrar los dos grupos de endpoints
app.include_router(auth_router)  # /auth/login
app.include_router(mcp_router)   # /mcp


@app.get("/health")
async def health():
    """
    Endpoint de verificación — responde {"status": "ok"} si el servidor está vivo.
    Lo usa Nginx para saber si el servicio está disponible.
    También lo usamos nosotros para confirmar que el despliegue funcionó.
    """
    return {"status": "ok", "service": "ha-mcp"}
