"""
main.py — Punto de entrada del servidor ha-mcp

Este es el primer archivo que se ejecuta cuando arranca el servidor.
Crea la aplicación FastAPI y le "conecta" los dos módulos principales:
  - auth_router: maneja el login (POST /auth/login)
  - mcp_router:  maneja las tool-calls de Heinzbot (POST /mcp)

FastAPI es el framework web que recibe las peticiones HTTPS que llegan
desde Nginx y las distribuye al código correcto.

El "lifespan" controla qué pasa al arrancar y al apagar el servidor:
  - Al arrancar: inicia el scheduler de tareas programadas
  - Al apagar:   detiene el scheduler limpiamente
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.auth_router import router as auth_router
from src.mcp.protocol import router as mcp_router
from src.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida del servidor.
    El código antes del 'yield' corre al arrancar.
    El código después del 'yield' corre al apagar.
    """
    scheduler.start()   # Inicia el reloj despertador de tareas programadas
    yield
    scheduler.shutdown()  # Apaga el scheduler limpiamente al detener el servidor


# La aplicación principal — uvicorn la arranca en el puerto 8002
app = FastAPI(
    title="ha-mcp",
    description="MCP server para Home Assistant — Heinzbot",
    version="1.0.0",
    lifespan=lifespan,
)

# Registrar los dos grupos de endpoints
app.include_router(auth_router)  # /auth/login
app.include_router(mcp_router)   # /mcp


@app.get("/health")
async def health():
    """
    Endpoint de verificación — responde {"status": "ok"} si el servidor está vivo.
    Lo usa Nginx para saber si el servicio está disponible.
    """
    return {"status": "ok", "service": "ha-mcp"}
