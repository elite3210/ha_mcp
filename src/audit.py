"""
audit.py — Registro de auditoría de acciones

Cada vez que Heinzbot ejecuta una acción que modifica el estado de un
dispositivo (encender, apagar, cambiar brillo), lo registramos aquí.

El formato usado es JSON Lines (.jsonl): un objeto JSON por línea.
Esto lo hace fácil de leer con herramientas estándar de Linux:

  # Ver las últimas 10 acciones:
  tail -10 /opt/ha-mcp/audit.jsonl

  # Buscar todas las veces que se encendió la sala:
  grep "luz_de_la_sala" /opt/ha-mcp/audit.jsonl

Solo registramos acciones de escritura (cambios de estado).
Las consultas de lectura (listar dispositivos, ver estado) no se registran
para no llenar el log con ruido innecesario.
"""

import json
from datetime import datetime, timezone

from src.config import settings


def log_action(user: str, tool: str, params: dict, result: str) -> None:
    """
    Escribe una línea de auditoría en el archivo .jsonl.

    Cada registro contiene:
      - ts:     timestamp UTC de cuando ocurrió la acción
      - user:   quién la ejecutó (nombre de usuario del JWT)
      - tool:   qué tool se llamó (ej: ha_turn_on_light)
      - params: con qué parámetros (ej: {"entity_id": "switch.sala"})
      - result: si fue exitosa o no
    """
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "tool": tool,
        "params": params,
        "result": result,
    }
    try:
        with open(settings.audit_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        # Si no se puede escribir el log (permisos, disco lleno, etc.)
        # dejamos pasar el error silenciosamente para no interrumpir la acción
        pass
