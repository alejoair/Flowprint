from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Instance(BaseModel):
    id: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class Connection(BaseModel):
    kind: Literal["exec", "data"]
    from_node: str
    from_pin: str
    to_node: str
    to_pin: str


class Variable(BaseModel):
    name: str
    type: str


class GraphSignature(BaseModel):
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)


class VisualMeta(BaseModel):
    positions: dict[str, list[float]] = Field(default_factory=dict)
    zoom: float = 1.0


class Graph(BaseModel):
    schema_version: str = "1.0"
    signature: GraphSignature = Field(default_factory=GraphSignature)
    variables: list[Variable] = Field(default_factory=list)
    instances: list[Instance]
    connections: list[Connection]
    visual: VisualMeta = Field(default_factory=VisualMeta)

    def exec_connections(self) -> list[Connection]:
        return [c for c in self.connections if c.kind == "exec"]

    def data_connections(self) -> list[Connection]:
        return [c for c in self.connections if c.kind == "data"]
