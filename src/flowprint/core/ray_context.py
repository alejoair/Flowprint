from __future__ import annotations

import copy
from typing import Any

import ray


@ray.remote
class _ContextActor:
    """Ray Actor holding the authoritative mutable context state.

    All methods are synchronous from the actor's perspective; Ray serialises
    concurrent calls automatically (single-threaded actor model).
    """

    def __init__(self) -> None:
        self._variables: dict[str, Any] = {}
        self._node_state: dict[str, dict] = {}
        self._event_queue: list[dict] = []

    def get_var(self, name: str) -> Any:
        return self._variables.get(name)

    def set_var(self, name: str, value: Any) -> None:
        self._variables[name] = value

    def get_node_state(self, instance_id: str) -> dict:
        return copy.deepcopy(self._node_state.get(instance_id, {}))

    def update_node_state(self, instance_id: str, patch: dict) -> None:
        self._node_state.setdefault(instance_id, {}).update(patch)

    def get_node_output(self, instance_id: str) -> Any:
        return self._node_state.get(instance_id, {}).get("__out__")

    def set_node_output(self, instance_id: str, value: Any) -> None:
        serialized = value.model_dump() if hasattr(value, "model_dump") else value
        self._node_state.setdefault(instance_id, {})["__out__"] = serialized

    def append_to_list(self, instance_id: str, key: str, value: Any) -> None:
        self._node_state.setdefault(instance_id, {}).setdefault(key, []).append(value)

    def push_event(self, event: dict) -> None:
        self._event_queue.append(event)

    def drain_events(self) -> list[dict]:
        events, self._event_queue = self._event_queue, []
        return events

    def set_cancelled(self) -> None:
        self._variables["__cancelled__"] = True

    def is_cancelled(self) -> bool:
        return bool(self._variables.get("__cancelled__"))


class RayContextProxy:
    """Wraps a _ContextActor handle with the ContextProtocol async interface."""

    def __init__(self, actor: ray.actor.ActorHandle) -> None:
        self._actor = actor

    async def get_var(self, name: str) -> Any:
        return await self._actor.get_var.remote(name)

    async def set_var(self, name: str, value: Any) -> None:
        await self._actor.set_var.remote(name, value)

    async def get_node_state(self, instance_id: str) -> dict:
        return await self._actor.get_node_state.remote(instance_id)

    async def update_node_state(self, instance_id: str, patch: dict) -> None:
        await self._actor.update_node_state.remote(instance_id, patch)

    async def get_node_output(self, instance_id: str) -> Any:
        return await self._actor.get_node_output.remote(instance_id)

    async def set_node_output(self, instance_id: str, value: Any) -> None:
        await self._actor.set_node_output.remote(instance_id, value)

    async def append_to_list(self, instance_id: str, key: str, value: Any) -> None:
        await self._actor.append_to_list.remote(instance_id, key, value)

    async def push_event(self, event: dict) -> None:
        await self._actor.push_event.remote(event)

    async def drain_events(self) -> list[dict]:
        return await self._actor.drain_events.remote()

    async def is_cancelled(self) -> bool:
        return await self._actor.is_cancelled.remote()

    async def cancel(self) -> None:
        await self._actor.set_cancelled.remote()
