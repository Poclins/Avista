// Mapas de etiquetas legibles (español de Chile) para presentar enums del
// contrato REST. Son puramente de PRESENTACIÓN: no toman decisiones ni derivan
// datos de negocio, solo traducen un valor del backend a texto para la UI
// (Requirement 9.6: sin lógica de negocio en el cliente).

import type { DecisionNivel, Dominio } from "../api/types";

export const ETIQUETA_DOMINIO: Record<Dominio, string> = {
  identidad_y_autonomia: "Identidad y autonomía",
  convivencia_y_ciudadania: "Convivencia y ciudadanía",
  corporalidad_y_movimiento: "Corporalidad y movimiento",
  lenguaje_verbal: "Lenguaje verbal",
  exploracion_del_entorno: "Exploración del entorno",
};

export const DOMINIOS: Dominio[] = [
  "identidad_y_autonomia",
  "convivencia_y_ciudadania",
  "corporalidad_y_movimiento",
  "lenguaje_verbal",
  "exploracion_del_entorno",
];

export const ETIQUETA_DECISION: Record<DecisionNivel, string> = {
  avanzar: "Puede avanzar de nivel",
  mantener: "Mantener el nivel actual",
  retroceder: "Conviene reforzar el nivel",
};

/** Clase CSS del badge de estado para una decisión de nivel. */
export function claseEstadoDecision(decision: DecisionNivel): string {
  return `estado estado--${decision}`;
}

/** Formatea una fecha ISO del backend a un formato local legible. */
export function formatearFecha(iso: string | undefined): string {
  if (!iso) return "—";
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return fecha.toLocaleDateString("es-CL", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
