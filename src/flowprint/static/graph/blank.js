export const BLANK_GRAPH = {
  schema_version: "1.0",
  signature: { inputs: {}, outputs: {} },
  variables: [],
  instances: [
    { id: "start", type: "Start", config: {} },
    { id: "end",   type: "End",   config: {} },
  ],
  connections: [
    { kind: "exec", from_node: "start", from_pin: "out", to_node: "end", to_pin: "in" },
  ],
  visual: { start: { x: 80, y: 200 }, end: { x: 400, y: 200 } },
};
