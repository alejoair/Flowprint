import React, { useState, useMemo } from "react";
import htm from "htm";

const html = htm.bind(React.createElement);

export function Sidebar({ catalog }) {
  const [q, setQ] = useState("");

  const groups = useMemo(() => {
    const out = {};
    for (const n of catalog) {
      if (!n.type.toLowerCase().includes(q.toLowerCase()) &&
          !(n.description ?? "").toLowerCase().includes(q.toLowerCase())) continue;
      const g = n.is_pure ? "Pure" : "Effect";
      (out[g] ??= []).push(n);
    }
    return out;
  }, [catalog, q]);

  return html`
    <aside className="sidebar">
      <div className="sidebar-header">Nodes</div>
      <input className="sidebar-search" placeholder="Search…" value=${q}
        onInput=${e => setQ(e.target.value)} />
      <div className="sidebar-list">
        ${Object.entries(groups).map(([g, nodes]) => html`
          <div key=${g}>
            <div className="sidebar-group">${g}</div>
            ${nodes.map(n => html`
              <div key=${n.type} className="sidebar-item" draggable=${true}
                onDragStart=${e => {
                  e.dataTransfer.setData("application/flowprint-node", n.type);
                  e.dataTransfer.effectAllowed = "move";
                }}
                title=${n.description}>
                <span className="sidebar-item-name">${n.type}</span>
                ${n.description && html`
                  <span className="sidebar-item-desc">${n.description}</span>`}
              </div>`)}
          </div>`)}
        ${Object.keys(groups).length === 0 && html`
          <div className="sidebar-empty">No nodes match.</div>`}
      </div>
    </aside>`;
}
