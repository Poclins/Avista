// Restringe cada sección al rol de UI seleccionado.

import { Navigate, Outlet } from "react-router-dom";
import type { RolUI } from "../api/types";
import { useRol } from "../roles/RolContext";

export function GuardRol({ rolRequerido }: { rolRequerido: RolUI }) {
  const { rol } = useRol();

  if (rol === null) {
    return <Navigate to="/seleccionar-rol" replace />;
  }
  if (rol !== rolRequerido) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
