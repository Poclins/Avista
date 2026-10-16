import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/global.css";

const contenedor = document.getElementById("root");
if (!contenedor) {
  throw new Error('No se encontró el elemento con id "root".');
}

createRoot(contenedor).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
