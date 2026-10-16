// SelectorRol â€” selector de RolUI para la demo (Requirement 8.4).
// Dos opciones mutuamente excluyentes; sin autenticaciÃ³n real.
// Controles con Ã¡rea tÃ¡ctil mÃ­nima de 44 x 44 px (Requirement 9.2).

import type { RolUI } from "../api/types";
import { useRol } from "../roles/RolContext";

const OPCIONES: { valor: RolUI; etiqueta: string }[] = [
  { valor: "educadora", etiqueta: "Educadora" },
  { valor: "directora", etiqueta: "Directora" },
];

export function SelectorRol() {
  const { rol, setRol } = useRol();

  return (
    <div
      className="selector-RolUI"
      role="group"
      aria-label="Seleccionar RolUI activo"
    >
      {OPCIONES.map((opcion) => {
        const activo = rol === opcion.valor;
        return (
          <button
            key={opcion.valor}
            type="button"
            className={`touch-target boton-RolUI${activo ? " boton-RolUI--activo" : ""}`}
            aria-pressed={activo}
            onClick={() => setRol(opcion.valor)}
          >
            {opcion.etiqueta}
          </button>
        );
      })}
    </div>
  );
}


