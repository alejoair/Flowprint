from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flowprint.routers.graphs import router as graphs_router
from flowprint.routers.nodes import router as nodes_router

app = FastAPI(title="Flowprint API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes_router)
app.include_router(graphs_router)
