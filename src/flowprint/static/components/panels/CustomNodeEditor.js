import React, { useState, useEffect, useRef, useCallback } from "react";
import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { python } from "@codemirror/lang-python";
import htm from "htm";

const html = htm.bind(React.createElement);

// ── CodeMirror dark theme ──────────────────────────

const DARK_THEME = EditorView.theme({
  "&":                           { height: "100%", backgroundColor: "#1e1e2e", color: "#cdd6f4" },
  "&.cm-focused":                { outline: "none" },
  ".cm-scroller":                { overflow: "auto", fontFamily: "'JetBrains Mono','Fira Code',monospace", fontSize: "13px" },
  ".cm-content":                 { caretColor: "#cdd6f4", padding: "4px 0" },
  ".cm-cursor":                  { borderLeftColor: "#cdd6f4" },
  ".cm-selectionBackground, ::selection": { backgroundColor: "#3d3f58 !important" },
  ".cm-activeLine":              { backgroundColor: "#26263a" },
  ".cm-activeLineGutter":        { backgroundColor: "#26263a" },
  ".cm-gutters":                 { backgroundColor: "#181825", borderRight: "1px solid #45475a", color: "#585b70" },
  ".cm-lineNumbers .cm-gutterElement": { padding: "0 8px 0 4px", minWidth: "32px" },
  ".cm-matchingBracket":         { backgroundColor: "#45475a", outline: "none" },
  ".cm-tooltip":                 { backgroundColor: "#313244", border: "1px solid #45475a" },
}, { dark: true });

// ── Node template ──────────────────────────────────

function makeTemplate(name) {
  const cls = name.charAt(0).toUpperCase() + name.slice(1);
  return `from pydantic import BaseModel
from flowprint.core.node import Node, NodeResult, ExecutionContext
from flowprint.core.control import Stop


class ${cls}(Node):
    """Descripción breve del nodo."""

    class Inputs(BaseModel):
        value: str = ""

    class Outputs(BaseModel):
        result: str = ""

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.value), Stop())
`;
}

// ── CodeMirror React wrapper ───────────────────────

function CodeEditor({ source, onChange }) {
  const containerRef = useRef(null);
  const viewRef      = useRef(null);

  useEffect(() => {
    viewRef.current = new EditorView({
      state: EditorState.create({
        doc: source,
        extensions: [
          basicSetup,
          python(),
          DARK_THEME,
          EditorView.updateListener.of(update => {
            if (update.docChanged) onChange(update.state.doc.toString());
          }),
        ],
      }),
      parent: containerRef.current,
    });
    return () => viewRef.current?.destroy();
  }, []); // create once

  // Sync external source changes (e.g. switching nodes)
  const prevSource = useRef(source);
  useEffect(() => {
    if (!viewRef.current || source === prevSource.current) return;
    prevSource.current = source;
    const current = viewRef.current.state.doc.toString();
    if (current !== source) {
      viewRef.current.dispatch({
        changes: { from: 0, to: current.length, insert: source },
      });
    }
  }, [source]);

  return html`<div ref=${containerRef} className="cm-host" />`;
}

// ── CustomNodeEditor panel ─────────────────────────

export function CustomNodeEditor({ customNodes, onLoad, onSave, onDelete, onClose }) {
  const [selected, setSelected]   = useState(null); // {name, source, isNew}
  const [source,   setSource]     = useState("");
  const [newName,  setNewName]    = useState("");
  const [error,    setError]      = useState(null);
  const [saving,   setSaving]     = useState(false);

  // Load list on open
  useEffect(() => { onLoad(); }, []);

  function selectNode(node) {
    setSelected({ name: node.name, isNew: false });
    setSource(node.source);
    setError(null);
  }

  function startNew() {
    const name = prompt("Nombre del nodo (identificador Python válido):");
    if (!name) return;
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) {
      alert("El nombre debe ser un identificador Python válido (letras, números, _).");
      return;
    }
    setSelected({ name, isNew: true });
    setSource(makeTemplate(name));
    setError(null);
  }

  async function handleSave() {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      await onSave(selected.name, source, selected.isNew);
      setSelected(prev => ({ ...prev, isNew: false })); // now it exists
    } catch (e) {
      // Server returns the syntax error message in the response body
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!selected || selected.isNew) return;
    if (!confirm(`¿Eliminar el nodo "${selected.name}"?`)) return;
    setSaving(true);
    try {
      await onDelete(selected.name);
      setSelected(null);
      setSource("");
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return html`
    <div className="modal-backdrop" onClick=${e => e.target === e.currentTarget && onClose()}>
      <div className="modal-panel">

        <div className="modal-header">
          <span>Custom Nodes</span>
          <button className="config-close" onClick=${onClose}>✕</button>
        </div>

        <div className="modal-body">

          <!-- Node list -->
          <div className="nodelist">
            <button className="btn btn-sm btn-primary" style=${{ margin: "8px", width: "calc(100% - 16px)" }}
              onClick=${startNew}>+ New node</button>
            ${customNodes.length === 0 && html`
              <div className="sidebar-empty">No custom nodes yet.</div>`}
            ${customNodes.map(n => html`
              <div key=${n.name}
                className=${"nodelist-item" + (selected?.name === n.name ? " nodelist-item--active" : "")}
                onClick=${() => selectNode(n)}>
                ${n.name}
              </div>`)}
          </div>

          <!-- Editor area -->
          <div className="editor-area">
            ${!selected && html`
              <div className="editor-placeholder">
                Select a node or create a new one.
              </div>`}

            ${selected && html`
              <div className="editor-topbar">
                <span className="editor-name">${selected.name}${selected.isNew ? " (new)" : ""}</span>
                <div style=${{ display: "flex", gap: 8 }}>
                  ${!selected.isNew && html`
                    <button className="btn btn-danger btn-sm" onClick=${handleDelete}
                      disabled=${saving}>Delete</button>`}
                  <button className="btn btn-primary btn-sm" onClick=${handleSave}
                    disabled=${saving}>${saving ? "Saving…" : "Save"}</button>
                </div>
              </div>

              ${error && html`<div className="editor-error">${error}</div>`}

              <div className="editor-wrap">
                <${CodeEditor} source=${source} onChange=${setSource} />
              </div>`}
          </div>

        </div>
      </div>
    </div>`;
}
