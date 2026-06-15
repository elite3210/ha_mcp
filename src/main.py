from fastapi import FastAPI

from src.auth_router import router as auth_router
from src.mcp.protocol import router as mcp_router

app = FastAPI(
    title="ha-mcp",
    description="MCP server para Home Assistant — Heinzbot",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(mcp_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ha-mcp"}
