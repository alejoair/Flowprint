import { useEffect } from "react";
import { fetchCatalog } from "../api/http.js";
import { useStore } from "../store/context.js";
import { A } from "../store/actions.js";

export function useCatalog() {
  const { state, dispatch } = useStore();

  useEffect(() => {
    if (state.catalog.length > 0) return;
    fetchCatalog()
      .then(d => dispatch({ type: A.CATALOG_LOADED, payload: Array.isArray(d) ? d : d.nodes ?? [] }))
      .catch(console.error);
  }, []);

  return state.catalog;
}
