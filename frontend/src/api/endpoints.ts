// Capa de servicios API tipada: una funcion por endpoint del contrato REST.
// Alineada EXACTAMENTE a los routers del backend (backend/app/api/routers).

import { request } from "./client";
import type {
  Bitacora,
  ConfirmarClasificacionBody,
  DecisionRecomendacionBody,
  EditarBitacoraBody,
  Educadora,
  FichaNino,
  GenerarBitacoraBody,
  GenerarRecomendacionBody,
  HealthStatus,
  Nino,
  Observacion,
  PeriodoReporte,
  Recomendacion,
  RecomendacionDecision,
  ReporteDireccion,
  RutaNiveles,
} from "./types";

// --- Educadoras y niños relacionados ---

/** GET /educadoras - opciones válidas del dataset. */
export function listarEducadoras(): Promise<Educadora[]> {
  return request<Educadora[]>("/educadoras");
}

/** GET /educadoras/{id}/ninos - niños/as del mismo jardín. */
export function listarNinosDeEducadora(idEducadora: string): Promise<Nino[]> {
  return request<Nino[]>(
    `/educadoras/${encodeURIComponent(idEducadora)}/ninos`,
  );
}
// --- Observaciones ---

/** POST /ninos/{id}/observaciones (multipart: medio o texto). */
export function crearObservacion(
  idNino: string,
  formData: FormData,
): Promise<Observacion> {
  return request<Observacion>(`/ninos/${encodeURIComponent(idNino)}/observaciones`, {
    method: "POST",
    formData,
    timeoutMs: 120_000,
  });
}

/** GET /ninos/{id}/observaciones - listar observaciones de un nino/a. */
export function listarObservaciones(idNino: string): Promise<Observacion[]> {
  return request<Observacion[]>(`/ninos/${encodeURIComponent(idNino)}/observaciones`);
}

/** PATCH /observaciones/{id}/clasificacion - confirmar/corregir. */
export function confirmarClasificacion(
  idObservacion: string,
  body: ConfirmarClasificacionBody,
): Promise<Observacion> {
  return request<Observacion>(
    `/observaciones/${encodeURIComponent(idObservacion)}/clasificacion`,
    { method: "PATCH", body },
  );
}

// --- Ninos ---

/** GET /ninos/{id} - ficha + trayectoria. */
export function obtenerFichaNino(idNino: string): Promise<FichaNino> {
  return request<FichaNino>(`/ninos/${encodeURIComponent(idNino)}`);
}

/** GET /ninos?jardin=...&sala=... - "Mi sala" (requiere ambos). */
export function listarNinosPorSala(jardin: string, sala: string): Promise<Nino[]> {
  return request<Nino[]>("/ninos", { query: { jardin, sala } });
}

// --- Bitacoras ---

/** POST /ninos/{id}/bitacoras - generar bitacora quincenal. */
export function generarBitacora(
  idNino: string,
  body: GenerarBitacoraBody,
): Promise<Bitacora> {
  return request<Bitacora>(`/ninos/${encodeURIComponent(idNino)}/bitacoras`, {
    method: "POST",
    body,
  });
}

/** GET /ninos/{id}/bitacoras - listar bitacoras. */
export function listarBitacoras(idNino: string): Promise<Bitacora[]> {
  return request<Bitacora[]>(`/ninos/${encodeURIComponent(idNino)}/bitacoras`);
}

/** PATCH /bitacoras/{id} - editar / aprobar. */
export function editarBitacora(
  idBitacora: string,
  body: EditarBitacoraBody,
): Promise<Bitacora> {
  return request<Bitacora>(`/bitacoras/${encodeURIComponent(idBitacora)}`, {
    method: "PATCH",
    body,
  });
}

// --- Recomendaciones ---

/** POST /ninos/{id}/recomendaciones - generar recomendacion de nivel. */
export function generarRecomendacion(
  idNino: string,
  body: GenerarRecomendacionBody,
): Promise<Recomendacion> {
  return request<Recomendacion>(
    `/ninos/${encodeURIComponent(idNino)}/recomendaciones`,
    { method: "POST", body },
  );
}

/** POST /recomendaciones/{id}/decision - registrar decision de la educadora. */
export function registrarDecisionRecomendacion(
  idRecomendacion: string,
  body: DecisionRecomendacionBody,
): Promise<RecomendacionDecision> {
  return request<RecomendacionDecision>(
    `/recomendaciones/${encodeURIComponent(idRecomendacion)}/decision`,
    { method: "POST", body },
  );
}

// --- Reportes de direccion ---

/** GET /jardines/{id}/reportes - generar/obtener reporte. */
export function obtenerReporteDireccion(
  idJardin: string,
  periodo: PeriodoReporte,
): Promise<ReporteDireccion> {
  return request<ReporteDireccion>(
    `/jardines/${encodeURIComponent(idJardin)}/reportes`,
    { query: { ...periodo } },
  );
}

// --- Ruta de referencia ---

/** GET /ruta-niveles - devuelve { niveles, version_rubrica }. */
export function obtenerRutaNiveles(): Promise<RutaNiveles> {
  return request<RutaNiveles>("/ruta-niveles");
}

// --- Salud ---

/** GET /health. */
export function obtenerSalud(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}
