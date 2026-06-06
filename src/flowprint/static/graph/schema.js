export function entryToData(entry) {
  return {
    label:       entry.type,
    nodeType:    entry.type,
    execInputs:  entry.exec_inputs  ?? [],
    execOutputs: entry.exec_outputs ?? [],
    dataInputs:  entry.data_inputs  ?? {},
    dataOutputs: entry.data_outputs ?? {},
    config:      {},
    configHint:  entry.config_hint  ?? "",
  };
}

export function toFlowprintGraph(rfNodes, rfEdges, signature) {
  const visual = {};
  rfNodes.forEach(n => { visual[n.id] = n.position; });
  return {
    schema_version: "1.0",
    signature: signature ?? { inputs: {}, outputs: {} },
    variables: [],
    instances: rfNodes.map(n => ({
      id:     n.id,
      type:   n.data.nodeType,
      config: n.data.config ?? {},
    })),
    connections: rfEdges.map(e => ({
      kind:      e.data?.kind ?? "data",
      from_node: e.source,      from_pin: e.sourceHandle,
      to_node:   e.target,      to_pin:   e.targetHandle,
    })),
    visual,
  };
}

export function fromFlowprintGraph(graph, catalog) {
  const byType = Object.fromEntries(catalog.map(c => [c.type, c]));

  const rfNodes = (graph.instances ?? []).map(inst => {
    const entry = byType[inst.type];
    const data  = entry
      ? { ...entryToData(entry), config: inst.config ?? {} }
      : { label: inst.type, nodeType: inst.type, execInputs: [], execOutputs: [],
          dataInputs: {}, dataOutputs: {}, config: inst.config ?? {}, configHint: "" };

    if (inst.type === "Start" && graph.signature?.inputs)
      data.dataOutputs = { ...graph.signature.inputs };
    if (inst.type === "End"   && graph.signature?.outputs)
      data.dataInputs  = { ...graph.signature.outputs };

    return {
      id:       inst.id,
      type:     "flowprint",
      position: graph.visual?.[inst.id] ?? { x: 100, y: 100 },
      data,
    };
  });

  const rfEdges = (graph.connections ?? []).map((c, i) => ({
    id:           `e${i}`,
    source:       c.from_node, sourceHandle: c.from_pin,
    target:       c.to_node,   targetHandle: c.to_pin,
    data:         { kind: c.kind },
    style:        c.kind === "exec"
                    ? { stroke: "#b0b0bc", strokeWidth: 2 }
                    : { stroke: "#5ba4cf", strokeWidth: 1.5 },
    animated:     c.kind === "exec",
  }));

  return { rfNodes, rfEdges };
}
