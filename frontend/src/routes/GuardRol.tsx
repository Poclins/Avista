// GuardRol â€” restringe el acceso a las secciones segÃºn el RolUI activo.
//  - Si no hay RolUI seleccionado, redirige a la pantalla de selecciÃ³n
//    (Requirement 8.5).
//  - Si el RolUI activo no coincide con el requerido por la secciÃ³n, redirige a
//    la raÃ­z, garantizando exclusividad entre educadora y directora
//    (Requirements 8.2, 8.3).

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


