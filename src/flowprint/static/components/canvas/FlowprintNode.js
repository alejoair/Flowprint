import React from "react";
import htm from "htm";
import { NodeHandle } from "./NodeHandle.js";

const html = htm.bind(React.createElement);

const HEADER_H = 32;
const PIN_H    = 22;

export function FlowprintNode({ data }) {
  const {
    label        = "?",
    execInputs   = [],
    execOutputs  = [],
    dataInputs   = {},
    dataOutputs  = {},
  } = data;

  const left  = [
    ...execInputs.map(id => ({ id, kind: "exec" })),
    ...Object.entries(dataInputs).map(([id, typeName]) => ({ id, kind: "data", typeName })),
  ];
  const right = [
    ...execOutputs.map(id => ({ id, kind: "exec" })),
    ...Object.entries(dataOutputs).map(([id, typeName]) => ({ id, kind: "data", typeName })),
  ];

  const totalH = HEADER_H + Math.max(left.length, right.length) * PIN_H + 8;
  const pinTop = i => HEADER_H + i * PIN_H + PIN_H / 2 - 5;

  return html`
    <div style=${{
      background: "#1e1e2e", border: "1px solid #45475a", borderRadius: 6,
      minWidth: 160, height: totalH, position: "relative",
      boxShadow: "0 2px 8px rgba(0,0,0,.4)",
    }}>
      <div style=${{
        height: HEADER_H, background: "#313244", borderRadius: "5px 5px 0 0",
        display: "flex", alignItems: "center", padding: "0 10px",
        fontSize: 12, fontWeight: 600, color: "#cdd6f4",
        borderBottom: "1px solid #45475a",
        overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis",
      }}>${label}</div>

      ${left.map((p, i) => html`
        <${NodeHandle} key=${"l"+p.id} side="left"
          id=${p.id} kind=${p.kind} typeName=${p.typeName} top=${pinTop(i)} />`)}

      ${right.map((p, i) => html`
        <${NodeHandle} key=${"r"+p.id} side="right"
          id=${p.id} kind=${p.kind} typeName=${p.typeName} top=${pinTop(i)} />`)}
    </div>`;
}
