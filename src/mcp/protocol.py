"""
Handler del protocolo MCP (Model Context Protocol) Streamable HTTP.
Spec: https://spec.modelcontextprotocol.io/specification/2025-03-26/
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth import get_current_user
from src.mcp.tools.registry import ALL_TOOLS, dispatch_tool

router = APIRouter()
bearer = HTTPBearer()

SERVER_INFO = {
    "name": "ha-mcp",
    "version": "1.0.0",
    "description": "MCP server para Home Assistant — Heinzbot",
}


def _ok(request_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


@router.post("/mcp")
async def mcp_handler(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    user = get_current_user(credentials)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_error(None, -32700, "Parse error"), status_code=400)

    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    # initialize — saludo inicial del LLM al servidor
    if method == "initialize":
        return JSONResponse(_ok(req_id, {
            "protocolVersion": "2025-03-26",
            "serverInfo": SERVER_INFO,
            "capabilities": {"tools": {}},
        }))

    # notifications/initialized — el cliente confirma la inicialización (no requiere respuesta)
    if method == "notifications/initialized":
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {}})

    # tools/list — el LLM pregunta qué tools hay disponibles
    if method == "tools/list":
        return JSONResponse(_ok(req_id, {"tools": ALL_TOOLS}))

    # tools/call — el LLM quiere ejecutar una tool
    if method == "tools/call":
        tool_name = params.get("name")
        tool_params = params.get("arguments", {})
        if not tool_name:
            return JSONResponse(_error(req_id, -32602, "Falta 'name' en params"))
        try:
            result_text = await dispatch_tool(tool_name, tool_params, user)
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
