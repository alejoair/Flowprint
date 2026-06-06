export class RunSession {
  constructor(graph, args, { onEvent, onDone }) {
    this._graph  = graph;
    this._args   = args ?? {};
    this._onEvent = onEvent;
    this._onDone  = onDone;
    this._ws     = null;
  }

  start() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${location.host}/graph/run/ws`);
    this._ws = ws;
    ws.onopen    = () => ws.send(JSON.stringify({ graph: this._graph, args: this._args }));
    ws.onmessage = e => { try { this._onEvent(JSON.parse(e.data)); } catch {} };
    ws.onclose   = () => this._onDone?.();
    ws.onerror   = () => this._onDone?.();
  }

  cancel() { this._ws?.close(); }
}
