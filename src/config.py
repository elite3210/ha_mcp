"""
config.py — Configuración centralizada del servidor

En lugar de escribir los valores de configuración (URL, tokens, puertos)
directamente en el código, los leemos del archivo .env usando pydantic-settings.

Ventaja: si necesitas cambiar algo (por ejemplo el puerto o el token de HA),
solo editas el .env en el VPS y reinicias el servicio — sin tocar el código.

El objeto `settings` se importa en todos los demás módulos como fuente
única de verdad. Así nunca hay valores duplicados ni hardcodeados.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # URL interna de Home Assistant dentro del VPS
    ha_url: str = "http://127.0.0.1:8123"

    # Token de larga duración de HA — permite que ha-mcp actúe sobre los dispositivos.
    # Se crea en HA → perfil de usuario → Tokens de acceso de larga duración.
    ha_token: str

    # Credenciales que configuras en Heinzbot para hacer login a ha-mcp.
    # Son independientes de las credenciales de Home Assistant.
    mcp_username: str
    mcp_password: str

    # Clave secreta con la que firmamos los JWT. Generada con: openssl rand -hex 32
    # Si alguien obtiene este valor puede falsificar tokens, protégelo bien.
    jwt_secret: str
    jwt_expire_hours: int = 8  # Cada token dura 8 horas antes de expirar

    # Dónde escucha el servidor dentro del VPS (Nginx hace de proxy hacia aquí)
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8002  # Puerto 8002 para no chocar con odoo-mcp que usa 8001

    # Ruta del archivo donde se registran todas las acciones (encender, apagar, etc.)
    audit_log_path: str = "/opt/ha-mcp/audit.jsonl"

    class Config:
        env_file = ".env"  # Lee los valores desde este archivo al arrancar


# Instancia global — todos los módulos importan este objeto
settings = Settings()
