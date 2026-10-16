// Mapas de etiquetas legibles (es-CL) para presentar enums del contrato REST.
// Puramente de PRESENTACION (Requirement 9.6: sin logica de negocio).

import type { DecisionNivel, Dominio, Nino } from "../api/types";

export const ETIQUETA_DOMINIO: Record<Dominio, string> = {
  cognitivo: "Cognitivo",
  lenguaje_comunicacion: "Lenguaje y comunicacion",
  motor_fino: "Motor fino",
  motor_grueso: "Motor grueso",
  socioemocional: "Socioemocional",
};

export const DOMINIOS: Dominio[] = [
  "cognitivo",
  "lenguaje_comunicacion",
  "motor_fino",
  "motor_grueso",
  "socioemocional",
];

export const ETIQUETA_DECISION: Record<DecisionNivel, string> = {
  AVANZAR: "Puede avanzar de nivel",
  MANTENER: "Mantener el nivel actual",
  RETROCEDER: "Conviene reforzar el nivel",
};

/** Clase CSS del badge de estado para una decision de nivel. */
export function claseEstadoDecision(decision: DecisionNivel): string {
  return `estado estado--${decision.toLowerCase()}`;
}

/** Formatea una fecha ISO del backend a un formato local legible. */
export function formatearFecha(iso: string | undefined | null): string {
  if (!iso) return "-";
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return fecha.toLocaleDateString("es-CL", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}


export function nombreCompletoNino(
  nino: Pick<Nino, "nombre" | "apellido_paterno" | "apellido_materno">,
): string {
  return [nino.nombre, nino.apellido_paterno, nino.apellido_materno]
    .filter(Boolean)
    .join(" ");
}