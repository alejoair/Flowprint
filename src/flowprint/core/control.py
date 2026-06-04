from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Goto:
    pins: list[str]


@dataclass
class Repeat:
    pins: list[str]


@dataclass
class Stop:
    pass


@dataclass
class Fork:
    pins: list[str]


Control = Goto | Repeat | Stop | Fork
