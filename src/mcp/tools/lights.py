"""
mcp/tools/lights.py — Herramientas para controlar luces y switches

Este módulo tiene dos partes:

1. DEFINICIONES (LIGHT_TOOLS): lista de diccionarios que describen cada tool
   en el formato que entiende MCP. Cada tool tiene:
     - name:        identificador único que el LLM usa para llamarla
     - description: texto que le explica al LLM cuándo y cómo usarla
     - inputSchema: qué parámetros acepta y cuáles son obligatorios

   El LLM lee estas descripciones y decide automáticamente qué tool
   llamar según lo que el usuario escribió. Por eso la descripción
   debe ser clara y detallada.

2. EJECUCIÓN (handle_light_tool): la función que realmente hace el trabajo.
   Recibe el nombre de la tool y sus parámetros, llama a Home Assistant
   a través del cliente HA, registra la acción en el log de auditoría,
   y devuelve un texto en español que el LLM usa para responder al usuario.

Dispositivos compatibles:
  - Switches WiFi Tuya registrados en HA como dominio "switch"
  - Luces inteligentes registradas en HA como dominio "light"
  - Cualquier dispositivo HA que soporte los servicios turn_on/turn_off

Para agregar nuevas categorías (sensores, clima, etc.) crea un archivo
nuevo similar a este y regístralo en registry.py.
"""

from src.audit import log_action
from src.ha.client import ha_client

# ─────────────────────────────────────────────────────────────
# PARTE 1: Definición de las tools (lo que ve el LLM)
# ─────────────────────────────────────────────────────────────

LIGHT_TOOLS = [
    {
        "name": "ha_list_lights",
        "description": (
            "Lista todos los dispositivos de luz y switches disponibles en Home Assistant. "
            "Úsala para saber qué entidades existen antes de encender o apagar algo."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "ha_get_light_state",
        "description": "Consulta el estado actual (encendido/apagado) de una luz o switch específico.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID de la entidad en HA, ej: light.salon o switch.enchufe_cocina",
                }
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "ha_turn_on_light",
        "description": (
            "Enciende una luz o switch. Opcionalmente puedes especificar brillo (1-100) "
            "y color en formato RGB para luces que lo soporten."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID de la entidad, ej: light.salon",
                },
                "brightness_pct": {
                    "type": "integer",
                    "description": "Brillo en porcentaje (1-100). Opcional.",
                    "minimum": 1,
                    "maximum": 100,
                },
                "rgb_color": {
                    "type": "array",
                    "description": "Color RGB como [rojo, verde, azul] (0-255 cada uno). Opcional.",
                    "items": {"type": "integer"},
                    "minItems": 3,
                    "maxItems": 3,
                },
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "ha_turn_off_light",
        "description": "Apaga una luz o switch específico.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID de la entidad, ej: light.salon",
                }
            },
            "required": ["entity_id"],
        },
    },
]


# ─────────────────────────────────────────────────────────────
# PARTE 2: Ejecución de las tools (el código que actúa sobre HA)
# ─────────────────────────────────────────────────────────────

async def handle_light_tool(name: str, params: dict, user: str) -> str:
    """
    Ejecuta la tool solicitada y retorna un texto con el resultado.

    El texto que retorna esta función es exactamente lo que el LLM
    recibe para formular su respuesta en lenguaje natural al usuario.
    """

    # ── ha_list_lights ──────────────────────────────────────────
    # Consulta HA y devuelve lista de todos los dispositivos de luz y switch
    if name == "ha_list_lights":
        lights = await ha_client.list_states("light")
        switches = await ha_client.list_states("switch")
        all_entities = lights + switches
        if not all_entities:
            return "No se encontraron luces ni switches en Home Assistant."
        lines = []
        for e in all_entities:
            state = e.get("state", "desconocido")
            # friendly_name es el nombre legible que pusiste en HA (ej: "Luz de la sala")
            friendly = e.get("attributes", {}).get("friendly_name", e["entity_id"])
            lines.append(f"- {friendly} ({e['entity_id']}): {state}")
        return "Dispositivos disponibles:\n" + "\n".join(lines)

    # ── ha_get_light_state ──────────────────────────────────────
    # Consulta el estado actual de una entidad específica
    if name == "ha_get_light_state":
        entity_id = params["entity_id"]
        data = await ha_client.get_state(entity_id)
        state = data.get("state", "desconocido")
        friendly = data.get("attributes", {}).get("friendly_name", entity_id)
        attrs = data.get("attributes", {})
        result = f"{friendly} está {state}"
        if "brightness" in attrs:
            # HA almacena el brillo en escala 0-255, lo convertimos a porcentaje
            pct = round(attrs["brightness"] / 255 * 100)
            result += f", brillo al {pct}%"
        return result

    # ── ha_turn_on_light ────────────────────────────────────────
    # Enciende el dispositivo. El dominio se extrae del entity_id
    # (ej: "switch.sala" → dominio "switch", "light.salon" → dominio "light")
    if name == "ha_turn_on_light":
        entity_id = params["entity_id"]
        domain = entity_id.split(".")[0]  # "switch" o "light"
        service_data: dict = {"entity_id": entity_id}

        # Parámetros opcionales — solo se envían a HA si el LLM los incluyó
        if "brightness_pct" in params:
            service_data["brightness_pct"] = params["brightness_pct"]
        if "rgb_color" in params:
            service_data["rgb_color"] = params["rgb_color"]

        await ha_client.call_service(domain, "turn_on", service_data)

        # Registramos la acción en el log de auditoría (solo escrituras)
        log_action(user, name, params, "ok")

        # Intentamos obtener el nombre amigable para la respuesta
        friendly = entity_id
        try:
            state_data = await ha_client.get_state(entity_id)
            friendly = state_data.get("attributes", {}).get("friendly_name", entity_id)
        except Exception:
            pass
        return f"{friendly} encendido correctamente."

    # ── ha_turn_off_light ───────────────────────────────────────
    # Apaga el dispositivo
    if name == "ha_turn_off_light":
        entity_id = params["entity_id"]
        domain = entity_id.split(".")[0]
        await ha_client.call_service(domain, "turn_off", {"entity_id": entity_id})
        log_action(user, name, params, "ok")
        friendly = entity_id
        try:
            state_data = await ha_client.get_state(entity_id)
            friendly = state_data.get("attributes", {}).get("friendly_name", entity_id)
        except Exception:
            pass
        return f"{friendly} apagado correctamente."

    return f"Tool desconocida: {name}"
