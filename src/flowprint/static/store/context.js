import React, { createContext, useContext, useReducer } from "react";
import htm from "htm";
import { reducer, INITIAL_STATE } from "./reducer.js";

const html = htm.bind(React.createElement);
const Ctx  = createContext(null);

export function StoreProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  return html`<${Ctx.Provider} value=${{ state, dispatch }}>${children}</${Ctx.Provider}>`;
}

export function useStore() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useStore must be inside StoreProvider");
  return ctx;
}
