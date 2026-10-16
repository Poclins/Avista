// Inicio — encamina según el rol activo hacia la primera sección del rol, o a
// la pantalla de selección si no hay rol (Requirement 8.5).

import { Navigate } from "react-router-dom";
import { useRol } from "../roles/RolContext";

export function Inicio() {
  const { rol } = useRol();

  if (rol === "educadora") {
    return <Navigate to="/educadora/mi-sala" replace />;
  }
  if (rol === "directora") {
    return <Navigate to="/directora/dashboard" replace />;
  }
  return <Navigate to="/seleccionar-rol" replace />;
}
