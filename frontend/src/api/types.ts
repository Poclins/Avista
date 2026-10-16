// Tipos del contrato REST - ESPEJO EXACTO de los schemas del backend
// (backend/app/api/schemas.py) y los enums de dominio (domain/models.py).

// Roles de navegacion del frontend (UI); no es el enum Rol del dataset.
export type RolUI = "educadora" | "directora";

export type FormatoCaptura = "texto" | "audio" | "foto" | "video";

export type Dominio =
  | "cognitivo"
  | "lenguaje_comunicacion"
  | "motor_fino"
  | "motor_grueso"
  | "socioemocional";

export type DecisionNivel = "AVANZAR" | "MANTENER" | "RETROCEDER";

export type EstadoBitacora = "borrador" | "aprobada";

export interface Nino {
  id_nino: string;
  id_jardin: string;
  fecha_nacimiento: string;
  sexo_registrado: string;
  sala_grupo: string;
  fecha_ingreso: string;
}

export interface Clasificacion {
  nivel_estimado: number | null;
  dominios: Dominio[];
  manifestaciones: string[];
  confianza: number;
  pendiente_clasificacion_manual: boolean;
}

export interface Observacion {
  id_observacion: string;
  id_nino: string;
  id_educadora: string;
  fecha_observacion: string;
  formato_captura: FormatoCaptura;
  nivel_estimado: number | null;
  nota_breve: string;
  duplicado: boolean;
  clasificacion: Clasificacion | null;
}

export interface FichaNino {
  nino: Nino;
  trayectoria: Observacion[];
}

export interface Bitacora {
  id_bitacora: string;
  id_nino: string;
  id_educadora: string;
  periodo: string;
  texto_generado: string;
  estado: EstadoBitacora;
  fecha: string;
}

export interface Recomendacion {
  id_recomendacion: string | null;
  id_nino: string;
  id_educadora: string;
  decision: DecisionNivel | null;
  tramo: string | null;
  nucleo: string | null;
  nivel_actual: number | null;
  score: number | null;
  conductas_observables_cubiertas: string[];
  conductas_observables_pendientes: string[];
  evidencia: string[];
  version_rubrica: string | null;
  argumento_ia: string;
  argumento_disponible: boolean;
  datos_insuficientes: boolean;
  observaciones_registradas: number;
  observaciones_faltantes: number;
  persistida: boolean;
}

export interface RecomendacionDecision {
  id_recomendacion: string;
  id_nino: string;
  id_educadora: string;
  decision: DecisionNivel;
  decision_educadora: string | null;
}

export interface ReporteDireccion {
  id_reporte: string;
  id_jardin: string;
  periodo: string;
  metricas: Record<string, unknown>;
  resumen_ejecutivo: string;
  resumen_disponible: boolean;
  fecha: string;
}

export interface NivelRuta {
  nivel: number;
  nombre_nivel: string;
  edad_min_meses: number;
  edad_max_meses: number;
  dominios: Dominio[];
  descripcion: string;
}

export interface RutaNiveles {
  niveles: NivelRuta[];
  version_rubrica: string | null;
}

export interface HealthStatus {
  status: string;
  app: string;
  use_mocks: boolean;
  environment: string;
}

export interface ObservacionTextoBody {
  id_educadora: string;
  texto: string;
  fecha_observacion?: string;
}

export interface ConfirmarClasificacionBody {
  accion: "confirmar" | "corregir";
  nivel_estimado?: number | null;
  dominios: Dominio[];
  manifestaciones: string[];
}

export interface GenerarBitacoraBody {
  id_educadora: string;
  fecha_inicio: string;
  fecha_fin: string;
}

export interface EditarBitacoraBody {
  accion: "editar" | "aprobar";
  texto?: string;
}

export interface GenerarRecomendacionBody {
  id_educadora: string;
  nivel_actual: number;
  nucleo?: string;
}

export interface DecisionRecomendacionBody {
  decision_educadora: string;
}

export interface PeriodoReporte {
  fecha_inicio: string;
  fecha_fin: string;
}
