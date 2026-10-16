// Definición de la navegación por rol (Requirement 8.2 y 8.3).
// Educadora: Mi sala, Capturar, Ficha, Bitácoras, Recomendaciones.
// Directora: Dashboard de dirección.

export interface ItemNav {
  ruta: string;
  etiqueta: string;
}

export const NAV_EDUCADORA: ItemNav[] = [
  { ruta: "/educadora/mi-sala", etiqueta: "Mi sala" },
  { ruta: "/educadora/capturar", etiqueta: "Capturar" },
  { ruta: "/educadora/bitacoras", etiqueta: "Bitácoras" },
];

export const NAV_DIRECTORA: ItemNav[] = [
  { ruta: "/directora/dashboard", etiqueta: "Dashboard" },
];
