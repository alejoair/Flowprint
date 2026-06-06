import React, { useEffect, useRef } from "react";
import htm from "htm";

const html = htm.bind(React.createElement);

const EV_COLORS = {
  node_start:     "#e5a663",
  node_complete:  "#78c17a",
  error:          "#f28b82",
  graph_complete: "#5ba4cf",
  cancelled:      "#8c8c9a",
};

export function ExecutionPanel({ events, onClose }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return html`
    <div className="exec-panel">
      <div className="exec-header">
        <span>Execution log</span>
        <button className="config-close" onClick=${onClose}>✕</button>
      </div>
      <div className="exec-body">
        ${events.length === 0 && html`
          <div className="exec-empty">Press ▶ Run to execute the graph.</div>`}
        ${events.map((ev, i) => {
          const type   = ev.event ?? ev.type ?? "unknown";
          const nodeId = ev.node  ?? ev.node_id;
          return html`
            <div key=${i} className="exec-event">
              <span style=${{
                display: "inline-block", padding: "1px 6px", borderRadius: 3,
                fontSize: 10, fontWeight: 600, marginRight: 6,
                background: EV_COLORS[type] ?? "#45475a", color: "#1e1e2e",
              }}>${type}</span>
              ${nodeId && html`<span className="exec-node">${nodeId} </span>`}
              ${type === "graph_complete" && ev.result != null && html`
                <pre className="exec-result">${JSON.stringify(ev.result, null, 2)}</pre>`}
              ${type === "error" && (ev.error ?? ev.message) && html`
                <span className="exec-error">${ev.error ?? ev.message}</span>`}
            </div>`;
        })}
        <div ref=${bottomRef} />
      </div>
    </div>`;
}
