// Capa de servicios API tipada: una función por endpoint del contrato REST
// (Módulo G). No contiene lógica de negocio; solo compone la llamada y devuelve
// datos tipados (Requirement 9.6).

import { request } from "./client";
import type {
  Bitacora,
  ConfirmarClasificacionBody,
  DecisionRecomendacionBody,
  EditarBitacoraBody,
  FichaNino,
  GenerarBitacoraBody,
  HealthStatus,
  NivelRuta,
  Nino,
  Observacion,
  PeriodoReporte,
  Recomendacion,
  ReporteDireccion,
} from "./types";

// --- Observaciones ---

/**
 * POST /ninos/{id}/observaciones
 * Crea una observación (multipart: medio o texto) y devuelve la clasificación propuesta.
 */
export function crearObservacion(
  idNino: string,
  formData: FormData,
): Promise<Observacion> {
  return request<Observacion>(`/ninos/${encodeURIComponent(idNino)}/observaciones`, {
    method: "POST",
    formData,
  });
}

/** PATCH /observaciones/{id}/clasificacion — confirmar/corregir clasificación. */
export function confirmarClasificacion(
  idObservacion: string,
  body: ConfirmarClasificacionBody,
): Promise<Observacion> {
  return request<Observacion>(
    `/observaciones/${encodeURIComponent(idObservacion)}/clasificacion`,
    { method: "PATCH", body },
  );
}

/** GET /ninos/{id}/observaciones — listar observaciones de un niño/a. */
export function listarObservaciones(idNino: string): Promise<Observacion[]> {
  return request<Observacion[]>(
    `/ninos/${encodeURIComponent(idNino)}/observaciones`,
  );
}

// --- Niños ---

/** GET /ninos/{id} — ficha + trayectoria. */
export function obtenerFichaNino(idNino: string): Promise<FichaNino> {
  return request<FichaNino>(`/ninos/${encodeURIComponent(idNino)}`);
}

/** GET /ninos?sala=... — "Mi sala". */
export function listarNinosPorSala(sala: string): Promise<Nino[]> {
  return request<Nino[]>("/ninos", { query: { sala } });
}

// --- Bitácoras ---

/** POST /ninos/{id}/bitacoras — generar bitácora quincenal. */
export function generarBitacora(
  idNino: string,
  body: GenerarBitacoraBody,
): Promise<Bitacora> {
  return request<Bitacora>(`/ninos/${encodeURIComponent(idNino)}/bitacoras`, {
    method: "POST",
    body,
  });
}

/** GET /ninos/{id}/bitacoras — listar bitácoras. */
export function listarBitacoras(idNino: string): Promise<Bitacora[]> {
  return request<Bitacora[]>(`/ninos/${encodeURIComponent(idNino)}/bitacoras`);
}

/** PATCH /bitacoras/{id} — editar / aprobar. */
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

/** POST /ninos/{id}/recomendaciones — generar recomendación de nivel. */
export function generarRecomendacion(idNino: string): Promise<Recomendacion> {
  return request<Recomendacion>(
    `/ninos/${encodeURIComponent(idNino)}/recomendaciones`,
    { method: "POST" },
  );
}

/** POST /recomendaciones/{id}/decision — registrar decisión de la educadora. */
export function registrarDecisionRecomendacion(
  idRecomendacion: string,
  body: DecisionRecomendacionBody,
): Promise<Recomendacion> {
  return request<Recomendacion>(
    `/recomendaciones/${encodeURIComponent(idRecomendacion)}/decision`,
    { method: "POST", body },
  );
}

// --- Reportes de dirección ---

/** GET /jardines/{id}/reportes — generar/obtener reporte de dirección. */
export function obtenerReporteDireccion(
  idJardin: string,
  periodo: PeriodoReporte,
): Promise<ReporteDireccion> {
  return request<ReporteDireccion>(
    `/jardines/${encodeURIComponent(idJardin)}/reportes`,
    { query: { ...periodo } },
  );
}

// --- Rúbrica / ruta de referencia ---

/** GET /ruta-niveles — rúbrica/ruta de referencia. */
export function obtenerRutaNiveles(): Promise<NivelRuta[]> {
  return request<NivelRuta[]>("/ruta-niveles");
}

// --- Salud ---

/** GET /health — salud para API Gateway / demo. */
export function obtenerSalud(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}
