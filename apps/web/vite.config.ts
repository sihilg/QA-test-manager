import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 5173,
      proxy: { "/api": { target: process.env.VITE_API_TARGET || env.VITE_API_TARGET || "http://127.0.0.1:8000", rewrite: (path: string) => path.slice(4) } },
    },
    test: { environment: "jsdom", globals: true, setupFiles: "./src/test/setup.ts" },
  };
});
