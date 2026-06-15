"""
Tools para controlar luces y switches (Tuya y otros) via Home Assistant.
"""

from src.ha.client import ha_client
from src.audit import log_action

# Definición de las tools en formato MCP (lo que ve Heinzbot / el LLM)
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


async def handle_light_tool(name: str, params: dict, user: str) -> str:
    """Ejecuta la tool de luz solicitada y retorna el resultado como texto."""

    if name == "ha_list_lights":
        lights = await ha_client.list_states("light")
        switches = await ha_client.list_states("switch")
        all_entities = lights + switches
        if not all_entities:
            return "No se encontraron luces ni switches en Home Assistant."
        lines = []
        for e in all_entities:
            state = e.get("state", "desconocido")
            friendly = e.get("attributes", {}).get("friendly_name", e["entity_id"])
            lines.append(f"- {friendly} ({e['entity_id']}): {state}")
        return "Dispositivos disponibles:\n" + "\n".join(lines)

    if name == "ha_get_light_state":
        entity_id = params["entity_id"]
        data = await ha_client.get_state(entity_id)
        state = data.get("state", "desconocido")
        friendly = data.get("attributes", {}).get("friendly_name", entity_id)
        attrs = data.get("attributes", {})
        result = f"{friendly} está {state}"
        if "brightness" in attrs:
            pct = round(attrs["brightness"] / 255 * 100)
            result += f", brillo al {pct}%"
        return result

    if name == "ha_turn_on_light":
        entity_id = params["entity_id"]
        domain = entity_id.split(".")[0]
        service_data: dict = {"entity_id": entity_id}
        if "brightness_pct" in params:
            service_data["brightness_pct"] = params["brightness_pct"]
        if "rgb_color" in params:
            service_data["rgb_color"] = params["rgb_color"]
        await ha_client.call_service(domain, "turn_on", service_data)
        log_action(user, name, params, "ok")
        friendly = entity_id
        try:
            state_data = await ha_client.get_state(entity_id)
            friendly = state_data.get("attributes", {}).get("friendly_name", entity_id)
        except Exception:
            pass
        return f"{friendly} encendido correctamente."

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
