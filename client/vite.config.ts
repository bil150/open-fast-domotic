import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  envDir: "..", // the .env files of the project root, shared with the server and docker compose
  // /api (REST and WebSocket) goes to the server run next to it, so the client calls its own origin as in production
  server: { host: "0.0.0.0", port: 3001, strictPort: true, proxy: { "/api": { target: "http://localhost:8000", ws: true } } },
  build: { outDir: "dist" },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
