"""
mcp/tools/scheduler_tools.py — Herramientas para programar encendido/apagado

Permite decirle a Heinzbot cosas como:
  "Enciende la luz de la sala a las 6pm"
  "Apaga el dormitorio a las 11pm"
  "¿Qué tengo programado?"
  "Cancela lo de las 6pm"

Cómo funciona internamente:
  1. El LLM llama a ha_schedule_action con entity_id, action y hora
  2. Calculamos la fecha/hora exacta en zona horaria Lima
  3. APScheduler registra el trabajo y espera hasta esa hora
  4. A la hora indicada, APScheduler llama a Home Assistant automáticamente

Las tres tools:
  - ha_schedule_action  → programa una acción
  - ha_list_schedules   → lista trabajos pendientes
  - ha_cancel_schedule  → cancela un trabajo pendiente
"""

import uuid
from datetime import datetime

from src.audit import log_action
from src.ha.client import ha_client
from src.scheduler import LIMA_TZ, job_registry, scheduler

# ─────────────────────────────────────────────────────────────
# PARTE 1: Definición de las tools (lo que ve el LLM)
# ─────────────────────────────────────────────────────────────

SCHEDULER_TOOLS = [
    {
        "name": "ha_schedule_action",
        "description": (
            "Programa encender o apagar un dispositivo a una hora específica. "
            "Por defecto lo programa para hoy en hora de Lima (Perú). "
            "Usa esta tool cuando el usuario diga algo como 'enciende X a las 6pm' o 'apaga Y a las 11pm'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "ID de la entidad en HA, ej: switch.luz_de_la_sala_interruptor_1",
                },
                "action": {
                    "type": "string",
                    "enum": ["on", "off"],
                    "description": "on para encender, off para apagar",
                },
                "time": {
                    "type": "string",
                    "description": "Hora en formato HH:MM (24h), ej: 18:00 para las 6pm, 23:00 para las 11pm",
                },
                "date": {
                    "type": "string",
                    "description": "Fecha en formato YYYY-MM-DD. Si no se especifica, se usa hoy en hora Lima.",
                },
            },
            "required": ["entity_id", "action", "time"],
        },
    },
    {
        "name": "ha_list_schedules",
        "description": "Lista todas las programaciones de encendido/apagado que están pendientes de ejecutarse.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "ha_cancel_schedule",
        "description": "Cancela una programación pendiente antes de que se ejecute. Usa ha_list_schedules primero para ver el ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "ID corto de la programación a cancelar (ej: a1b2c3d4)",
                },
            },
            "required": ["job_id"],
        },
    },
]


# ─────────────────────────────────────────────────────────────
# PARTE 2: Función que APScheduler ejecuta a la hora indicada
# ─────────────────────────────────────────────────────────────

async def _run_scheduled_action(job_id: str, entity_id: str, action: str, user: str) -> None:
    """
    Esta función la llama APScheduler automáticamente a la hora programada.
    No la llama el LLM directamente — es el "despertador" interno.
    """
    domain = entity_id.split(".")[0]  # "switch" o "light"
    await ha_client.call_service(domain, f"turn_{action}", {"entity_id": entity_id})
    log_action(user, "ha_schedule_action_executed", {"entity_id": entity_id, "action": action}, "ok")
    # Limpiar del registro de metadatos después de ejecutar
    job_registry.pop(job_id, None)


# ─────────────────────────────────────────────────────────────
# PARTE 3: Ejecución de las tools (llamadas por el LLM)
# ─────────────────────────────────────────────────────────────

async def handle_scheduler_tool(name: str, params: dict, user: str) -> str:

    # ── ha_schedule_action ──────────────────────────────────────
    if name == "ha_schedule_action":
        entity_id = params["entity_id"]
        action    = params["action"]       # "on" o "off"
        time_str  = params["time"]         # "18:00"
        date_str  = params.get("date")     # "2026-06-17" o None

        # Parsear la hora HH:MM
        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            return "Formato de hora incorrecto. Usa HH:MM, ejemplo: 18:00"

        # Calcular la fecha objetivo en Lima (hoy si no se especificó)
        now_lima = datetime.now(LIMA_TZ)
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return "Formato de fecha incorrecto. Usa YYYY-MM-DD, ejemplo: 2026-06-17"
        else:
            target_date = now_lima.date()

        # Construir la fecha/hora completa en zona Lima
        scheduled_dt = LIMA_TZ.localize(
            datetime(target_date.year, target_date.month, target_date.day, hour, minute)
        )

        # Verificar que la hora no sea en el pasado
        if scheduled_dt <= now_lima:
            return (
                f"La hora {time_str} del {target_date} ya pasó en hora Lima. "
                f"Ahora son las {now_lima.strftime('%H:%M')}. Indica una hora futura."
            )

        # Generar un ID corto y legible para el trabajo
        job_id = uuid.uuid4().hex[:8]

        # Consultar nombre amigable de la entidad para el mensaje de confirmación
        friendly = entity_id
        try:
            state_data = await ha_client.get_state(entity_id)
            friendly = state_data.get("attributes", {}).get("friendly_name", entity_id)
        except Exception:
            pass

        # Registrar el trabajo en APScheduler — se ejecutará una sola vez
        scheduler.add_job(
            _run_scheduled_action,
            trigger="date",            # trigger "date" = una sola vez en fecha/hora exacta
            run_date=scheduled_dt,
            args=[job_id, entity_id, action, user],
            id=job_id,
        )

        # Guardar metadatos legibles para mostrar en ha_list_schedules
        accion_texto = "encender" if action == "on" else "apagar"
        job_registry[job_id] = {
            "entity_id": entity_id,
            "friendly":  friendly,
            "action":    action,
            "hora":      scheduled_dt.strftime("%H:%M"),
            "fecha":     scheduled_dt.strftime("%d/%m/%Y"),
            "descripcion": f"{accion_texto.capitalize()} {friendly} a las {scheduled_dt.strftime('%H:%M')} del {scheduled_dt.strftime('%d/%m/%Y')}",
        }

        log_action(user, name, params, f"programado job_id={job_id}")
        return (
            f"Programado: {accion_texto} '{friendly}' a las {scheduled_dt.strftime('%H:%M')} "
            f"del {scheduled_dt.strftime('%d/%m/%Y')} (hora Lima). ID: {job_id}"
        )

    # ── ha_list_schedules ───────────────────────────────────────
    if name == "ha_list_schedules":
        if not job_registry:
            return "No hay programaciones pendientes."
        lines = ["Programaciones pendientes:"]
        for jid, meta in job_registry.items():
            lines.append(f"- [{jid}] {meta['descripcion']}")
        return "\n".join(lines)

    # ── ha_cancel_schedule ──────────────────────────────────────
    if name == "ha_cancel_schedule":
        job_id = params["job_id"]
        if job_id not in job_registry:
            return f"No se encontró ninguna programación con ID '{job_id}'."
        meta = job_registry[job_id]
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
        job_registry.pop(job_id, None)
        log_action(user, name, params, "cancelado")
        return f"Programación cancelada: {meta['descripcion']}"

    return f"Tool desconocida: {name}"
