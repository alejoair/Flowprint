import React, { useState } from "react";
import htm from "htm";

const html = htm.bind(React.createElement);

const TYPES = ["str", "int", "float", "bool", "list", "dict", "Any"];

function PinList({ title, pins, onChange }) {
  function update(i, field, value) {
    onChange(pins.map((p, j) => j === i ? { ...p, [field]: value } : p));
  }
  function add()      { onChange([...pins, { name: "", type: "str" }]); }
  function remove(i)  { onChange(pins.filter((_, j) => j !== i)); }

  return html`
    <div className="sig-col">
      <div className="sig-col-header">${title}</div>
      <div className="sig-rows">
        ${pins.map((p, i) => html`
          <div key=${i} className="sig-row">
            <input className="config-input" value=${p.name} placeholder="name"
              onInput=${e => update(i, "name", e.target.value)} />
            <select className="config-input sig-type" value=${p.type}
              onChange=${e => update(i, "type", e.target.value)}>
              ${TYPES.map(t => html`<option key=${t} value=${t}>${t}</option>`)}
            </select>
            <button className="config-del" onClick=${() => remove(i)}>✕</button>
          </div>`)}
        <button className="btn btn-sm" onClick=${add}>+ Add</button>
      </div>
    </div>`;
}

export function SignatureEditor({ signature, onApply, onClose }) {
  const [inputs,  setInputs]  = useState(
    Object.entries(signature.inputs  ?? {}).map(([name, type]) => ({ name, type }))
  );
  const [outputs, setOutputs] = useState(
    Object.entries(signature.outputs ?? {}).map(([name, type]) => ({ name, type }))
  );

  function handleApply() {
    const toObj = rows =>
      Object.fromEntries(rows.filter(r => r.name.trim()).map(r => [r.name.trim(), r.type]));
    onApply({ inputs: toObj(inputs), outputs: toObj(outputs) });
    onClose();
  }

  return html`
    <div className="modal-backdrop" onClick=${e => e.target === e.currentTarget && onClose()}>
      <div className="modal-panel sig-panel">

        <div className="modal-header">
          <span>Graph Signature</span>
          <button className="config-close" onClick=${onClose}>✕</button>
        </div>

        <div className="sig-body">
          <${PinList} title="Inputs"  pins=${inputs}  onChange=${setInputs}  />
          <div className="sig-divider" />
          <${PinList} title="Outputs" pins=${outputs} onChange=${setOutputs} />
        </div>

        <div className="sig-footer">
          <button className="btn" onClick=${onClose}>Cancel</button>
          <button className="btn btn-primary" onClick=${handleApply}>Apply</button>
        </div>

      </div>
    </div>`;
}
