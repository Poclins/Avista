// SelectorRol — selector de rol para la demo (Requirement 8.4).
// Dos opciones mutuamente excluyentes; sin autenticación real.
// Controles con área táctil mínima de 44 x 44 px (Requirement 9.2).

import type { Rol } from "../api/types";
import { useRol } from "../roles/RolContext";

const OPCIONES: { valor: Rol; etiqueta: string }[] = [
  { valor: "educadora", etiqueta: "Educadora" },
  { valor: "directora", etiqueta: "Directora" },
];

export function SelectorRol() {
  const { rol, setRol } = useRol();

  return (
    <div
      className="selector-rol"
      role="group"
      aria-label="Seleccionar rol activo"
    >
      {OPCIONES.map((opcion) => {
        const activo = rol === opcion.valor;
        return (
          <button
            key={opcion.valor}
            type="button"
            className={`touch-target boton-rol${activo ? " boton-rol--activo" : ""}`}
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
