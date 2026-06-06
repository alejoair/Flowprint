import { useStore } from "../store/context.js";
import { A } from "../store/actions.js";
import * as http from "../api/http.js";

export function useCustomNodes({ reloadCatalog } = {}) {
  const { state, dispatch } = useStore();

  async function loadList() {
    const list = await http.fetchCustomNodes();
    dispatch({ type: A.CUSTOM_NODES_LOADED, payload: Array.isArray(list) ? list : [] });
  }

  async function save(name, source, isNew) {
    isNew
      ? await http.createCustomNode(name, source)
      : await http.updateCustomNode(name, source);
    await loadList();
    await reloadCatalog?.();  // new node type appears in sidebar
  }

  async function remove(name) {
    await http.deleteCustomNode(name);
    await loadList();
    await reloadCatalog?.();
  }

  return {
    customNodes: state.customNodes,
    loadList,
    save,
    remove,
  };
}
