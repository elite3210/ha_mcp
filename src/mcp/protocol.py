"""
mcp/protocol.py — Handler del protocolo MCP (Model Context Protocol)

MCP es el protocolo que usa Heinzbot para hablar con servidores de herramientas.
Funciona sobre HTTP usando el formato JSON-RPC 2.0: cada mensaje tiene
un "method" que indica qué se quiere hacer y "params" con los argumentos.

Este módulo es el "traductor" entre Heinzbot y nuestras tools:
  1. Recibe el mensaje JSON de Heinzbot en POST /mcp
  2. Verifica que el Bearer JWT sea válido
  3. Lee el "method" del mensaje y lo dirige al código correcto
  4. Devuelve la respuesta en el formato que MCP espera

Los cuatro métodos que implementamos:
  - initialize:              el LLM saluda al servidor al conectarse
  - notifications/initialized: el LLM confirma que recibió el saludo
  - tools/list:              el LLM pregunta "¿qué herramientas tienes?"
  - tools/call:              el LLM dice "ejecuta esta herramienta con estos parámetros"

Spec oficial: https://spec.modelcontextprotocol.io/specification/2025-03-26/
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth import get_current_user
from src.mcp.tools.registry import ALL_TOOLS, dispatch_tool

router = APIRouter()

# HTTPBearer extrae automáticamente el token del header "Authorization: Bearer ..."
bearer = HTTPBearer()

SERVER_INFO = {
    "name": "ha-mcp",
    "version": "1.0.0",
    "description": "MCP server para Home Assistant — Heinzbot",
}


def _ok(request_id, result: dict) -> dict:
    """Construye una respuesta JSON-RPC exitosa."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id, code: int, message: str) -> dict:
    """Construye una respuesta JSON-RPC de error."""
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


@router.post("/mcp")
async def mcp_handler(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    """
    Punto de entrada único para todas las llamadas MCP de Heinzbot.

    FastAPI llama automáticamente a get_current_user() antes de ejecutar
    este código — si el JWT es inválido, FastAPI devuelve 401 y ni
    llegamos aquí.
    """
    # Identificar quién hace la llamada (viene del JWT)
    user = get_current_user(credentials)

    # Parsear el cuerpo JSON de la petición
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_error(None, -32700, "Parse error"), status_code=400)

    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    # El LLM saluda al servidor al iniciar la sesión
    # Respondemos con información del servidor y sus capacidades
    if method == "initialize":
        return JSONResponse(_ok(req_id, {
            "protocolVersion": "2025-03-26",
            "serverInfo": SERVER_INFO,
            "capabilities": {"tools": {}},
        }))

    # Confirmación de inicialización — solo acusamos recibo
    if method == "notifications/initialized":
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {}})

    # El LLM pregunta qué tools están disponibles
    # Respondemos con el catálogo completo definido en registry.py
    if method == "tools/list":
        return JSONResponse(_ok(req_id, {"tools": ALL_TOOLS}))

    # El LLM quiere ejecutar una tool específica
    # Delegamos al registry que sabe a qué módulo enviar la llamada
    if method == "tools/call":
        tool_name = params.get("name")
        tool_params = params.get("arguments", {})
        if not tool_name:
            return JSONResponse(_error(req_id, -32602, "Falta 'name' en params"))
        try:
            result_text = await dispatch_tool(tool_name, tool_params, user)
            # Importante: los errores de tool van en result con isError=True,
            # NO como errores HTTP. Así lo define la spec MCP.
            return JSONResponse(_ok(req_id, {
                "content": [{"type": "text", "text": result_text}],
                "isError": False,
            }))
        except Exception as exc:
            return JSONResponse(_ok(req_id, {
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            }))

    return JSONResponse(_error(req_id, -32601, f"Método no implementado: {method}"))
