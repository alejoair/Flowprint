import React, { useState, useCallback, useRef, useEffect } from "react";
import { createRoot } from "react-dom/client";
import ReactFlow, {
  addEdge, useNodesState, useEdgesState,
  Controls, Background, BackgroundVariant, MiniMap,
} from "reactflow";
import htm from "htm";

import { fetchCatalog, fetchGraphs, fetchGraph, saveGraph, createGraph, deleteGraph, openRunWS } from "/ui/api.js";
import { FlowprintNode, Sidebar, Toolbar, ConfigPanel, ExecutionPanel } from "/ui/components.js";

const html = htm.bind(React.createElement);

/* ── Node types (must be module-scope) ───────────── */
const NODE_TYPES = { flowprint: FlowprintNode };

/* ── Helpers ─────────────────────────────────────── */
let _id = 1;
const uid = () => `node_${_id++}`;

function entryToData(e) {
  return {
    label: e.type, nodeType: e.type,
    execInputs:  e.exec_inputs  ?? [],
    execOutputs: e.exec_outputs ?? [],
    dataInputs:  e.data_inputs  ?? {},
    dataOutputs: e.data_outputs ?? {},
    config: {}, configHint: e.config_hint ?? "",
  };
}

function toGraph(rfNodes, rfEdges, sig) {
  const visual = {};
  rfNodes.forEach(n => { visual[n.id] = n.position; });
  return {
    schema_version: "1.0",
    signature: sig ?? { inputs:{}, outputs:{} },
    variables: [],
    instances:   rfNodes.map(n => ({ id:n.id, type:n.data.nodeType, config:n.data.config??{} })),
    connections: rfEdges.map(e => ({
      kind: e.data?.kind ?? "data",
      from_node: e.source, from_pin: e.sourceHandle,
      to_node:   e.target, to_pin:   e.targetHandle,
    })),
    visual,
  };
}

function fromGraph(graph, catalog) {
  const map = Object.fromEntries(catalog.map(c => [c.type, c]));
  const rfNodes = (graph.instances ?? []).map(inst => {
    const entry = map[inst.type];
    const data  = entry ? { ...entryToData(entry), config: inst.config??{} } : {
      label: inst.type, nodeType: inst.type,
      execInputs:[], execOutputs:[], dataInputs:{}, dataOutputs:{},
      config: inst.config??{}, configHint:"",
    };
    if (inst.type === "Start" && graph.signature?.inputs)
      data.dataOutputs = { ...graph.signature.inputs };
    if (inst.type === "End"   && graph.signature?.outputs)
      data.dataInputs  = { ...graph.signature.outputs };
    return { id: inst.id, type:"flowprint", position: graph.visual?.[inst.id] ?? {x:100,y:100}, data };
  });
  const rfEdges = (graph.connections ?? []).map((c, i) => ({
    id: `e${i}`, source:c.from_node, sourceHandle:c.from_pin,
    target:c.to_node, targetHandle:c.to_pin,
    data: { kind: c.kind },
    style: c.kind==="exec" ? {stroke:"#b0b0bc",strokeWidth:2} : {stroke:"#5ba4cf",strokeWidth:1.5},
    animated: c.kind === "exec",
  }));
  return { rfNodes, rfEdges };
}

const BLANK = {
  schema_version:"1.0", signature:{inputs:{},outputs:{}}, variables:[],
  instances:[
    {id:"start",type:"Start",config:{}},
    {id:"end",  type:"End",  config:{}},
  ],
  connections:[{kind:"exec",from_node:"start",from_pin:"out",to_node:"end",to_pin:"in"}],
  visual:{start:{x:80,y:200},end:{x:400,y:200}},
};

/* ── App ─────────────────────────────────────────── */

function App() {
  const [catalog, setCatalog] = useState([]);
  const [graphs,  setGraphs ] = useState([]);
  const [gName,   setGName  ] = useState(null);
  const [sig,     setSig    ] = useState({inputs:{},outputs:{}});
  const [dirty,   setDirty  ] = useState(false);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const [selNode,   setSelNode  ] = useState(null);
  const [showExec,  setShowExec ] = useState(false);
  const [execEvts,  setExecEvts ] = useState([]);
  const [running,   setRunning  ] = useState(false);
  const wsRef   = useRef(null);
  const wrapRef = useRef(null);
  const [rfi,   setRfi] = useState(null);

  useEffect(() => {
    fetchCatalog().then(d => setCatalog(Array.isArray(d) ? d : d.nodes ?? [])).catch(console.error);
    refreshList();
  }, []);

  useEffect(() => {
    if (catalog.length > 0 && nodes.length === 0) loadGraph(BLANK, null);
  }, [catalog]);

  function refreshList() {
    fetchGraphs().then(d => setGraphs(Array.isArray(d) ? d : [])).catch(console.error);
  }

  function loadGraph(graph, name) {
    const { rfNodes, rfEdges } = fromGraph(graph, catalog);
    setNodes(rfNodes); setEdges(rfEdges);
    setSig(graph.signature ?? {inputs:{},outputs:{}});
    setGName(name); setDirty(false); setSelNode(null);
  }

  function handleNew() { loadGraph(BLANK, null); setDirty(false); }

  async function handleOpen(name) {
    try { loadGraph(await fetchGraph(name), name); }
    catch (e) { alert("Could not load: " + e.message); }
  }

  async function handleSave() {
    let name = gName ?? prompt("Graph name:");
    if (!name) return;
    const g = toGraph(nodes, edges, sig);
    try {
      gName ? await saveGraph(name, g) : await createGraph(name, g);
      setGName(name); setDirty(false); refreshList();
    } catch (e) { alert("Save failed: " + e.message); }
  }

  async function handleDelete() {
    if (!gName || !confirm(`Delete "${gName}"?`)) return;
    try { await deleteGraph(gName); refreshList(); handleNew(); }
    catch (e) { alert("Delete failed: " + e.message); }
  }

  function handleRun() {
    setExecEvts([]); setShowExec(true); setRunning(true);
    wsRef.current = openRunWS(
      toGraph(nodes, edges, sig), {},
      ev => setExecEvts(p => [...p, ev]),
      () => setRunning(false),
    );
  }
  function handleStop() { wsRef.current?.close(); setRunning(false); }

  const onConnect = useCallback(params => {
    const isExec = ["in","out"].includes(params.sourceHandle) && ["in","out"].includes(params.targetHandle);
    setEdges(eds => addEdge({
      ...params, data:{kind: isExec?"exec":"data"},
      style: isExec?{stroke:"#b0b0bc",strokeWidth:2}:{stroke:"#5ba4cf",strokeWidth:1.5},
      animated: isExec,
    }, eds));
    setDirty(true);
  }, [setEdges]);

  const onDrop = useCallback(e => {
    e.preventDefault();
    const type = e.dataTransfer.getData("application/flowprint-node");
    if (!type || !rfi) return;
    const bounds = wrapRef.current.getBoundingClientRect();
    const position = rfi.project({ x: e.clientX - bounds.left, y: e.clientY - bounds.top });
    const entry = catalog.find(c => c.type === type);
    if (!entry) return;
    setNodes(nds => [...nds, { id:uid(), type:"flowprint", position, data:entryToData(entry) }]);
    setDirty(true);
  }, [rfi, catalog, setNodes]);

  const onDragOver = useCallback(e => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; }, []);

  function onNodeClick(_, node) { setSelNode(node); }
  function onPaneClick()        { setSelNode(null); }

  function onCfgChange(nodeId, newCfg) {
    setNodes(nds => nds.map(n => n.id===nodeId ? {...n, data:{...n.data,config:newCfg}} : n));
    setSelNode(prev => prev?.id===nodeId ? {...prev,data:{...prev.data,config:newCfg}} : prev);
    setDirty(true);
  }

  return html`
    <div className="app">
      <${Toolbar}
        graphName=${gName} graphs=${graphs}
        onNew=${handleNew} onOpen=${handleOpen}
        onSave=${handleSave} onDelete=${handleDelete}
        onRun=${handleRun} onStop=${handleStop}
        running=${running} dirty=${dirty}
      />
      <div className="canvas-wrap">
        <${Sidebar} catalog=${catalog} />
        <div className="flow-wrap" ref=${wrapRef}>
          <${ReactFlow}
            nodes=${nodes} edges=${edges}
            nodeTypes=${NODE_TYPES}
            onNodesChange=${changes => { onNodesChange(changes); if (changes.some(c=>c.type!=="select")) setDirty(true); }}
            onEdgesChange=${changes => { onEdgesChange(changes); if (changes.some(c=>c.type!=="select")) setDirty(true); }}
            onConnect=${onConnect}
            onDrop=${onDrop} onDragOver=${onDragOver}
            onNodeClick=${onNodeClick} onPaneClick=${onPaneClick}
            onInit=${setRfi}
            fitView=${true}
            deleteKeyCode="Delete"
          >
            <${Controls} />
            <${MiniMap} nodeColor="#313244" maskColor="rgba(0,0,0,.4)"
              style=${{background:"#181825"}} />
            <${Background} variant=${BackgroundVariant.Dots}
              color="#45475a" gap=${20} size=${1} />
          </${ReactFlow}>
        </div>
        ${selNode && html`<${ConfigPanel} node=${selNode} onChange=${onCfgChange} onClose=${() => setSelNode(null)} />`}
      </div>
      ${showExec && html`<${ExecutionPanel} events=${execEvts} onClose=${() => setShowExec(false)} />`}
    </div>`;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
