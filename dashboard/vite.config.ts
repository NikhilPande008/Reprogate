import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      ["/investigations", "/evaluation", "/demo", "/pilot-review", "/review-packets", "/webhook-jobs"].map((path) => [path, process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000"]),
    ),
  },
  test: { environment: "jsdom", setupFiles: "./src/testSetup.ts" },
});
