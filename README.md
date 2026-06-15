# ha-mcp

Servidor MCP (Model Context Protocol) para controlar Home Assistant desde Heinzbot.

## Arquitectura

```mermaid
flowchart TD
    A([Heinzbot Android]) -->|POST Bearer JWT / HTTPS| B

    subgraph VPS["VPS Hostinger — jarvis.heinzsport.com"]
        B[Nginx :443 SSL] -->|/auth| C
        B -->|/mcp| C
        C[FastAPI ha-mcp :8002]
        C -->|REST API interna| D[Home Assistant :8123]
        D -->|controla| E([Dispositivos Tuya / otros])
    end
```

## Flujo de autenticación

```mermaid
sequenceDiagram
    participant H as Heinzbot
    participant A as /auth/login
    participant M as /mcp
    participant HA as Home Assistant

    H->>A: POST {username, password}
    A->>HA: Verifica credenciales
    HA-->>A: OK
    A-->>H: JWT (válido 8h)

    H->>M: POST {method, params} + Bearer JWT
    M->>M: Valida JWT
    M->>HA: Llama REST API
    HA-->>M: Estado / resultado
    M-->>H: JSON-RPC response
```

## Herramientas disponibles

| Tool | Descripción |
|------|-------------|
| `ha_list_lights` | Lista luces y switches disponibles |
| `ha_get_light_state` | Estado actual de una luz/switch |
| `ha_turn_on_light` | Enciende (con brillo y color opcionales) |
| `ha_turn_off_light` | Apaga una luz o switch |

## Estructura del proyecto

```mermaid
graph LR
    A[src/main.py] --> B[auth_router.py]
    A --> C[mcp/protocol.py]
    B --> D[auth.py]
    C --> E[mcp/tools/registry.py]
    E --> F[mcp/tools/lights.py]
    F --> G[ha/client.py]
    D --> G
```

## Instalación en VPS

```bash
# 1. Clonar
mkdir -p /opt/ha-mcp && cd /opt/ha-mcp
git clone https://github.com/elite3210/ha_mcp.git .

# 2. Entorno virtual
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configurar
cp .env.example .env
nano .env   # completar HA_TOKEN y JWT_SECRET

# 4. Permisos
chown -R odoo:odoo /opt/ha-mcp

# 5. Servicio systemd
cp systemd/ha-mcp.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ha-mcp
systemctl start ha-mcp

# 6. Verificar
curl http://127.0.0.1:8002/health
```

## Variables de entorno

Ver `.env.example` para la lista completa.

## Generar JWT_SECRET

```bash
openssl rand -hex 32
```
