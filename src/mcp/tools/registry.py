from src.mcp.tools.lights import LIGHT_TOOLS, handle_light_tool

# Lista completa de tools disponibles (se expone en tools/list)
ALL_TOOLS = LIGHT_TOOLS

# Nombres de tools agrupados por módulo para el despachador
_LIGHT_TOOL_NAMES = {t["name"] for t in LIGHT_TOOLS}


async def dispatch_tool(name: str, params: dict, user: str) -> str:
    """Dirige la llamada a la tool correcta según su nombre."""
    if name in _LIGHT_TOOL_NAMES:
        return await handle_light_tool(name, params, user)
    return f"Tool '{name}' no encontrada."
