import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        strictPort: true,

        // Allow local-network + your domain
        host: true,                     // enables LAN access
        allowedHosts: [
            "dashboards.paudaboyzz.com" // allow your domain
        ],

        proxy: {
            "/api": {
                target: "http://localhost:4000",
                changeOrigin: true,
            },
        },
    },
});
