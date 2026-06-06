import React from "react";
import { Handle, Position } from "reactflow";
import htm from "htm";

const html = htm.bind(React.createElement);

const TYPE_COLORS = {
  str:   "#5ba4cf",
  int:   "#78c17a",
  float: "#4ec9b0",
  bool:  "#e5a663",
  list:  "#a98af7",
  dict:  "#f28b82",
  Any:   "#8c8c9a",
};

export function NodeHandle({ id, side, kind, typeName, top }) {
  const isLeft = side === "left";
  const isExec = kind === "exec";
  const color  = isExec ? "#b0b0bc" : (TYPE_COLORS[typeName] ?? TYPE_COLORS.Any);

  return html`
    <div style=${{
      position: "absolute", top,
      [isLeft ? "left" : "right"]: -14,
      display: "flex", alignItems: "center", gap: 4,
      flexDirection: isLeft ? "row" : "row-reverse",
      pointerEvents: "none",
    }}>
      <${Handle}
        type=${isLeft ? "target" : "source"}
        position=${isLeft ? Position.Left : Position.Right}
        id=${id}
        style=${{
          position: "relative", top: 0, left: 0, right: 0, transform: "none",
          width: isExec ? 12 : 10, height: isExec ? 12 : 10,
          background: color, border: `2px solid ${color}`,
          borderRadius: isExec ? 2 : "50%",
          pointerEvents: "all",
        }}
      />
      <span style=${{ fontSize: 10, color, userSelect: "none" }}>${id}</span>
    </div>`;
}
