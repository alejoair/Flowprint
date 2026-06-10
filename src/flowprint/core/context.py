from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ContextProtocol(Protocol):
    async def get_var(self, name: str) -> Any: ...
    async def set_var(self, name: str, value: Any) -> None: ...
    async def get_node_state(self, instance_id: str) -> dict: ...
    async def update_node_state(self, instance_id: str, patch: dict) -> None: ...
    async def get_node_output(self, instance_id: str) -> Any: ...
    async def set_node_output(self, instance_id: str, value: Any) -> None: ...
    async def append_to_list(self, instance_id: str, key: str, value: Any) -> None: ...


class LocalContext:
    """In-process implementation of ContextProtocol. No Ray required."""

    def __init__(self) -> None:
        self._variables: dict[str, Any] = {}
        self._node_state: dict[str, dict] = {}

    async def get_var(self, name: str) -> Any:
        return self._variables.get(name)

    async def set_var(self, name: str, value: Any) -> None:
        self._variables[name] = value

    async def get_node_state(self, instance_id: str) -> dict:
        return self._node_state.setdefault(instance_id, {})

    async def update_node_state(self, instance_id: str, patch: dict) -> None:
        self._node_state.setdefault(instance_id, {}).update(patch)

    async def get_node_output(self, instance_id: str) -> Any:
        return self._node_state.get(instance_id, {}).get("__out__")

    async def set_node_output(self, instance_id: str, value: Any) -> None:
        # Store as plain dict so the value survives cross-process serialization in Ray
        serialized = value.model_dump() if hasattr(value, "model_dump") else value
        self._node_state.setdefault(instance_id, {})["__out__"] = serialized

    async def append_to_list(self, instance_id: str, key: str, value: Any) -> None:
        self._node_state.setdefault(instance_id, {}).setdefault(key, []).append(value)

    # Synchronous shims — used only by test_e2e.py assertions after engine.run()
    def node_state(self, instance_id: str) -> dict:
        return self._node_state.setdefault(instance_id, {})

    def get_var_sync(self, name: str) -> Any:
        return self._variables.get(name)
