import aiohttp
from src.config import settings


class HAClient:
    """Cliente async para la REST API de Home Assistant."""

    def __init__(self):
        self.base_url = settings.ha_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.ha_token}",
            "Content-Type": "application/json",
        }

    async def get_state(self, entity_id: str) -> dict:
        """Consulta el estado de una entidad (ej: light.salon)."""
        url = f"{self.base_url}/api/states/{entity_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def list_states(self, domain: str | None = None) -> list[dict]:
        """Lista todas las entidades, opcionalmente filtrando por dominio (light, switch, etc.)."""
        url = f"{self.base_url}/api/states"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                resp.raise_for_status()
                states = await resp.json()
        if domain:
            states = [s for s in states if s["entity_id"].startswith(f"{domain}.")]
        return states

    async def call_service(self, domain: str, service: str, data: dict) -> dict:
        """Llama a un servicio de HA (ej: light.turn_on con entity_id y brightness)."""
        url = f"{self.base_url}/api/services/{domain}/{service}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as resp:
                resp.raise_for_status()
                return await resp.json()


ha_client = HAClient()
