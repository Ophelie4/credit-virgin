import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // share.sh exposes the dev server through a Cloudflare quick tunnel
    allowedHosts: [".trycloudflare.com", "creditvirgin.tech", ".creditvirgin.tech"],
    proxy: { "/api": "http://localhost:8000" },
  },
});
