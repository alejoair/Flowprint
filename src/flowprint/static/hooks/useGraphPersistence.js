import { useStore } from "../store/context.js";
import { A } from "../store/actions.js";
import * as http from "../api/http.js";

export function useGraphPersistence() {
  const { state, dispatch } = useStore();

  async function loadList() {
    const list = await http.fetchGraphs();
    dispatch({ type: A.GRAPHS_LIST_LOADED, payload: Array.isArray(list) ? list : [] });
  }

  async function load(name) {
    const graph = await http.fetchGraph(name);
    dispatch({ type: A.GRAPH_LOADED, payload: { name, graph } });
    return graph;
  }

  async function save(name, graph) {
    state.graphName
      ? await http.saveGraph(name, graph)
      : await http.createGraph(name, graph);
    dispatch({ type: A.GRAPH_SAVED, payload: { name } });
    await loadList();
  }

  async function remove(name) {
    await http.deleteGraph(name);
    await loadList();
  }

  return { load, save, remove, loadList };
}
