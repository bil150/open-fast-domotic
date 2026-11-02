import "@fontsource/orbitron";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { initTranslator } from "./commons/application/locale/locale";

const container = document.getElementById("root");
if (!container) throw new Error("#root element not found");

// i18n must be ready before the first render
void initTranslator().then(() => {
  createRoot(container).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
});
