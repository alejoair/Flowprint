import { A } from "./actions.js";

export const INITIAL_STATE = {
  catalog:        [],
  graphs:         [],
  graphName:      null,
  signature:      { inputs: {}, outputs: {} },
  dirty:          false,
  selectedNodeId: null,
  running:        false,
  execEvents:     [],
  showExecPanel:  false,
  customNodes:    [],
  nodeEditorOpen: false,
};

export function reducer(state, { type, payload }) {
  switch (type) {
    case A.CATALOG_LOADED:
      return { ...state, catalog: payload };

    case A.GRAPHS_LIST_LOADED:
      return { ...state, graphs: payload };

    case A.GRAPH_LOADED:
      return {
        ...state,
        graphName:      payload.name,
        signature:      payload.graph?.signature ?? { inputs: {}, outputs: {} },
        dirty:          false,
        selectedNodeId: null,
        execEvents:     [],
      };

    case A.GRAPH_SAVED:
      return { ...state, graphName: payload.name, dirty: false };

    case A.MARK_DIRTY:
      return { ...state, dirty: true };

    case A.NODE_SELECTED:
      return { ...state, selectedNodeId: payload };

    case A.NODE_DESELECTED:
      return { ...state, selectedNodeId: null };

    case A.EXECUTION_STARTED:
      return { ...state, running: true, execEvents: [], showExecPanel: true };

    case A.EXECUTION_EVENT:
      return { ...state, execEvents: [...state.execEvents, payload] };

    case A.EXECUTION_DONE:
      return { ...state, running: false };

    case A.EXEC_PANEL_TOGGLE:
      return { ...state, showExecPanel: !state.showExecPanel };

    case A.CUSTOM_NODES_LOADED:
      return { ...state, customNodes: payload };

    case A.NODE_EDITOR_OPEN:
      return { ...state, nodeEditorOpen: true };

    case A.NODE_EDITOR_CLOSE:
      return { ...state, nodeEditorOpen: false };

    case A.SIGNATURE_CHANGED:
      return { ...state, signature: payload, dirty: true };

    default:
      return state;
  }
}
