import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../src/flowprint/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/nodes": "http://localhost:8000",
      "/graphs": "http://localhost:8000",
      "/graph": "http://localhost:8000",
      "/types": "http://localhost:8000",
      "/mcp": "http://localhost:8000",
    },
  },
});
