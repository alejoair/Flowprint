import React, { useState } from "react";
import htm from "htm";

const html = htm.bind(React.createElement);

export function Toolbar({
  graphName, graphs, dirty, running,
  onNew, onOpen, onSave, onDelete, onRun, onStop, onOpenNodeEditor,
}) {
  const [showOpen, setShowOpen] = useState(false);

  return html`
    <header className="toolbar">
      <div className="toolbar-brand">Flowprint</div>

      <div className="toolbar-section">
        <button className="btn" onClick=${onNew}>New</button>

        <div className="dropdown-wrap">
          <button className="btn" onClick=${() => setShowOpen(v => !v)}>
            Open ${showOpen ? "▲" : "▼"}
          </button>
          ${showOpen && html`
            <div className="dropdown">
              ${graphs.length === 0 && html`
                <div className="dropdown-empty">No saved graphs</div>`}
              ${graphs.map(g => html`
                <div key=${g.name} className="dropdown-item"
                  onClick=${() => { onOpen(g.name); setShowOpen(false); }}>
                  ${g.name}
                </div>`)}
            </div>`}
        </div>

        <button className="btn btn-primary" onClick=${onSave} disabled=${!dirty}>
          Save${graphName ? ` "${graphName}"` : ""}
        </button>

        ${graphName && html`
          <button className="btn btn-danger" onClick=${onDelete}>Delete</button>`}
      </div>

      <div className="toolbar-section toolbar-right">
        <button className="btn" onClick=${onOpenNodeEditor} title="Manage custom nodes">
          ⚙ Nodes
        </button>
        ${running
          ? html`<button className="btn btn-danger" onClick=${onStop}>■ Stop</button>`
          : html`<button className="btn btn-run" onClick=${onRun}>▶ Run</button>`}
      </div>
    </header>`;
}
