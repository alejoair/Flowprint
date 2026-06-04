import React, { useState, useEffect, useRef, useMemo } from "react";
import { Handle, Position } from "reactflow";
import htm from "htm";

const html = htm.bind(React.createElement);

/* ── FlowprintNode ────────────────────────────────── */

const HEADER_H = 32;
const PIN_H    = 22;
const TYPE_COLORS = {
  str: "#5ba4cf", int: "#78c17a", float: "#4ec9b0",
  bool: "#e5a663", list: "#a98af7", dict: "#f28b82", Any: "#8c8c9a",
};
const pinColor = t => TYPE_COLORS[t] ?? TYPE_COLORS.Any;

export function FlowprintNode({ data }) {
  const { label, execInputs = [], execOutputs = [], dataInputs = {}, dataOutputs = {} } = data;

  const left  = [...execInputs.map(id => ({ kind:"exec", id })),
                 ...Object.entries(dataInputs).map(([id, t]) => ({ kind:"data", id, t }))];
  const right = [...execOutputs.map(id => ({ kind:"exec", id })),
                 ...Object.entries(dataOutputs).map(([id, t]) => ({ kind:"data", id, t }))];

  const totalH = HEADER_H + Math.max(left.length, right.length) * PIN_H + 8;
  const pinTop = i => HEADER_H + i * PIN_H + PIN_H / 2 - 5;

  function makeHandle(pin, i, side) {
    const isExec = pin.kind === "exec";
    const color  = isExec ? "#b0b0bc" : pinColor(pin.t);
    const isLeft = side === "left";
    return html`
      <div key=${side[0]+pin.id} style=${{
        position:"absolute", top: pinTop(i),
        [isLeft ? "left" : "right"]: -14,
        display:"flex", alignItems:"center", gap:4,
        flexDirection: isLeft ? "row" : "row-reverse",
        pointerEvents:"none",
      }}>
        <${Handle}
          type=${isLeft ? "target" : "source"}
          position=${isLeft ? Position.Left : Position.Right}
          id=${pin.id}
          style=${{
            position:"relative", top:0, left:0, right:0, transform:"none",
            width: isExec?12:10, height: isExec?12:10,
            background:color, border:`2px solid ${color}`,
            borderRadius: isExec ? 2 : "50%",
            pointerEvents:"all",
          }}
        />
        <span style=${{ fontSize:10, color, userSelect:"none" }}>${pin.id}</span>
      </div>`;
  }

  return html`
    <div style=${{
      background:"#1e1e2e", border:"1px solid #45475a", borderRadius:6,
      minWidth:160, height:totalH, position:"relative",
      boxShadow:"0 2px 8px rgba(0,0,0,.4)",
    }}>
      <div style=${{
        height:HEADER_H, background:"#313244", borderRadius:"5px 5px 0 0",
        display:"flex", alignItems:"center", padding:"0 10px",
        fontSize:12, fontWeight:600, color:"#cdd6f4",
        borderBottom:"1px solid #45475a", overflow:"hidden",
        whiteSpace:"nowrap", textOverflow:"ellipsis",
      }}>${label}</div>
      ${left.map((p, i) => makeHandle(p, i, "left"))}
      ${right.map((p, i) => makeHandle(p, i, "right"))}
    </div>`;
}

/* ── Sidebar ──────────────────────────────────────── */

export function Sidebar({ catalog }) {
  const [q, setQ] = useState("");

  const groups = useMemo(() => {
    const out = {};
    for (const n of catalog) {
      if (!n.type.toLowerCase().includes(q.toLowerCase()) &&
          !(n.description||"").toLowerCase().includes(q.toLowerCase())) continue;
      const g = n.is_pure ? "Pure" : "Effect";
      (out[g] ??= []).push(n);
    }
    return out;
  }, [catalog, q]);

  return html`
    <aside className="sidebar">
      <div className="sidebar-header">Nodes</div>
      <input className="sidebar-search" placeholder="Search…"
        value=${q} onInput=${e => setQ(e.target.value)} />
      <div className="sidebar-list">
        ${Object.entries(groups).map(([g, nodes]) => html`
          <div key=${g}>
            <div className="sidebar-group">${g}</div>
            ${nodes.map(n => html`
              <div key=${n.type} className="sidebar-item"
                draggable=${true}
                onDragStart=${e => {
                  e.dataTransfer.setData("application/flowprint-node", n.type);
                  e.dataTransfer.effectAllowed = "move";
                }}
                title=${n.description}>
                <span className="sidebar-item-name">${n.type}</span>
                ${n.description && html`<span className="sidebar-item-desc">${n.description}</span>`}
              </div>`)}
          </div>`)}
        ${Object.keys(groups).length === 0 && html`<div className="sidebar-empty">No nodes match.</div>`}
      </div>
    </aside>`;
}

/* ── Toolbar ──────────────────────────────────────── */

export function Toolbar({ graphName, graphs, onNew, onOpen, onSave, onDelete, onRun, onStop, running, dirty }) {
  const [open, setOpen] = useState(false);
  return html`
    <header className="toolbar">
      <div className="toolbar-brand">Flowprint</div>
      <div className="toolbar-section">
        <button className="btn" onClick=${onNew}>New</button>
        <div className="dropdown-wrap">
          <button className="btn" onClick=${() => setOpen(v => !v)}>Open ${open?"▲":"▼"}</button>
          ${open && html`
            <div className="dropdown">
              ${graphs.length === 0 && html`<div className="dropdown-empty">No saved graphs</div>`}
              ${graphs.map(g => html`
                <div key=${g.name} className="dropdown-item" onClick=${() => { onOpen(g.name); setOpen(false); }}>
                  ${g.name}
                </div>`)}
            </div>`}
        </div>
        <button className="btn btn-primary" onClick=${onSave} disabled=${!dirty}>
          Save${graphName ? ` "${graphName}"` : ""}
        </button>
        ${graphName && html`<button className="btn btn-danger" onClick=${onDelete}>Delete</button>`}
      </div>
      <div className="toolbar-section toolbar-right">
        ${running
          ? html`<button className="btn btn-danger" onClick=${onStop}>Stop</button>`
          : html`<button className="btn btn-run" onClick=${onRun}>▶ Run</button>`}
      </div>
    </header>`;
}

/* ── ConfigPanel ──────────────────────────────────── */

export function ConfigPanel({ node, onChange, onClose }) {
  const [cfg, setCfg] = useState({});
  useEffect(() => { setCfg(node?.data?.config ?? {}); }, [node?.id]);

  if (!node) return null;
  const { label, configHint } = node.data;

  function set(k, v) {
    const next = { ...cfg, [k]: v };
    setCfg(next); onChange(node.id, next);
  }
  function del(k) {
    const next = { ...cfg }; delete next[k];
    setCfg(next); onChange(node.id, next);
  }
  function add() {
    const k = prompt("Config key:"); if (k && !(k in cfg)) set(k, "");
  }

  return html`
    <aside className="config-panel">
      <div className="config-header">
        <span>${label}</span>
        <button className="config-close" onClick=${onClose}>✕</button>
      </div>
      ${configHint && html`<div className="config-hint">${configHint}</div>`}
      <div className="config-body">
        ${Object.entries(cfg).map(([k, v]) => html`
          <div key=${k} className="config-row">
            <span className="config-key">${k}</span>
            <input className="config-input"
              value=${typeof v === "object" ? JSON.stringify(v) : String(v)}
              onInput=${e => { let val = e.target.value; try { val = JSON.parse(val); } catch {} set(k, val); }} />
            <button className="config-del" onClick=${() => del(k)}>✕</button>
          </div>`)}
        <button className="btn btn-sm" onClick=${add}>+ Add key</button>
      </div>
    </aside>`;
}

/* ── ExecutionPanel ───────────────────────────────── */

const EV_COLORS = {
  node_start:"#e5a663", node_complete:"#78c17a",
  error:"#f28b82", graph_complete:"#5ba4cf", cancelled:"#8c8c9a",
};

export function ExecutionPanel({ events, onClose }) {
  const bottom = useRef(null);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior:"smooth" }); }, [events.length]);

  return html`
    <div className="exec-panel">
      <div className="exec-header">
        <span>Execution log</span>
        <button className="config-close" onClick=${onClose}>✕</button>
      </div>
      <div className="exec-body">
        ${events.length === 0 && html`<div className="exec-empty">Press ▶ Run to execute the graph.</div>`}
        ${events.map((ev, i) => {
          const type = ev.event ?? ev.type ?? "unknown";
          const nodeId = ev.node ?? ev.node_id;
          return html`
          <div key=${i} className="exec-event">
            <span style=${{ display:"inline-block", padding:"1px 6px", borderRadius:3, fontSize:10,
              fontWeight:600, background:EV_COLORS[type]??"#45475a", color:"#1e1e2e", marginRight:6 }}>
              ${type}
            </span>
            ${nodeId && html`<span className="exec-node">${nodeId} </span>`}
            ${type === "graph_complete" && ev.result != null &&
              html`<pre className="exec-result">${JSON.stringify(ev.result, null, 2)}</pre>`}
            ${type === "error" && (ev.error ?? ev.message) &&
              html`<span className="exec-error">${ev.error ?? ev.message}</span>`}
          </div>`})}
        <div ref=${bottom} />
      </div>
    </div>`;
}
