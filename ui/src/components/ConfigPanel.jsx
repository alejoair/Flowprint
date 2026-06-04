import React, { useState, useEffect } from "react";

export default function ConfigPanel({ node, onChange, onClose }) {
  const [config, setConfig] = useState({});

  useEffect(() => {
    setConfig(node?.data?.config ?? {});
  }, [node?.id]);

  if (!node) return null;

  const { label, configHint } = node.data;

  function setKey(k, v) {
    const next = { ...config, [k]: v };
    setConfig(next);
    onChange(node.id, next);
  }

  function addKey() {
    const k = prompt("Config key name:");
    if (k && !(k in config)) setKey(k, "");
  }

  function removeKey(k) {
    const next = { ...config };
    delete next[k];
    setConfig(next);
    onChange(node.id, next);
  }

  return (
    <aside className="config-panel">
      <div className="config-header">
        <span>{label}</span>
        <button className="config-close" onClick={onClose}>✕</button>
      </div>

      {configHint && (
        <div className="config-hint">{configHint}</div>
      )}

      <div className="config-body">
        {Object.entries(config).map(([k, v]) => (
          <div key={k} className="config-row">
            <span className="config-key">{k}</span>
            <input
              className="config-input"
              value={typeof v === "object" ? JSON.stringify(v) : String(v)}
              onChange={(e) => {
                let val = e.target.value;
                try { val = JSON.parse(val); } catch { /* keep as string */ }
                setKey(k, val);
              }}
            />
            <button className="config-del" onClick={() => removeKey(k)}>✕</button>
          </div>
        ))}

        <button className="btn btn-sm" onClick={addKey}>+ Add key</button>
      </div>
    </aside>
  );
}
