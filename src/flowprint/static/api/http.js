async function _fetch(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    const msg = await r.text().catch(() => String(r.status));
    throw new Error(`${opts?.method ?? "GET"} ${url} → ${r.status}: ${msg}`);
  }
  return r.status === 204 ? null : r.json();
}

const json = body => ({ headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const fetchCatalog  = () => _fetch("/nodes");
export const fetchGraphs   = () => _fetch("/graphs");
export const fetchGraph    = name => _fetch(`/graphs/${name}`).then(d => d.graph ?? d);
export const createGraph   = (name, graph) => _fetch(`/graphs/${name}`, { method: "POST", ...json({ graph }) });
export const saveGraph     = (name, graph) => _fetch(`/graphs/${name}`, { method: "PUT",  ...json({ graph }) });
export const deleteGraph   = name => _fetch(`/graphs/${name}`, { method: "DELETE" });
export const validateGraph = graph => _fetch("/graph/validate", { method: "POST", ...json({ graph }) });
