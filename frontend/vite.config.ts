import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backendHost = process.env.BACKEND_HOST ?? "";
const backendPort = process.env.BACKEND_PORT ?? "";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    __APP_BACKEND_HOST__: JSON.stringify(backendHost),
    __APP_BACKEND_PORT__: JSON.stringify(backendPort),
  },
  server: {
    allowedHosts: ["localhost", "127.0.0.1"],
  },
  preview: {
    allowedHosts: true,
  },
});
