import React, { useState, useMemo } from "react";

export default function Sidebar({ catalog }) {
  const [search, setSearch] = useState("");

  const groups = useMemo(() => {
    const filtered = catalog.filter(
      (n) =>
        n.type.toLowerCase().includes(search.toLowerCase()) ||
        (n.description || "").toLowerCase().includes(search.toLowerCase())
    );
    const map = {};
    for (const n of filtered) {
      const group = n.is_pure ? "Pure" : "Effect";
      if (!map[group]) map[group] = [];
      map[group].push(n);
    }
    return map;
  }, [catalog, search]);

  function onDragStart(e, nodeType) {
    e.dataTransfer.setData("application/flowprint-node", nodeType);
    e.dataTransfer.effectAllowed = "move";
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">Nodes</div>
      <input
        className="sidebar-search"
        placeholder="Search…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div className="sidebar-list">
        {Object.entries(groups).map(([group, nodes]) => (
          <div key={group}>
            <div className="sidebar-group">{group}</div>
            {nodes.map((n) => (
              <div
                key={n.type}
                className="sidebar-item"
                draggable
                onDragStart={(e) => onDragStart(e, n.type)}
                title={n.description}
              >
                <span className="sidebar-item-name">{n.type}</span>
                {n.description && (
                  <span className="sidebar-item-desc">{n.description}</span>
                )}
              </div>
            ))}
          </div>
        ))}
        {Object.keys(groups).length === 0 && (
          <div className="sidebar-empty">No nodes match.</div>
        )}
      </div>
    </aside>
  );
}
