export async function fetchCatalog() {
  const r = await fetch("/nodes"); if (!r.ok) throw new Error(r.status); return r.json();
}
export async function fetchGraphs() {
  const r = await fetch("/graphs"); if (!r.ok) throw new Error(r.status); return r.json();
}
export async function fetchGraph(name) {
  const r = await fetch(`/graphs/${name}`); if (!r.ok) throw new Error(r.status); return r.json();
}
export async function saveGraph(name, graph) {
  const r = await fetch(`/graphs/${name}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(graph) });
  if (!r.ok) throw new Error(r.status); return r.json();
}
export async function createGraph(name, graph) {
  const r = await fetch(`/graphs/${name}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(graph) });
  if (!r.ok) throw new Error(r.status); return r.json();
}
export async function deleteGraph(name) {
  const r = await fetch(`/graphs/${name}`, { method: "DELETE" }); if (!r.ok) throw new Error(r.status);
}

export function openRunWS(graph, args, onEvent, onClose) {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${location.host}/graph/run/ws`);
  ws.onopen    = () => ws.send(JSON.stringify({ graph, args: args ?? {} }));
  ws.onmessage = e => { try { onEvent(JSON.parse(e.data)); } catch {} };
  ws.onclose   = () => onClose?.();
  ws.onerror   = () => onClose?.();
  return ws;
}
