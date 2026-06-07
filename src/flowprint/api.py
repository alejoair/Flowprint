from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute, APIWebSocketRoute
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders
from fastmcp import FastMCP

from flowprint.mcp_tools import register as register_mcp_tools
from flowprint.routers.graphs import router as graphs_router
from flowprint.routers.nodes import router as nodes_router

_STATIC_DIR = Path(__file__).parent / "static"

# ---------------------------------------------------------------------------
# Core REST API
# ---------------------------------------------------------------------------

_api = FastAPI(title="Flowprint API")
_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_api.include_router(nodes_router)
_api.include_router(graphs_router)

# ---------------------------------------------------------------------------
# MCP server generated from the REST API + curated tools
# Exposed at /mcp  (streamable-http transport, compatible with MCP clients)
# ---------------------------------------------------------------------------

_mcp = FastMCP.from_fastapi(app=_api, name="Flowprint")
register_mcp_tools(_mcp)
_mcp_app = _mcp.http_app(path="/mcp")

# ---------------------------------------------------------------------------
# Combined app — REST + MCP served from the same process
# ---------------------------------------------------------------------------

_api_routes = [r for r in _api.routes if isinstance(r, (APIRoute, APIWebSocketRoute))]

app = FastAPI(
    title="Flowprint",
    description="Multi-agent orchestration engine with Blueprint-style execution.",
    routes=[*_mcp_app.routes, *_api_routes],
    lifespan=_mcp_app.lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static frontend — served at /ui/, index at /
# ---------------------------------------------------------------------------

class _NoCacheStaticFiles(StaticFiles):
    async def __call__(self, scope, receive, send):
        async def _send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("Cache-Control", "no-cache, no-store, must-revalidate")
                headers.append("Pragma", "no-cache")
                headers.append("Expires", "0")
            await send(message)
        await super().__call__(scope, receive, _send)

if (_STATIC_DIR / "index.html").exists():
    app.mount("/ui", _NoCacheStaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def _index():
        return FileResponse(
            _STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
