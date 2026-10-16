// Tipos del contrato REST (espejo de los modelos de dominio del backend, Módulo A).
// El cliente NO contiene lógica de negocio: solo describe las formas de datos
// que viajan por la API REST (Requirement 9.6).

export type Rol = "educadora" | "directora";

export type FormatoCaptura = "texto" | "audio" | "foto" | "video";

export type Dominio =
  | "identidad_y_autonomia"
  | "convivencia_y_ciudadania"
  | "corporalidad_y_movimiento"
  | "lenguaje_verbal"
  | "exploracion_del_entorno";

export type DecisionNivel = "avanzar" | "mantener" | "retroceder";

export type DecisionEducadora = "acepto" | "rechazo" | "ajusto";

export type EstadoBitacora = "borrador" | "aprobada";

export interface Nino {
  id_nino: string;
  sala: string;
  tramo?: string;
  id_jardin?: string;
}

export interface NivelRuta {
  nivel: number;
  dominio: Dominio;
  descriptor: string;
}

export interface Manifestacion {
  id_manifestacion: string;
  nivel: number;
  dominio: Dominio;
  descripcion: string;
}

export interface ClasificacionPropuesta {
  nivel_estimado: number;
  dominios: Dominio[];
  manifestaciones: string[];
  confianza_baja: boolean;
}

export interface Observacion {
  id_observacion: string;
  id_nino: string;
  formato_captura: FormatoCaptura;
  texto?: string;
  fecha: string;
  clasificacion?: ClasificacionPropuesta;
  pendiente_clasificacion_manual?: boolean;
}

export interface FichaNino {
  nino: Nino;
  observaciones: Observacion[];
}

export interface Bitacora {
  id_bitacora: string;
  id_nino: string;
  periodo_inicio: string;
  periodo_fin: string;
  contenido: string;
  estado: EstadoBitacora;
  citas: string[];
}

export interface Recomendacion {
  id_recomendacion: string;
  id_nino: string;
  tramo: string;
  nucleo: string;
  nivel_actual: number;
  decision: DecisionNivel;
  argumento: string;
  version_rubrica: string;
  datos_insuficientes?: boolean;
  decision_educadora?: DecisionEducadora;
}

export interface ReporteDireccion {
  id_jardin: string;
  periodo_inicio: string;
  periodo_fin: string;
  subieron: number;
  mantuvieron: number;
  bajaron: number;
  distribucion_por_sala: Record<string, Record<string, number>>;
  distribucion_por_dominio: Record<string, Record<string, number>>;
  total_observaciones: number;
  total_bitacoras: number;
  alertas_retroceso: string[];
  alertas_inactividad: string[];
  kpi_tiempo_ahorrado_horas: number;
  resumen_ejecutivo?: string;
}

export interface HealthStatus {
  status: string;
}

// --- Cuerpos de petición (payloads) ---

export interface ConfirmarClasificacionBody {
  nivel: number;
  dominios: Dominio[];
  manifestaciones: string[];
}

export interface GenerarBitacoraBody {
  periodo_inicio: string;
  periodo_fin: string;
}

export interface EditarBitacoraBody {
  contenido?: string;
  estado?: EstadoBitacora;
}

export interface DecisionRecomendacionBody {
  decision_educadora: DecisionEducadora;
  nivel_ajustado?: number;
}

export interface PeriodoReporte {
  periodo_inicio: string;
  periodo_fin: string;
}
