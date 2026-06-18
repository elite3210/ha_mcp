"""
scheduler.py — Programador de tareas en segundo plano

APScheduler es una librería que funciona como un "reloj despertador" dentro
del servidor. Permite decirle "a las 18:00 de hoy, ejecuta esta función" y
él se encarga de esperar y ejecutarla en el momento correcto.

Usamos AsyncIOScheduler porque nuestro servidor FastAPI es async — así el
scheduler corre en el mismo loop de eventos sin bloquear nada.

Zona horaria: America/Lima (UTC-5) — todas las horas se interpretan en
hora de Lima, no en UTC del servidor.

LIMITACIÓN IMPORTANTE: los trabajos viven en memoria RAM. Si el servidor
se reinicia, los trabajos pendientes se pierden. Para programaciones del
mismo día esto es aceptable. En el futuro se puede agregar persistencia
con JobStoreSQLAlchemy si se necesita.
"""

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Zona horaria de Lima — UTC-5
LIMA_TZ = pytz.timezone("America/Lima")

# Instancia del scheduler — se inicia en main.py al arrancar el servidor
scheduler = AsyncIOScheduler(timezone=LIMA_TZ)

# Registro de metadatos de trabajos pendientes
# APScheduler guarda el trabajo internamente, pero aquí guardamos información
# legible para mostrársela al usuario cuando pregunte qué tiene programado.
# Formato: { job_id: { "descripcion": ..., "entity_id": ..., "action": ..., "hora": ... } }
job_registry: dict[str, dict] = {}
