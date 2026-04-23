import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Base path :
//  - en dev (npm run dev)   : "/"
//  - en build pour Pages    : "/act-energy-hedge-report/"
//    (sous-chemin du repo, injecte via env var BASE_PATH par le workflow)
const base = process.env.BASE_PATH || "/";

export default defineConfig({
  base,
  plugins: [react(), tailwindcss()],
  server: { open: true },
});
