import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// PWA mobile-first (Requirement 9.1). El manifest y el service worker se generan
// con vite-plugin-pwa; el estilo definitivo llega desde los mockups de Figma.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "jAImes — Fundación Integra",
        short_name: "jAImes",
        description:
          "Asistente de documentación pedagógica (datos sintéticos de uso pedagógico).",
        lang: "es-CL",
        dir: "ltr",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        background_color: "#ffffff",
        theme_color: "#1b4965",
        // Ícono vectorial escalable del scaffold. Los íconos PNG definitivos
        // (192/512, incl. maskable) llegan con los assets de Figma (Tarea 13).
        icons: [
          {
            src: "favicon.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico,woff2}"],
        // No cachear la API REST: siempre datos frescos del backend.
        navigateFallbackDenylist: [/^\/api/, /^\/health/],
      },
      devOptions: {
        enabled: false,
      },
    }),
  ],
  server: {
    port: 5173,
    // Proxy opcional hacia el backend FastAPI local durante el desarrollo.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
