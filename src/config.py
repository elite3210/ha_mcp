from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ha_url: str = "http://127.0.0.1:8123"
    ha_token: str

    # Credenciales locales para el login de Heinzbot → ha-mcp
    mcp_username: str
    mcp_password: str

    jwt_secret: str
    jwt_expire_hours: int = 8

    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8002

    audit_log_path: str = "/opt/ha-mcp/audit.jsonl"

    class Config:
        env_file = ".env"


settings = Settings()
