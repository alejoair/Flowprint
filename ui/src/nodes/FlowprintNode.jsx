import React from "react";
import { Handle, Position } from "reactflow";

const HEADER_H = 32;
const PIN_H = 22;

const TYPE_COLORS = {
  str: "#5ba4cf",
  int: "#78c17a",
  float: "#4ec9b0",
  bool: "#e5a663",
  list: "#a98af7",
  dict: "#f28b82",
  Any: "#8c8c9a",
};

function pinColor(typeName) {
  return TYPE_COLORS[typeName] ?? TYPE_COLORS.Any;
}

function ExecHandle({ kind, id, position, top, label }) {
  return (
    <div
      style={{
        position: "absolute",
        top,
        [position === Position.Left ? "left" : "right"]: -14,
        display: "flex",
        alignItems: "center",
        gap: 4,
        flexDirection: position === Position.Left ? "row" : "row-reverse",
        pointerEvents: "none",
      }}
    >
      <Handle
        type={kind}
        position={position}
        id={id}
        style={{
          position: "relative",
          top: 0,
          left: 0,
          right: 0,
          transform: "none",
          width: 12,
          height: 12,
          background: "#b0b0bc",
          border: "2px solid #6c6c7a",
          borderRadius: 2,
          pointerEvents: "all",
        }}
      />
      <span style={{ fontSize: 10, color: "#b0b0bc", userSelect: "none" }}>{label}</span>
    </div>
  );
}

function DataHandle({ kind, id, position, top, label, typeName }) {
  const color = pinColor(typeName);
  return (
    <div
      style={{
        position: "absolute",
        top,
        [position === Position.Left ? "left" : "right"]: -14,
        display: "flex",
        alignItems: "center",
        gap: 4,
        flexDirection: position === Position.Left ? "row" : "row-reverse",
        pointerEvents: "none",
      }}
    >
      <Handle
        type={kind}
        position={position}
        id={id}
        style={{
          position: "relative",
          top: 0,
          left: 0,
          right: 0,
          transform: "none",
          width: 10,
          height: 10,
          background: color,
          border: `2px solid ${color}`,
          borderRadius: "50%",
          pointerEvents: "all",
        }}
      />
      <span style={{ fontSize: 10, color, userSelect: "none" }}>
        {label}
        {typeName && typeName !== "Any" && (
          <span style={{ opacity: 0.6 }}> ({typeName})</span>
        )}
      </span>
    </div>
  );
}

export default function FlowprintNode({ data }) {
  const { label, execInputs = [], execOutputs = [], dataInputs = {}, dataOutputs = {} } = data;

  const leftPins = [
    ...execInputs.map((id) => ({ kind: "exec", id, label: id })),
    ...Object.entries(dataInputs).map(([id, type]) => ({ kind: "data", id, label: id, type })),
  ];
  const rightPins = [
    ...execOutputs.map((id) => ({ kind: "exec", id, label: id })),
    ...Object.entries(dataOutputs).map(([id, type]) => ({ kind: "data", id, label: id, type })),
  ];

  const bodyH = Math.max(leftPins.length, rightPins.length) * PIN_H + 8;
  const totalH = HEADER_H + bodyH;

  function pinTop(i) {
    return HEADER_H + i * PIN_H + PIN_H / 2 - 5;
  }

  return (
    <div
      style={{
        background: "#1e1e2e",
        border: "1px solid #45475a",
        borderRadius: 6,
        minWidth: 160,
        height: totalH,
        position: "relative",
        boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
      }}
    >
      {/* header */}
      <div
        style={{
          height: HEADER_H,
          background: "#313244",
          borderRadius: "5px 5px 0 0",
          display: "flex",
          alignItems: "center",
          padding: "0 10px",
          fontSize: 12,
          fontWeight: 600,
          color: "#cdd6f4",
          borderBottom: "1px solid #45475a",
          overflow: "hidden",
          whiteSpace: "nowrap",
          textOverflow: "ellipsis",
        }}
      >
        {label}
      </div>

      {/* left pins */}
      {leftPins.map((pin, i) =>
        pin.kind === "exec" ? (
          <ExecHandle
            key={`l-${pin.id}`}
            kind="target"
            id={pin.id}
            position={Position.Left}
            top={pinTop(i)}
            label={pin.label}
          />
        ) : (
          <DataHandle
            key={`l-${pin.id}`}
            kind="target"
            id={pin.id}
            position={Position.Left}
            top={pinTop(i)}
            label={pin.label}
            typeName={pin.type}
          />
        )
      )}

      {/* right pins */}
      {rightPins.map((pin, i) =>
        pin.kind === "exec" ? (
          <ExecHandle
            key={`r-${pin.id}`}
            kind="source"
            id={pin.id}
            position={Position.Right}
            top={pinTop(i)}
            label={pin.label}
          />
        ) : (
          <DataHandle
            key={`r-${pin.id}`}
            kind="source"
            id={pin.id}
            position={Position.Right}
            top={pinTop(i)}
            label={pin.label}
            typeName={pin.type}
          />
        )
      )}
    </div>
  );
}
