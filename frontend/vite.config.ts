import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5455 ("HW5"): 5173 and the other 5xxx ports are used by other course projects.
// The backend (http://localhost:8000) allows this origin in its CORS settings.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5455,
    strictPort: true,
  },
});
