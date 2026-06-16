"""
ha/client.py — Cliente para la REST API de Home Assistant

Home Assistant expone todos sus dispositivos y servicios a través de
una API REST interna en http://127.0.0.1:8123/api/

Este módulo es el "puente" entre ha-mcp y Home Assistant.
Cada tool de luces/switches llama a este cliente para:
  - Consultar el estado actual de un dispositivo
  - Listar todos los dispositivos disponibles
  - Ejecutar servicios (encender, apagar, etc.)

Usamos aiohttp en lugar de la librería requests porque es "async":
no bloquea el servidor mientras espera la respuesta de HA. Esto permite
que ha-mcp atienda múltiples peticiones al mismo tiempo.

El token HA_TOKEN del .env va en el header Authorization de cada petición.
Home Assistant lo usa para verificar que quien llama tiene permiso.
"""

import aiohttp

from src.config import settings


class HAClient:
    """Cliente async para la REST API de Home Assistant."""

    def __init__(self):
        # URL base de HA dentro del VPS (nunca sale al exterior)
        self.base_url = settings.ha_url.rstrip("/")

        # Headers que van en cada petición a HA
        # El Long-Lived Token le dice a HA "soy ha-mcp y tengo permiso"
        self.headers = {
            "Authorization": f"Bearer {settings.ha_token}",
            "Content-Type": "application/json",
        }

    async def get_state(self, entity_id: str) -> dict:
        """
        Consulta el estado actual de una entidad específica.

        Ejemplo de entity_id: "switch.luz_de_la_sala_interruptor_1"
        HA responde con un dict que incluye "state" (on/off) y "attributes"
        (nombre amigable, brillo, color, etc.)
        """
        url = f"{self.base_url}/api/states/{entity_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                resp.raise_for_status()  # Lanza error si HA responde 4xx/5xx
                return await resp.json()

    async def list_states(self, domain: str | None = None) -> list[dict]:
        """
        Lista todas las entidades de HA, con filtro opcional por dominio.

        Dominios comunes: "light" (luces), "switch" (enchufes/interruptores),
        "sensor" (sensores), "climate" (aires acondicionados).

        Sin filtro devuelve TODAS las entidades (pueden ser cientos).
        """
        url = f"{self.base_url}/api/states"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                resp.raise_for_status()
                states = await resp.json()

        # Filtrar por dominio si se especificó
        # El entity_id siempre tiene formato "dominio.nombre"
        if domain:
            states = [s for s in states if s["entity_id"].startswith(f"{domain}.")]
        return states

    async def call_service(self, domain: str, service: str, data: dict) -> dict:
        """
        Ejecuta un servicio de HA — aquí es donde ocurre la acción real.

        Ejemplos:
          domain="switch", service="turn_on",  data={"entity_id": "switch.sala"}
          domain="light",  service="turn_on",  data={"entity_id": "light.salon", "brightness_pct": 80}
          domain="light",  service="turn_off", data={"entity_id": "light.salon"}

        HA recibe la petición y la traduce en una señal WiFi hacia el dispositivo Tuya.
        """
        url = f"{self.base_url}/api/services/{domain}/{service}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as resp:
                resp.raise_for_status()
                return await resp.json()


# Instancia global — se crea una sola vez al arrancar el servidor
# Todos los módulos de tools importan este objeto
ha_client = HAClient()
