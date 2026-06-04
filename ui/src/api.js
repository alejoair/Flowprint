const BASE = "";

export async function fetchCatalog() {
  const res = await fetch(`${BASE}/nodes`);
  if (!res.ok) throw new Error(`GET /nodes → ${res.status}`);
  return res.json();
}

export async function fetchGraphs() {
  const res = await fetch(`${BASE}/graphs`);
  if (!res.ok) throw new Error(`GET /graphs → ${res.status}`);
  return res.json();
}

export async function fetchGraph(name) {
  const res = await fetch(`${BASE}/graphs/${name}`);
  if (!res.ok) throw new Error(`GET /graphs/${name} → ${res.status}`);
  return res.json();
}

export async function saveGraph(name, graph) {
  const res = await fetch(`${BASE}/graphs/${name}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph),
  });
  if (!res.ok) throw new Error(`PUT /graphs/${name} → ${res.status}`);
  return res.json();
}

export async function createGraph(name, graph) {
  const res = await fetch(`${BASE}/graphs/${name}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph),
  });
  if (!res.ok) throw new Error(`POST /graphs/${name} → ${res.status}`);
  return res.json();
}

export async function deleteGraph(name) {
  const res = await fetch(`${BASE}/graphs/${name}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE /graphs/${name} → ${res.status}`);
}

export async function validateGraph(graph) {
  const res = await fetch(`${BASE}/graph/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph),
  });
  if (!res.ok) throw new Error(`POST /graph/validate → ${res.status}`);
  return res.json();
}

export function openRunWS(graph, args, onEvent, onClose) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${window.location.host}/graph/run/ws`);

  ws.onopen = () => ws.send(JSON.stringify({ graph, args: args ?? {} }));
  ws.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data));
    } catch {
      /* ignore non-JSON frames */
    }
  };
  ws.onclose = () => onClose?.();
  ws.onerror = () => onClose?.();
  return ws;
}
