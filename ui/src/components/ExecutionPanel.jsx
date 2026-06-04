import React, { useRef, useEffect } from "react";

function statusBadge(status) {
  const colors = {
    node_start: "#e5a663",
    node_complete: "#78c17a",
    error: "#f28b82",
    graph_complete: "#5ba4cf",
    cancelled: "#8c8c9a",
  };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "1px 6px",
        borderRadius: 3,
        fontSize: 10,
        fontWeight: 600,
        background: colors[status] ?? "#45475a",
        color: "#1e1e2e",
        marginRight: 6,
      }}
    >
      {status}
    </span>
  );
}

export default function ExecutionPanel({ events, onClose }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="exec-panel">
      <div className="exec-header">
        <span>Execution log</span>
        <button className="config-close" onClick={onClose}>✕</button>
      </div>
      <div className="exec-body">
        {events.length === 0 && (
          <div className="exec-empty">Press ▶ Run to execute the graph.</div>
        )}
        {events.map((ev, i) => (
          <div key={i} className="exec-event">
            {statusBadge(ev.type)}
            {ev.node_id && <span className="exec-node">{ev.node_id} </span>}
            {ev.type === "graph_complete" && ev.result != null && (
              <pre className="exec-result">{JSON.stringify(ev.result, null, 2)}</pre>
            )}
            {ev.type === "error" && ev.message && (
              <span className="exec-error">{ev.message}</span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
