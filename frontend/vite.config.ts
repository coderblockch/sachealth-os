/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// API paths served by FastAPI. In dev, Vite proxies them to the backend so the
// browser talks to a single origin (no CORS needed, same as production).
const API_PATHS = ["/auth", "/beds", "/patients", "/triage", "/stats", "/health"];
const BACKEND_URL = process.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  // FastAPI serves the build under /app so React routes never clash with /beds etc.
  base: "/app/",
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(API_PATHS.map((path) => [path, { target: BACKEND_URL, changeOrigin: true }])),
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    restoreMocks: true,
  },
});
