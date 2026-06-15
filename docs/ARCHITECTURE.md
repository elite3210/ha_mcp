# ARCHITECTURE.md — Arquitectura del Sistema

**Proyecto:** ha-mcp  
**Versión:** 1.0  
**Última actualización:** 2026-06-15

---

## 1. Visión general

ha-mcp es un servidor intermediario (middleware) que traduce el protocolo MCP — usado por LLMs para hacer tool-calls — en llamadas a la REST API de Home Assistant.

```mermaid
flowchart TD
    subgraph Internet
        HB([Heinzbot Android])
    end

    subgraph VPS["VPS Hostinger — Ubuntu"]
        subgraph Nginx["Nginx :443 — jarvis.heinzsport.com"]
            N1[SSL Termination]
            N2[Reverse Proxy]
        end

        subgraph HAMCP["ha-mcp — FastAPI :8002"]
            AUTH[auth_router\nPOST /auth/login]
            MCP[mcp/protocol\nPOST /mcp]
            TOOLS[tools/registry\nlights.py ...]
            CLIENT[ha/client\naiohttp async]
            AUDIT[(audit.jsonl)]
        end

        subgraph HA["Home Assistant :8123"]
            HAAPI[REST API]
            DEVICES([Dispositivos\nTuya / otros])
        end
    end

    HB -->|HTTPS Bearer JWT| N1
    N1 --> N2
    N2 -->|/auth| AUTH
    N2 -->|/mcp| MCP
    AUTH -->|verifica| CLIENT
    MCP -->|valida JWT| AUTH
    MCP --> TOOLS
    TOOLS --> CLIENT
    TOOLS --> AUDIT
    CLIENT -->|HTTP interno| HAAPI
    HAAPI --> DEVICES
```

---

## 2. Capas del sistema

```mermaid
graph TB
    subgraph L1["Capa 1 — Transporte"]
        NGINX[Nginx + SSL]
    end
    subgraph L2["Capa 2 — Auth"]
        JWT[JWT Handler]
        LOGIN[POST /auth/login]
    end
    subgraph L3["Capa 3 — Protocolo MCP"]
        PROTO[JSON-RPC Handler\nPOST /mcp]
    end
    subgraph L4["Capa 4 — Tools"]
        REG[Registry]
        LIGHTS[lights.py]
        FUTURE[... futuras tools]
    end
    subgraph L5["Capa 5 — Integración HA"]
        HACLIENT[HAClient\naiohttp]
    end
    subgraph L6["Capa 6 — Dominio"]
        HAAPI[Home Assistant REST API]
    end

    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 --> L5
    L5 --> L6
```

Cada capa tiene una única responsabilidad. Una nueva tool solo agrega código en L4 — las demás capas no cambian.

---

## 3. Decisiones de arquitectura

### DA-01 — FastAPI como framework

**Decisión:** Usar FastAPI (Python).  
**Razón:** El proyecto odoo-mcp ya usa FastAPI y está funcionando en el mismo VPS. Reusar el mismo stack evita instalar nuevas dependencias y el usuario ya conoce el patrón de despliegue.  
**Alternativas descartadas:** Flask (no async nativo), Node.js (cambio de lenguaje).

### DA-02 — MCP Streamable HTTP (no SSE)

**Decisión:** Implementar el protocolo MCP sobre HTTP puro (POST).  
**Razón:** Heinzbot hace tool-calls síncronas. No necesitamos streaming de eventos. HTTP puro es más simple y compatible con Nginx sin configuración extra.  
**Spec de referencia:** `2025-03-26`

### DA-03 — Long-Lived Token de HA como credencial del servidor

**Decisión:** El servidor usa un token de larga duración de HA (variable `HA_TOKEN`) para todas las llamadas internas.  
**Razón:** Simplifica la arquitectura. El control de acceso lo hace el JWT propio del servidor. No necesitamos re-autenticar contra HA en cada llamada.  
**Implicación:** El `HA_TOKEN` nunca sale del servidor. Los clientes solo ven JWTs de 8h.

### DA-04 — Auditoría en JSON Lines (no base de datos)

**Decisión:** Registrar acciones en un archivo `.jsonl` local.  
**Razón:** Simplicidad de operación. Sin dependencia de base de datos extra. El archivo es legible con `cat` o `jq`. Suficiente para la escala actual (un usuario).  
**Alternativa futura:** SQLite si se necesita búsqueda o múltiples usuarios.

### DA-05 — Puerto 8002 (no 8001)

**Decisión:** El servidor escucha en el puerto 8002.  
**Razón:** El puerto 8001 está ocupado por odoo-mcp en el mismo VPS. Usar 8002 evita conflictos.

---

## 4. Flujo de autenticación

```mermaid
sequenceDiagram
    participant C as Heinzbot
    participant A as auth_router
    participant AH as auth.py
    participant HA as Home Assistant

    C->>A: POST /auth/login {username, password}
    A->>HA: POST /api/auth/token (grant_type=password)
    alt Credenciales válidas
        HA-->>A: 200 OK
        A->>AH: create_jwt(username)
        AH-->>A: JWT firmado (8h)
        A-->>C: {access_token, expires_in: 28800}
    else Credenciales inválidas
        HA-->>A: 401
        A-->>C: 401 Credenciales incorrectas
    end
```

---

## 5. Flujo de una tool-call

```mermaid
sequenceDiagram
    participant C as Heinzbot / LLM
    participant P as mcp/protocol.py
    participant R as tools/registry.py
    participant T as tools/lights.py
    participant HA as ha/client.py

    C->>P: POST /mcp {method: tools/call, name: ha_turn_on_light, ...}
    P->>P: Valida Bearer JWT
    P->>R: dispatch_tool("ha_turn_on_light", params, user)
    R->>T: handle_light_tool(...)
    T->>HA: call_service("light", "turn_on", {entity_id, brightness_pct})
    HA-->>T: 200 OK
    T->>T: log_action(audit.jsonl)
    T-->>P: "Salón encendido correctamente."
    P-->>C: {result: {content: [{type: text, text: ...}]}}
```

---

## 6. Estructura de archivos y responsabilidades

```mermaid
graph LR
    A["main.py\nPunto de entrada\nregistra routers"] --> B["auth_router.py\nPOST /auth/login"]
    A --> C["mcp/protocol.py\nPOST /mcp\nJSON-RPC dispatch"]

    B --> D["auth.py\ncreate_jwt\ndecode_jwt\nverify_ha_credentials"]
    D --> E["config.py\nlee .env\nfuente única de verdad"]

    C --> F["mcp/tools/registry.py\nALL_TOOLS catálogo\ndispatch_tool router"]
    F --> G["mcp/tools/lights.py\nLIGHT_TOOLS defs\nhandle_light_tool exec"]
    G --> H["ha/client.py\nHAClient async\nget_state list_states call_service"]
    G --> I["audit.py\nlog_action\nJSON Lines"]

    H --> E
    I --> E
```

---

## 7. Despliegue en producción

```mermaid
flowchart LR
    GH[GitHub\nelite3210/ha_mcp] -->|git pull| VPS

    subgraph VPS["/opt/ha-mcp — VPS"]
        CODE[Código fuente]
        VENV[.venv Python]
        ENV[.env secretos]
        SVC[systemd ha-mcp.service]
        UVI[uvicorn :8002]
    end

    subgraph Nginx
        SSL[SSL :443]
        PROXY[Proxy /mcp /auth]
    end

    SVC -->|gestiona proceso| UVI
    UVI -->|lee| CODE
    UVI -->|lee| ENV
    Nginx --> UVI
```

---

## 8. Consideraciones de seguridad

| Riesgo | Mitigación |
|--------|-----------|
| Interceptación de tráfico | HTTPS obligatorio via Nginx + Let's Encrypt |
| Acceso sin autenticar | JWT requerido en todo endpoint `/mcp` |
| Exposición del HA_TOKEN | Vive solo en `.env` del servidor, nunca sale |
| JWT robado | Expiración de 8h, sin refresh token |
| Escalada de privilegios | El servidor corre como usuario `odoo` (sin root) |
| Log de acciones | `audit.jsonl` registra quién hizo qué y cuándo |
