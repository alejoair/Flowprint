import React, { useState, useCallback, useRef, useEffect } from "react";
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  MiniMap,
} from "reactflow";
import "reactflow/dist/style.css";

import FlowprintNode from "./nodes/FlowprintNode.jsx";
import Sidebar from "./components/Sidebar.jsx";
import Toolbar from "./components/Toolbar.jsx";
import ConfigPanel from "./components/ConfigPanel.jsx";
import ExecutionPanel from "./components/ExecutionPanel.jsx";
import {
  fetchCatalog,
  fetchGraphs,
  fetchGraph,
  saveGraph,
  createGraph,
  deleteGraph,
  validateGraph,
  openRunWS,
} from "./api.js";

const NODE_TYPES = { flowprint: FlowprintNode };

let _idCounter = 1;
function uid() {
  return `node_${_idCounter++}`;
}

function catalogEntryToNodeData(entry) {
  return {
    label: entry.type,
    nodeType: entry.type,
    execInputs: entry.exec_inputs ?? [],
    execOutputs: entry.exec_outputs ?? [],
    dataInputs: entry.data_inputs ?? {},
    dataOutputs: entry.data_outputs ?? {},
    config: {},
    configHint: entry.config_hint ?? "",
  };
}

// Convert ReactFlow nodes/edges back to a Flowprint graph JSON
function toFlowprintGraph(rfNodes, rfEdges, signature) {
  const instances = rfNodes.map((n) => ({
    id: n.id,
    type: n.data.nodeType,
    config: n.data.config ?? {},
  }));

  const connections = rfEdges.map((e) => {
    const isExec = e.data?.kind === "exec";
    return {
      kind: isExec ? "exec" : "data",
      from_node: e.source,
      from_pin: e.sourceHandle,
      to_node: e.target,
      to_pin: e.targetHandle,
    };
  });

  const visual = {};
  rfNodes.forEach((n) => {
    visual[n.id] = { x: n.position.x, y: n.position.y };
  });

  return {
    schema_version: "1.0",
    signature: signature ?? { inputs: {}, outputs: {} },
    variables: [],
    instances,
    connections,
    visual,
  };
}

// Convert saved Flowprint graph JSON to ReactFlow nodes/edges
function fromFlowprintGraph(graph, catalog) {
  const catalogMap = Object.fromEntries(catalog.map((c) => [c.type, c]));

  const rfNodes = (graph.instances ?? []).map((inst) => {
    const entry = catalogMap[inst.type];
    const data = entry
      ? { ...catalogEntryToNodeData(entry), config: inst.config ?? {} }
      : {
          label: inst.type,
          nodeType: inst.type,
          execInputs: [],
          execOutputs: [],
          dataInputs: {},
          dataOutputs: {},
          config: inst.config ?? {},
        };

    // Override Start/End pins from signature
    if (inst.type === "Start" && graph.signature?.inputs) {
      data.dataOutputs = Object.fromEntries(
        Object.entries(graph.signature.inputs).map(([k, v]) => [k, v])
      );
    }
    if (inst.type === "End" && graph.signature?.outputs) {
      data.dataInputs = Object.fromEntries(
        Object.entries(graph.signature.outputs).map(([k, v]) => [k, v])
      );
    }

    const pos = graph.visual?.[inst.id] ?? { x: 100, y: 100 };
    return { id: inst.id, type: "flowprint", position: pos, data };
  });

  const rfEdges = (graph.connections ?? []).map((c, i) => ({
    id: `e${i}`,
    source: c.from_node,
    sourceHandle: c.from_pin,
    target: c.to_node,
    targetHandle: c.to_pin,
    data: { kind: c.kind },
    style: c.kind === "exec"
      ? { stroke: "#b0b0bc", strokeWidth: 2 }
      : { stroke: "#5ba4cf", strokeWidth: 1.5 },
    animated: c.kind === "exec",
  }));

  return { rfNodes, rfEdges };
}

const BLANK_GRAPH = {
  schema_version: "1.0",
  signature: { inputs: {}, outputs: {} },
  variables: [],
  instances: [
    { id: "start", type: "Start", config: {} },
    { id: "end", type: "End", config: {} },
  ],
  connections: [
    { kind: "exec", from_node: "start", from_pin: "out", to_node: "end", to_pin: "in" },
  ],
  visual: { start: { x: 80, y: 200 }, end: { x: 400, y: 200 } },
};

export default function App() {
  const [catalog, setCatalog] = useState([]);
  const [graphs, setGraphs] = useState([]);
  const [graphName, setGraphName] = useState(null);
  const [signature, setSignature] = useState({ inputs: {}, outputs: {} });
  const [dirty, setDirty] = useState(false);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const [selectedNode, setSelectedNode] = useState(null);
  const [showExec, setShowExec] = useState(false);
  const [execEvents, setExecEvents] = useState([]);
  const [running, setRunning] = useState(false);
  const wsRef = useRef(null);

  const reactFlowWrapper = useRef(null);
  const [rfInstance, setRfInstance] = useState(null);

  // Load catalog and graph list on mount
  useEffect(() => {
    fetchCatalog()
      .then((data) => setCatalog(Array.isArray(data) ? data : data.nodes ?? []))
      .catch(console.error);
    refreshGraphList();
  }, []);

  // Load blank graph once catalog is ready
  useEffect(() => {
    if (catalog.length > 0 && nodes.length === 0) {
      loadGraph(BLANK_GRAPH, null);
    }
  }, [catalog]);

  function refreshGraphList() {
    fetchGraphs()
      .then((data) => setGraphs(Array.isArray(data) ? data : []))
      .catch(console.error);
  }

  function loadGraph(graph, name) {
    const { rfNodes, rfEdges } = fromFlowprintGraph(graph, catalog);
    setNodes(rfNodes);
    setEdges(rfEdges);
    setSignature(graph.signature ?? { inputs: {}, outputs: {} });
    setGraphName(name);
    setDirty(false);
    setSelectedNode(null);
  }

  // Toolbar actions
  function handleNew() {
    loadGraph(BLANK_GRAPH, null);
    setDirty(false);
  }

  async function handleOpen(name) {
    try {
      const graph = await fetchGraph(name);
      loadGraph(graph, name);
    } catch (e) {
      alert(`Could not load graph: ${e.message}`);
    }
  }

  async function handleSave() {
    let name = graphName;
    if (!name) {
      name = prompt("Graph name (used as filename):");
      if (!name) return;
    }
    const graph = toFlowprintGraph(nodes, edges, signature);
    try {
      if (graphName) {
        await saveGraph(name, graph);
      } else {
        await createGraph(name, graph);
      }
      setGraphName(name);
      setDirty(false);
      refreshGraphList();
    } catch (e) {
      alert(`Save failed: ${e.message}`);
    }
  }

  async function handleDelete() {
    if (!graphName) return;
    if (!confirm(`Delete "${graphName}"?`)) return;
    try {
      await deleteGraph(graphName);
      refreshGraphList();
      handleNew();
    } catch (e) {
      alert(`Delete failed: ${e.message}`);
    }
  }

  // Run
  function handleRun() {
    const graph = toFlowprintGraph(nodes, edges, signature);
    setExecEvents([]);
    setShowExec(true);
    setRunning(true);
    wsRef.current = openRunWS(
      graph,
      {},
      (ev) => setExecEvents((prev) => [...prev, ev]),
      () => setRunning(false)
    );
  }

  function handleStop() {
    wsRef.current?.close();
    setRunning(false);
  }

  // ReactFlow callbacks
  const onConnect = useCallback(
    (params) => {
      // Determine kind: exec handle ids are "in" or "out", data pins are everything else
      const isExec = ["in", "out"].includes(params.sourceHandle) &&
                     ["in", "out"].includes(params.targetHandle);
      const edge = {
        ...params,
        data: { kind: isExec ? "exec" : "data" },
        style: isExec
          ? { stroke: "#b0b0bc", strokeWidth: 2 }
          : { stroke: "#5ba4cf", strokeWidth: 1.5 },
        animated: isExec,
      };
      setEdges((eds) => addEdge(edge, eds));
      setDirty(true);
    },
    [setEdges]
  );

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      const nodeType = e.dataTransfer.getData("application/flowprint-node");
      if (!nodeType) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = rfInstance.screenToFlowPosition({
        x: e.clientX - bounds.left,
        y: e.clientY - bounds.top,
      });

      const entry = catalog.find((c) => c.type === nodeType);
      if (!entry) return;

      const id = uid();
      const newNode = {
        id,
        type: "flowprint",
        position,
        data: catalogEntryToNodeData(entry),
      };
      setNodes((nds) => [...nds, newNode]);
      setDirty(true);
    },
    [rfInstance, catalog, setNodes]
  );

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  function onNodeClick(_, node) {
    setSelectedNode(node);
  }

  function onPaneClick() {
    setSelectedNode(null);
  }

  function handleConfigChange(nodeId, newConfig) {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, config: newConfig } } : n
      )
    );
    setSelectedNode((prev) =>
      prev?.id === nodeId
        ? { ...prev, data: { ...prev.data, config: newConfig } }
        : prev
    );
    setDirty(true);
  }

  return (
    <div className="app">
      <Toolbar
        graphName={graphName}
        graphs={graphs}
        onNew={handleNew}
        onOpen={handleOpen}
        onSave={handleSave}
        onDelete={handleDelete}
        onRun={handleRun}
        onStop={handleStop}
        running={running}
        dirty={dirty}
      />

      <div className="canvas-wrap">
        <Sidebar catalog={catalog} />

        <div className="flow-wrap" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={NODE_TYPES}
            onNodesChange={(changes) => {
              onNodesChange(changes);
              if (changes.some((c) => c.type !== "select")) setDirty(true);
            }}
            onEdgesChange={(changes) => {
              onEdgesChange(changes);
              if (changes.some((c) => c.type !== "select")) setDirty(true);
            }}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onInit={setRfInstance}
            fitView
            deleteKeyCode="Delete"
          >
            <Controls />
            <MiniMap
              nodeColor="#313244"
              maskColor="rgba(0,0,0,0.4)"
              style={{ background: "#181825" }}
            />
            <Background
              variant={BackgroundVariant.Dots}
              color="#45475a"
              gap={20}
              size={1}
            />
          </ReactFlow>
        </div>

        {selectedNode && (
          <ConfigPanel
            node={selectedNode}
            onChange={handleConfigChange}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>

      {showExec && (
        <ExecutionPanel
          events={execEvents}
          onClose={() => setShowExec(false)}
        />
      )}
    </div>
  );
}
