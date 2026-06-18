"""
mcp/tools/registry.py — Catálogo central de herramientas (tools)

Este módulo tiene dos responsabilidades:

1. CATÁLOGO (ALL_TOOLS): agrupa la definición de todas las tools disponibles.
   Cuando Heinzbot pregunta "¿qué puedes hacer?" (método tools/list),
   protocol.py devuelve esta lista. El LLM la lee y sabe qué tool llamar
   según lo que el usuario le pida.

2. DESPACHADOR (dispatch_tool): cuando llega una llamada a una tool específica,
   este módulo decide a qué archivo de código enviarla.

   Ejemplo: si llega "ha_turn_on_light"   → va a lights.py
            si llega "ha_schedule_action" → va a scheduler_tools.py
            si en el futuro agregamos "ha_get_temperature" → irá a sensors.py

Cómo agregar una nueva categoría de tools (ejemplo: sensores):
  1. Crear src/mcp/tools/sensors.py con SENSOR_TOOLS y handle_sensor_tool()
  2. Importar aquí: from src.mcp.tools.sensors import SENSOR_TOOLS, handle_sensor_tool
  3. Agregar a ALL_TOOLS: ALL_TOOLS = LIGHT_TOOLS + SENSOR_TOOLS + SCHEDULER_TOOLS
  4. Agregar al despachador el bloque correspondiente

El resto del servidor (main.py, protocol.py, auth.py) no necesita cambios.
"""

from src.mcp.tools.lights import LIGHT_TOOLS, handle_light_tool
from src.mcp.tools.scheduler_tools import SCHEDULER_TOOLS, handle_scheduler_tool

# Catálogo completo — aquí se suman todas las tools de todos los módulos
ALL_TOOLS = LIGHT_TOOLS + SCHEDULER_TOOLS

# Sets con los nombres de tools por módulo para búsqueda rápida
_LIGHT_TOOL_NAMES     = {t["name"] for t in LIGHT_TOOLS}
_SCHEDULER_TOOL_NAMES = {t["name"] for t in SCHEDULER_TOOLS}


async def dispatch_tool(name: str, params: dict, user: str) -> str:
    """
    Recibe el nombre de una tool y la envía al módulo correcto.

    Retorna siempre un string con el resultado — ese texto es lo que
    el LLM recibe y usa para responderle al usuario en lenguaje natural.
    """
    if name in _LIGHT_TOOL_NAMES:
        return await handle_light_tool(name, params, user)

    if name in _SCHEDULER_TOOL_NAMES:
        return await handle_scheduler_tool(name, params, user)

    return f"Tool '{name}' no encontrada."
