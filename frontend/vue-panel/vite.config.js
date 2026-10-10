
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  build: {
    lib: {
      entry: "src/panel.js",
      name: "VuePanel",
      fileName: () => "vue-panel.js",
      formats: ["es"],
      cssFileName: "vue-panel"
    }
  }
});
