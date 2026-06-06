import React from "react";
import { createRoot } from "react-dom/client";
import htm from "htm";
import { StoreProvider } from "./store/context.js";
import App from "./App.js";

const html = htm.bind(React.createElement);

createRoot(document.getElementById("root")).render(
  html`<${StoreProvider}><${App} /></${StoreProvider}>`
);
