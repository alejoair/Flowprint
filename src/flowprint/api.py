from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute, APIWebSocketRoute
from fastmcp import FastMCP

from flowprint.routers.graphs import router as graphs_router
from flowprint.routers.nodes import router as nodes_router

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
# MCP server generated from the REST API
# Exposed at /mcp  (streamable-http transport, compatible with MCP clients)
# ---------------------------------------------------------------------------

_mcp = FastMCP.from_fastapi(app=_api, name="Flowprint")
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
