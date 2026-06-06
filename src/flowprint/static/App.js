import React, { useState, useCallback, useRef, useEffect } from "react";
import ReactFlow, {
  addEdge, useNodesState, useEdgesState,
  Controls, Background, BackgroundVariant, MiniMap,
} from "reactflow";
import htm from "htm";

import { useStore }            from "./store/context.js";
import { A }                   from "./store/actions.js";
import { useCatalog }          from "./hooks/useCatalog.js";
import { useGraphPersistence } from "./hooks/useGraphPersistence.js";
import { useExecution }        from "./hooks/useExecution.js";

import { fromFlowprintGraph, toFlowprintGraph, entryToData } from "./graph/schema.js";
import { BLANK_GRAPH }         from "./graph/blank.js";

import { FlowprintNode }  from "./components/canvas/FlowprintNode.js";
import { Sidebar }        from "./components/panels/Sidebar.js";
import { ConfigPanel }    from "./components/panels/ConfigPanel.js";
import { ExecutionPanel } from "./components/panels/ExecutionPanel.js";
import { Toolbar }        from "./components/toolbar/Toolbar.js";
import { KeybindHandler } from "./components/shared/KeybindHandler.js";

const html = htm.bind(React.createElement);

// Must be module-scope so React Flow doesn't remount on every render
const NODE_TYPES = { flowprint: FlowprintNode };

let _idCounter = 1;
const uid = () => `node_${_idCounter++}`;

export default function App() {
  const { state, dispatch } = useStore();
  const catalog     = useCatalog();
  const persistence = useGraphPersistence();
  const execution   = useExecution();

  // React Flow owns node/edge state; our store tracks semantic state
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [rfi,   setRfi] = useState(null);
  const wrapRef = useRef(null);

  // Load graph list on mount
  useEffect(() => { persistence.loadList(); }, []);

  // Load blank graph once catalog arrives
  useEffect(() => {
    if (catalog.length > 0 && nodes.length === 0) loadIntoCanvas(BLANK_GRAPH, null);
  }, [catalog.length]);

  // ── Canvas helpers ────────────────────────────────

  function loadIntoCanvas(graph, name) {
    const { rfNodes, rfEdges } = fromFlowprintGraph(graph, catalog);
    setNodes(rfNodes);
    setEdges(rfEdges);
    dispatch({ type: A.GRAPH_LOADED, payload: { name, graph } });
  }

  // ── Toolbar handlers ──────────────────────────────

  function handleNew() {
    loadIntoCanvas(BLANK_GRAPH, null);
  }

  async function handleOpen(name) {
    try {
      const graph = await persistence.load(name); // also dispatches GRAPH_LOADED
      const { rfNodes, rfEdges } = fromFlowprintGraph(graph, catalog);
      setNodes(rfNodes);
      setEdges(rfEdges);
    } catch (e) { alert("Could not load: " + e.message); }
  }

  async function handleSave() {
    const name = state.graphName ?? prompt("Graph name:");
    if (!name) return;
    const graph = toFlowprintGraph(nodes, edges, state.signature);
    try { await persistence.save(name, graph); }
    catch (e) { alert("Save failed: " + e.message); }
  }

  async function handleDelete() {
    if (!state.graphName || !confirm(`Delete "${state.graphName}"?`)) return;
    try { await persistence.remove(state.graphName); handleNew(); }
    catch (e) { alert("Delete failed: " + e.message); }
  }

  function handleRun() {
    execution.run(toFlowprintGraph(nodes, edges, state.signature), {});
  }

  // ── React Flow callbacks ──────────────────────────

  const onConnect = useCallback(params => {
    const isExec = ["in", "out"].includes(params.sourceHandle) &&
                   ["in", "out"].includes(params.targetHandle);
    setEdges(eds => addEdge({
      ...params,
      data:     { kind: isExec ? "exec" : "data" },
      style:    isExec ? { stroke: "#b0b0bc", strokeWidth: 2 }
                       : { stroke: "#5ba4cf", strokeWidth: 1.5 },
      animated: isExec,
    }, eds));
    dispatch({ type: A.MARK_DIRTY });
  }, [setEdges, dispatch]);

  const onDrop = useCallback(e => {
    e.preventDefault();
    const type = e.dataTransfer.getData("application/flowprint-node");
    if (!type || !rfi) return;
    const bounds   = wrapRef.current.getBoundingClientRect();
    const position = rfi.project({ x: e.clientX - bounds.left, y: e.clientY - bounds.top });
    const entry    = catalog.find(c => c.type === type);
    if (!entry) return;
    setNodes(nds => [...nds, { id: uid(), type: "flowprint", position, data: entryToData(entry) }]);
    dispatch({ type: A.MARK_DIRTY });
  }, [rfi, catalog, setNodes, dispatch]);

  const onDragOver = useCallback(e => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  // Derive selected node from RF state on each render (O(n) but graph is small)
  const selectedNode = nodes.find(n => n.id === state.selectedNodeId) ?? null;

  function onNodeClick(_, node) { dispatch({ type: A.NODE_SELECTED,   payload: node.id }); }
  function onPaneClick()        { dispatch({ type: A.NODE_DESELECTED }); }

  function onCfgChange(nodeId, newCfg) {
    setNodes(nds => nds.map(n =>
      n.id === nodeId ? { ...n, data: { ...n.data, config: newCfg } } : n
    ));
    dispatch({ type: A.MARK_DIRTY });
  }

  // ── Render ────────────────────────────────────────

  return html`
    <div className="app">
      <${KeybindHandler} onSave=${handleSave} onNew=${handleNew} />

      <${Toolbar}
        graphName=${state.graphName}
        graphs=${state.graphs}
        dirty=${state.dirty}
        running=${state.running}
        onNew=${handleNew}
        onOpen=${handleOpen}
        onSave=${handleSave}
        onDelete=${handleDelete}
        onRun=${handleRun}
        onStop=${execution.cancel}
      />

      <div className="canvas-wrap">
        <${Sidebar} catalog=${catalog} />

        <div className="flow-wrap" ref=${wrapRef}>
          <${ReactFlow}
            nodes=${nodes}
            edges=${edges}
            nodeTypes=${NODE_TYPES}
            onNodesChange=${changes => {
              onNodesChange(changes);
              if (changes.some(c => c.type !== "select")) dispatch({ type: A.MARK_DIRTY });
            }}
            onEdgesChange=${changes => {
              onEdgesChange(changes);
              if (changes.some(c => c.type !== "select")) dispatch({ type: A.MARK_DIRTY });
            }}
            onConnect=${onConnect}
            onDrop=${onDrop}
            onDragOver=${onDragOver}
            onNodeClick=${onNodeClick}
            onPaneClick=${onPaneClick}
            onInit=${setRfi}
            fitView=${true}
            deleteKeyCode="Delete"
          >
            <${Controls} />
            <${MiniMap}
              nodeColor="#313244"
              maskColor="rgba(0,0,0,.4)"
              style=${{ background: "#181825" }}
            />
            <${Background}
              variant=${BackgroundVariant.Dots}
              color="#45475a" gap=${20} size=${1}
            />
          </${ReactFlow}>
        </div>

        ${selectedNode && html`
          <${ConfigPanel}
            node=${selectedNode}
            onChange=${onCfgChange}
            onClose=${() => dispatch({ type: A.NODE_DESELECTED })}
          />`}
      </div>

      ${state.showExecPanel && html`
        <${ExecutionPanel}
          events=${state.execEvents}
          onClose=${() => dispatch({ type: A.EXEC_PANEL_TOGGLE })}
        />`}
    </div>`;
}
