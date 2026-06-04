from __future__ import annotations

from flowprint.core.node import Node
from flowprint.nodes.agents.echo import AgentEcho
from flowprint.nodes.control.branch import Branch
from flowprint.nodes.control.end import End
from flowprint.nodes.control.flipflop import FlipFlop
from flowprint.nodes.control.foreach import ForEach
from flowprint.nodes.control.sequence import Sequence
from flowprint.nodes.control.start import Start
from flowprint.nodes.data.concat import Concat
from flowprint.nodes.data.const import Const
from flowprint.nodes.data.equals import Equals
from flowprint.nodes.data.itemof import ItemOf
from flowprint.nodes.variables.getvar import GetVar
from flowprint.nodes.variables.setvar import SetVar

NODE_REGISTRY: dict[str, type[Node]] = {
    "Start": Start,
    "End": End,
    "Sequence": Sequence,
    "ForEach": ForEach,
    "Branch": Branch,
    "FlipFlop": FlipFlop,
    "Const": Const,
    "Concat": Concat,
    "ItemOf": ItemOf,
    "Equals": Equals,
    "GetVar": GetVar,
    "SetVar": SetVar,
    "AgentEcho": AgentEcho,
}
