import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backendPort = process.env.BACKEND_PORT || "3000";
const backendUrl = `http://127.0.0.1:${backendPort}`;

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": backendUrl,
      "/ws": { target: backendUrl, ws: true },
    },
  },
});
