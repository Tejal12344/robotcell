
import { createApp } from "vue";
import Panel from "./Panel.vue";

window.mountVuePanel = function (element, options = {}) {
  if (!element) {
    console.error("Vue panel mount element was not found.");
    return null;
  }

  const app = createApp(Panel, options);
  app.mount(element);

  return app;
};
