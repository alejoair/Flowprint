import React, { useState } from "react";

export default function Toolbar({
  graphName,
  graphs,
  onNew,
  onOpen,
  onSave,
  onDelete,
  onRun,
  onStop,
  running,
  dirty,
}) {
  const [showGraphs, setShowGraphs] = useState(false);

  return (
    <header className="toolbar">
      <div className="toolbar-brand">Flowprint</div>

      <div className="toolbar-section">
        <button className="btn" onClick={onNew}>New</button>

        <div className="dropdown-wrap">
          <button
            className="btn"
            onClick={() => setShowGraphs((v) => !v)}
          >
            Open {showGraphs ? "▲" : "▼"}
          </button>
          {showGraphs && (
            <div className="dropdown">
              {graphs.length === 0 && (
                <div className="dropdown-empty">No saved graphs</div>
              )}
              {graphs.map((g) => (
                <div
                  key={g.name}
                  className="dropdown-item"
                  onClick={() => {
                    onOpen(g.name);
                    setShowGraphs(false);
                  }}
                >
                  {g.name}
                </div>
              ))}
            </div>
          )}
        </div>

        <button className="btn btn-primary" onClick={onSave} disabled={!dirty}>
          Save{graphName ? ` "${graphName}"` : ""}
        </button>

        {graphName && (
          <button className="btn btn-danger" onClick={onDelete}>
            Delete
          </button>
        )}
      </div>

      <div className="toolbar-section toolbar-right">
        {running ? (
          <button className="btn btn-danger" onClick={onStop}>
            Stop
          </button>
        ) : (
          <button className="btn btn-run" onClick={onRun}>
            ▶ Run
          </button>
        )}
      </div>
    </header>
  );
}
