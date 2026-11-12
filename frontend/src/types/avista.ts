export type AmbitoCurricular = 
  | 'desarrollo_personal' 
  | 'comunicacion_integral' 
  | 'interaccion_entorno';

export type NucleoCurricular =
  | 'identidad_autonomia'
  | 'convivencia_ciudadania'
  | 'corporalidad_movimiento'
  | 'lenguaje_verbal'
  | 'lenguajes_artisticos'
  | 'exploracion_natural'
  | 'comprension_sociocultural'
  | 'pensamiento_matematico';

export type TramoNivel = 'tramo_1_salacuna' | 'tramo_2_medio' | 'tramo_3_transicion';

export type TipoFormato = 'nota_escrita' | 'audio_voz' | 'foto_apunte' | 'video_registro';

export type EstadoBitacora = 'borrador_ia' | 'en_revision' | 'aprobada' | 'rechazada';

export type DecisionNivel = 'avanzar' | 'mantener' | 'reforzar';

export interface Observacion {
  id: string;
  id_nino: string;
  fecha: string;
  hora: string;
  formato: TipoFormato;
  texto_crudo: string;
  texto_anonimizado: string;
  ambito: AmbitoCurricular;
  nucleo: NucleoCurricular;
  indicador_logro: string;
  nivel_logrado: 'en_inicio' | 'en_desarrollo' | 'consolidado';
  adjunto_url?: string;
  duracion_audio?: string;
  educadora_responsable: string;
  validado_por_educadora: boolean;
  tags: string[];
}

export interface Parvulo {
  id: string; // Seudónimo e.g. NI-2841
  alias_pedagogico: string; // "Párvulo Lucas M."
  sala: string; // e.g. "SG-A"
  jardin_id: string; // e.g. "JAR-0009"
  jardin_nombre: string; // "Jardín Infantil Los Copihues"
  nivel_actual: string; // "Medio Menor (24 - 36 meses)"
  tramo: TramoNivel;
  edad_meses: number;
  genero_seudonimo: 'M' | 'F';
  total_observaciones: number;
  estado_cobertura: 'optimo' | 'adecuado' | 'pendiente';
  fecha_ingreso: string;
  proxima_revision: string;
  avatar_color: string;
}

export interface EvidenciaCitada {
  observacion_id: string;
  fecha: string;
  texto_cita: string;
  nucleo: NucleoCurricular;
  relevancia: string;
}

export interface RecomendacionNivel {
  id: string;
  id_nino: string;
  fecha_generacion: string;
  tramo_actual: TramoNivel;
  decision_propuesta: DecisionNivel;
  confianza_rubrica: number; // 0.0 - 1.0
  fundamentacion_pedagogica: string;
  evidencias: EvidenciaCitada[];
  estado_educadora: 'pendiente' | 'confirmada' | 'ajustada' | 'rechazada';
  nota_educadora?: string;
  fecha_decision?: string;
}

export interface BitacoraQuincenal {
  id: string;
  id_nino: string;
  periodo: string; // "Quincena 1 - Octubre 2026"
  fecha_corte: string;
  resumen_ejecutivo: string;
  desarrollo_personal_social: string;
  comunicacion_integral: string;
  interaccion_entorno: string;
  estrategia_aula_sugerida: string;
  observaciones_computadas: number;
  estado: EstadoBitacora;
  fecha_aprobacion?: string;
  firmado_por?: string;
}

export interface ReporteDireccion {
  jardin_id: string;
  jardin_nombre: string;
  sala: string;
  total_ninos: number;
  cobertura_observaciones_pct: number;
  observaciones_totales_quincena: number;
  horas_semanales_ahorradas_estimadas: number;
  distribucion_ambitos: {
    desarrollo_personal: number;
    comunicacion_integral: number;
    interaccion_entorno: number;
  };
  distribucion_recomendaciones: {
    avanzar: number;
    mantener: number;
    reforzar: number;
  };
  alertas_atencion_temprana: {
    id_nino: string;
    motivo: string;
    prioridad: 'alta' | 'media';
  }[];
}

// 1. Radar de Zonas Ciegas
export interface ZonaCiegaParvulo {
  id_nino: string;
  alias_pedagogico: string;
  total_observaciones: number;
  ambitos_vacios: AmbitoCurricular[];
  nucleos_faltantes: NucleoCurricular[];
  dias_sin_registro: number;
  nivel_urgencia: 'alta' | 'media' | 'baja';
  sugerencia_aula: string;
}

// 2. Receta de Andamiaje Lúdico Situado
export interface RecetaAndamiaje {
  id: string;
  id_nino: string;
  alias_pedagogico: string;
  desafio_detectado: string;
  ambito: AmbitoCurricular;
  nucleo: NucleoCurricular;
  titulo_actividad: string;
  materiales_integra: string[];
  duracion_sugerida: string;
  momento_jornada: 'patio_techado' | 'rincon_juego' | 'circulo_bienvenida' | 'colacion_higiene';
  pasos_mediacion: string[];
  pregunta_gatilladora: string;
  criterio_exito_observable: string;
  parvulo_companero_sugerido?: string;
}

// 5. Análisis Multimodal de Garabateo y Dibujo Infantil
export interface AnalisisGarabato {
  id: string;
  imagen_url: string;
  titulo_obra: string;
  estadio_lowenfeld: 'garabateo_desordenado' | 'garabateo_longitudinal' | 'garabateo_circular' | 'figura_humana_incipiente' | 'exploracion_cromatica';
  estadio_nombre_comun: string;
  rango_etario_tipico: string;
  prension_motriz_observada: string;
  distribucion_espacial: string;
  intencionalidad_simbolica: string;
  indicador_bcep_asociado: string;
  observacion_sugerida: string;
}

// 6. Banco Colaborativo de Experiencias Semánticas (pgvector)
export interface ExperienciaIntegra {
  id: string;
  titulo: string;
  region: string;
  jardin_origen: string;
  desafio_clave: string;
  solucion_probada: string;
  materiales_usados: string[];
  resultado_observado: string;
  ambito: AmbitoCurricular;
  nucleo: NucleoCurricular;
  tags: string[];
  votos_utilidad: number;
  similitud_semantica?: number; // 0.0 a 1.0 (vector match)
}
