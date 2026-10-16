// GuardRol — restringe el acceso a las secciones según el rol activo.
//  - Si no hay rol seleccionado, redirige a la pantalla de selección
//    (Requirement 8.5).
//  - Si el rol activo no coincide con el requerido por la sección, redirige a
//    la raíz, garantizando exclusividad entre educadora y directora
//    (Requirements 8.2, 8.3).

import { Navigate, Outlet } from "react-router-dom";
import type { Rol } from "../api/types";
import { useRol } from "../roles/RolContext";

export function GuardRol({ rolRequerido }: { rolRequerido: Rol }) {
  const { rol } = useRol();

  if (rol === null) {
    return <Navigate to="/seleccionar-rol" replace />;
  }
  if (rol !== rolRequerido) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
