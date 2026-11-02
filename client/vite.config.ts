import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  envDir: "..", // the .env files of the project root, shared with the server and docker compose
  server: { port: 3001, strictPort: true },
  build: { outDir: "dist" },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
