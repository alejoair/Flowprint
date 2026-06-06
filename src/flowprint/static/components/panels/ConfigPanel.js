import React, { useState, useEffect } from "react";
import htm from "htm";

const html = htm.bind(React.createElement);

export function ConfigPanel({ node, onChange, onClose }) {
  const [cfg, setCfg] = useState({});

  useEffect(() => { setCfg(node?.data?.config ?? {}); }, [node?.id]);

  if (!node) return null;
  const { label, configHint } = node.data;

  function set(k, v) {
    const next = { ...cfg, [k]: v };
    setCfg(next);
    onChange(node.id, next);
  }
  function del(k) {
    const next = { ...cfg };
    delete next[k];
    setCfg(next);
    onChange(node.id, next);
  }
  function add() {
    const k = prompt("Config key:");
    if (k && !(k in cfg)) set(k, "");
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
              onInput=${e => {
                let val = e.target.value;
                try { val = JSON.parse(val); } catch {}
                set(k, val);
              }} />
            <button className="config-del" onClick=${() => del(k)}>✕</button>
          </div>`)}
        <button className="btn btn-sm" onClick=${add}>+ Add key</button>
      </div>
    </aside>`;
}
