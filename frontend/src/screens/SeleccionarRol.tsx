// SeleccionarRol — pantalla mostrada cuando no hay rol activo (Requirement 8.5):
// solicita elegir un rol antes de acceder a las secciones específicas.

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { SelectorRol } from "../components/SelectorRol";
import { useRol } from "../roles/RolContext";

export function SeleccionarRol() {
  const { rol } = useRol();
  const navigate = useNavigate();

  // Al elegir un rol, redirige a la raíz, que encamina según el rol.
  useEffect(() => {
    if (rol) navigate("/", { replace: true });
  }, [rol, navigate]);

  return (
    <section className="pantalla pantalla--centro">
      <h1 className="pantalla__titulo">Selecciona un rol</h1>
      <p className="pantalla__descripcion">
        Para continuar, elige con qué rol quieres usar jAImes. En la demo no se
        requiere autenticación.
      </p>
      <SelectorRol />
    </section>
  );
}
