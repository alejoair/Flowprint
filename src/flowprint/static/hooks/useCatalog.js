import { useEffect } from "react";
import { fetchCatalog } from "../api/http.js";
import { useStore } from "../store/context.js";
import { A } from "../store/actions.js";

export function useCatalog() {
  const { state, dispatch } = useStore();

  async function load() {
    const d = await fetchCatalog();
    dispatch({ type: A.CATALOG_LOADED, payload: Array.isArray(d) ? d : d.nodes ?? [] });
  }

  useEffect(() => { if (state.catalog.length === 0) load(); }, []);

  return { catalog: state.catalog, reloadCatalog: load };
}
