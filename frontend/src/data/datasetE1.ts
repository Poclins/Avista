import { Parvulo, Observacion, BitacoraQuincenal, RecomendacionNivel, ReporteDireccion } from '../types/avista';

export const JARDIN_ACTUAL = {
  id: 'JAR-0009',
  nombre: 'Jardín Infantil Los Copihues',
  direccion: 'Calle Las Camelias 412, San Bernardo',
  region: 'Región Metropolitana',
  institucion: 'Fundación Integra',
  salasDisponibles: ['SG-A', 'SG-B', 'SC-1']
};

export const SALA_ACTUAL = {
  codigo: 'SG-A',
  nombre: 'Sala Grupo A · Nivel Medio Menor',
  capacidad: 20,
  inscritos: 19,
  educadora_a_cargo: 'Tía Marcela Valenzuela (Educadora Guía)',
  tecnico_apoyo: 'Tía Carolina Fuentes (Asistente de Párvulos)'
};

export const PARVULOS_DATASET_E1: Parvulo[] = [
  {
    id: 'NI-1001',
    alias_pedagogico: 'Párvulo NI-1001 (Lucas M.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 29,
    genero_seudonimo: 'M',
    total_observaciones: 6,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-emerald-600'
  },
  {
    id: 'NI-1002',
    alias_pedagogico: 'Párvulo NI-1002 (Martina S.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 31,
    genero_seudonimo: 'F',
    total_observaciones: 7,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-indigo-600'
  },
  {
    id: 'NI-1003',
    alias_pedagogico: 'Párvulo NI-1003 (Agustín P.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 27,
    genero_seudonimo: 'M',
    total_observaciones: 4,
    estado_cobertura: 'adecuado',
    fecha_ingreso: '2026-03-15',
    proxima_revision: '2026-11-16',
    avatar_color: 'bg-amber-600'
  },
  {
    id: 'NI-1004',
    alias_pedagogico: 'Párvulo NI-1004 (Sofía B.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 33,
    genero_seudonimo: 'F',
    total_observaciones: 8,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-rose-600'
  },
  {
    id: 'NI-1005',
    alias_pedagogico: 'Párvulo NI-1005 (Mateo V.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 25,
    genero_seudonimo: 'M',
    total_observaciones: 2,
    estado_cobertura: 'pendiente',
    fecha_ingreso: '2026-04-01',
    proxima_revision: '2026-11-12',
    avatar_color: 'bg-amber-700'
  },
  {
    id: 'NI-1006',
    alias_pedagogico: 'Párvulo NI-1006 (Emilia R.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 30,
    genero_seudonimo: 'F',
    total_observaciones: 5,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-teal-600'
  },
  {
    id: 'NI-1007',
    alias_pedagogico: 'Párvulo NI-1007 (Joaquín G.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 28,
    genero_seudonimo: 'M',
    total_observaciones: 5,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-cyan-600'
  },
  {
    id: 'NI-1008',
    alias_pedagogico: 'Párvulo NI-1008 (Catalina C.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 34,
    genero_seudonimo: 'F',
    total_observaciones: 7,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-purple-600'
  },
  {
    id: 'NI-1009',
    alias_pedagogico: 'Párvulo NI-1009 (Tomás F.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 26,
    genero_seudonimo: 'M',
    total_observaciones: 3,
    estado_cobertura: 'adecuado',
    fecha_ingreso: '2026-03-20',
    proxima_revision: '2026-11-18',
    avatar_color: 'bg-blue-600'
  },
  {
    id: 'NI-1010',
    alias_pedagogico: 'Párvulo NI-1010 (Francisca D.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 32,
    genero_seudonimo: 'F',
    total_observaciones: 6,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-pink-600'
  },
  {
    id: 'NI-1011',
    alias_pedagogico: 'Párvulo NI-1011 (Benjamín T.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 31,
    genero_seudonimo: 'M',
    total_observaciones: 5,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-emerald-700'
  },
  {
    id: 'NI-1012',
    alias_pedagogico: 'Párvulo NI-1012 (Isidora M.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 29,
    genero_seudonimo: 'F',
    total_observaciones: 4,
    estado_cobertura: 'adecuado',
    fecha_ingreso: '2026-03-10',
    proxima_revision: '2026-11-19',
    avatar_color: 'bg-violet-600'
  },
  {
    id: 'NI-1013',
    alias_pedagogico: 'Párvulo NI-1013 (Vicente N.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 28,
    genero_seudonimo: 'M',
    total_observaciones: 6,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-sky-600'
  },
  {
    id: 'NI-1014',
    alias_pedagogico: 'Párvulo NI-1014 (Ignacia Z.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 35,
    genero_seudonimo: 'F',
    total_observaciones: 7,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-fuchsia-600'
  },
  {
    id: 'NI-1015',
    alias_pedagogico: 'Párvulo NI-1015 (Gaspar L.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 27,
    genero_seudonimo: 'M',
    total_observaciones: 1,
    estado_cobertura: 'pendiente',
    fecha_ingreso: '2026-04-10',
    proxima_revision: '2026-11-11',
    avatar_color: 'bg-rose-700'
  },
  {
    id: 'NI-1016',
    alias_pedagogico: 'Párvulo NI-1016 (Florencia K.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 30,
    genero_seudonimo: 'F',
    total_observaciones: 5,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-teal-700'
  },
  {
    id: 'NI-1017',
    alias_pedagogico: 'Párvulo NI-1017 (Damián O.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 29,
    genero_seudonimo: 'M',
    total_observaciones: 4,
    estado_cobertura: 'adecuado',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-17',
    avatar_color: 'bg-amber-800'
  },
  {
    id: 'NI-1018',
    alias_pedagogico: 'Párvulo NI-1018 (Amanda H.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 32,
    genero_seudonimo: 'F',
    total_observaciones: 5,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-emerald-800'
  },
  {
    id: 'NI-1019',
    alias_pedagogico: 'Párvulo NI-1019 (Maximiliano E.)',
    sala: 'SG-A',
    jardin_id: 'JAR-0009',
    jardin_nombre: 'Jardín Infantil Los Copihues',
    nivel_actual: 'Medio Menor (24 - 36 meses)',
    tramo: 'tramo_2_medio',
    edad_meses: 33,
    genero_seudonimo: 'M',
    total_observaciones: 6,
    estado_cobertura: 'optimo',
    fecha_ingreso: '2026-03-02',
    proxima_revision: '2026-11-15',
    avatar_color: 'bg-slate-700'
  }
];

export const OBSERVACIONES_INICIALES: Observacion[] = [
  {
    id: 'OBS-001',
    id_nino: 'NI-1001',
    fecha: '2026-11-04',
    hora: '10:35',
    formato: 'nota_escrita',
    texto_crudo: 'Lucas logra apilar 7 bloques de madera sin que se caigan en el rincón de construcción. Al final aplaude y le muestra a su compañero.',
    texto_anonimizado: '[NI-1001] logra apilar 7 bloques de madera sin que se caigan en el rincón de construcción. Al final aplaude y le muestra a su compañero.',
    ambito: 'interaccion_entorno',
    nucleo: 'pensamiento_matematico',
    indicador_logro: 'Construcción y coordinación óculo-manual de estructuras estables',
    nivel_logrado: 'consolidado',
    educadora_responsable: 'Tía Marcela',
    validado_por_educadora: true,
    tags: ['bloques', 'motricidad fina', 'autonomía']
  },
  {
    id: 'OBS-002',
    id_nino: 'NI-1001',
    fecha: '2026-11-06',
    hora: '11:15',
    formato: 'audio_voz',
    duracion_audio: '0:34 min',
    texto_crudo: 'Audio de sala: Durante el patio techado, Lucas invitó espontáneamente a Tomás a compartir la carretilla azul diciendo "tú empujas y yo subo las piñas". Hubo alternancia pacífica de roles durante 15 minutos.',
    texto_anonimizado: 'Durante el patio techado, [NI-1001] invitó espontáneamente a [NI-1009] a compartir la carretilla azul diciendo "tú empujas y yo subo las piñas". Hubo alternancia pacífica de roles durante 15 minutos.',
    ambito: 'desarrollo_personal',
    nucleo: 'convivencia_ciudadania',
    indicador_logro: 'Interacción colaborativa y resolución pacífica en juego reglado',
    nivel_logrado: 'consolidado',
    educadora_responsable: 'Tía Marcela',
    validado_por_educadora: true,
    tags: ['juego cooperativo', 'lenguaje verbal', 'empatía']
  },
  {
    id: 'OBS-003',
    id_nino: 'NI-1001',
    fecha: '2026-11-07',
    hora: '14:20',
    formato: 'foto_apunte',
    adjunto_url: '/images/pedagogical_notes_capture_1794283481387.jpg',
    texto_crudo: 'Foto cuaderno educadora: Clasificó hojas secas del patio según tamaño (grandes y chicas) en dos bandejas plásticas. Nombró los colores café y amarillo.',
    texto_anonimizado: 'Clasificó hojas secas del patio según tamaño (grandes y chicas) en dos bandejas plásticas. Nombró los colores café y amarillo.',
    ambito: 'interaccion_entorno',
    nucleo: 'exploracion_natural',
    indicador_logro: 'Clasificación de elementos naturales según atributos perceptuales',
    nivel_logrado: 'consolidado',
    educadora_responsable: 'Tía Carolina',
    validado_por_educadora: true,
    tags: ['entorno natural', 'clasificación', 'vocabulario']
  },
  {
    id: 'OBS-004',
    id_nino: 'NI-1002',
    fecha: '2026-11-03',
    hora: '09:40',
    formato: 'video_registro',
    duracion_audio: '0:45 min',
    texto_crudo: 'Registro en video de actividad plástica: Martina sostiene el pincel grueso con prensión trípode incipiente, combinando témpera azul y amarilla para descubrir el verde.',
    texto_anonimizado: 'Registro en video de actividad plástica: [NI-1002] sostiene el pincel grueso con prensión trípode incipiente, combinando témpera azul y amarilla para descubrir el verde.',
    ambito: 'comunicacion_integral',
    nucleo: 'lenguajes_artisticos',
    indicador_logro: 'Exploración de mezclas de color y motricidad gráfica',
    nivel_logrado: 'consolidado',
    educadora_responsable: 'Tía Marcela',
    validado_por_educadora: true,
    tags: ['pintura', 'creatividad', 'prensión']
  },
  {
    id: 'OBS-005',
    id_nino: 'NI-1002',
    fecha: '2026-11-05',
    hora: '12:10',
    formato: 'nota_escrita',
    texto_crudo: 'En la hora de almuerzo, sirve su vaso con jarra plástica pequeña con mínima ayuda de la tía y pide verbalmente "más agua por favor".',
    texto_anonimizado: 'En la hora de almuerzo, sirve su vaso con jarra plástica pequeña con mínima ayuda de la tía y pide verbalmente "más agua por favor".',
    ambito: 'desarrollo_personal',
    nucleo: 'identidad_autonomia',
    indicador_logro: 'Autonomía en hábitos de alimentación y modales de convivencia',
    nivel_logrado: 'consolidado',
    educadora_responsable: 'Tía Marcela',
    validado_por_educadora: true,
    tags: ['autonomía', 'alimentación', 'lenguaje cortés']
  },
  {
    id: 'OBS-006',
    id_nino: 'NI-1005',
    fecha: '2026-11-02',
    hora: '10:00',
    formato: 'nota_escrita',
    texto_crudo: 'Mateo presenta dificultad al separarse de su cuidador en la mañana, llanto durante 20 minutos. Se calma con canción de cuna y mantita de apego.',
    texto_anonimizado: '[NI-1005] presenta dificultad al separarse de su cuidador en la mañana, llanto durante 20 minutos. Se calma con canción de cuna y mantita de apego.',
    ambito: 'desarrollo_personal',
    nucleo: 'identidad_autonomia',
    indicador_logro: 'Proceso de apego seguro y adaptación a la jornada de sala cuna/medio',
    nivel_logrado: 'en_inicio',
    educadora_responsable: 'Tía Marcela',
    validado_por_educadora: true,
    tags: ['adaptación', 'regulación emocional', 'apego']
  },
  {
    id: 'OBS-007',
    id_nino: 'NI-1005',
    fecha: '2026-11-05',
    hora: '11:30',
    formato: 'audio_voz',
    duracion_audio: '0:28 min',
    texto_crudo: 'Audio tía: Durante el juego libre en el patio, Mateo observa a otros niños jugar con pelotas pero no se acerca. Al ofrecerle una pelota prefiere jugar solo cerca del rincón de libros.',
    texto_anonimizado: 'Durante el juego libre en el patio, [NI-1005] observa a otros niños jugar con pelotas pero no se acerca. Al ofrecerle una pelota prefiere jugar solo cerca del rincón de libros.',
    ambito: 'desarrollo_personal',
    nucleo: 'convivencia_ciudadania',
    indicador_logro: 'Integración en actividades grupales de patio',
    nivel_logrado: 'en_inicio',
    educadora_responsable: 'Tía Marcela',
    validado_por_educadora: true,
    tags: ['socialización', 'juego solitario', 'alerta de apoyo']
  },
  {
    id: 'OBS-008',
    id_nino: 'NI-1004',
    fecha: '2026-11-05',
    hora: '10:15',
    formato: 'nota_escrita',
    texto_crudo: 'Sofía relata con oraciones completas de 5 palabras lo que soñó: "El gato amarillo comió pescado en el techo". Responde a preguntas abiertas sobre el relato.',
    texto_anonimizado: '[NI-1004] relata con oraciones completas de 5 palabras lo que soñó: "El gato amarillo comió pescado en el techo". Responde a preguntas abiertas sobre el relato.',
    ambito: 'comunicacion_integral',
    nucleo: 'lenguaje_verbal',
    indicador_logro: 'Estructuración sintáctica de relatos orales y comprensión lectora/narrativa',
    nivel_logrado: 'consolidado',
    educadora_responsable: 'Tía Marcela',
    validado_por_educadora: true,
    tags: ['lenguaje verbal', 'narración', 'oraciones completas']
  }
];

export const BITACORAS_INICIALES: BitacoraQuincenal[] = [
  {
    id: 'BIT-001',
    id_nino: 'NI-1001',
    periodo: 'Quincena 1 · Noviembre 2026',
    fecha_corte: '2026-11-08',
    resumen_ejecutivo: 'El párvulo [NI-1001] evidencia un período de consolidación sobresaliente en sus habilidades socioemocionales y cognitivas. Demuestra una marcada autonomía en la selección de actividades de exploración, altos niveles de concentración en juego constructivo y una espontánea iniciativa para compartir y negociar turnos con sus pares.',
    desarrollo_personal_social: 'Muestra seguridad afectiva en la rutina diaria. En convivencia, destaca su capacidad de invitar a pares a juegos compartidos (evidenciado en el juego de la carretilla) con regulación asertiva de turnos y respeto de normas de sala.',
    comunicacion_integral: 'Su lenguaje verbal se manifiesta con vocabulario variado, utilizando frases propositivas para coordinar acciones con compañeros. Comprende consignas de doble instrucción sin dificultad.',
    interaccion_entorno: 'Notable progresión en pensamiento matemático: apila hasta 7 bloques demostrando ajuste postural y equilibrio. En exploración natural, clasifica autónomamente elementos por criterio de tamaño y color.',
    estrategia_aula_sugerida: 'Potenciar su rol como mediador en mesas de trabajo cooperativo y desafiarlo con patrones seriados de 3 elementos (grande-mediano-pequeño).',
    observaciones_computadas: 6,
    estado: 'en_revision',
    firmado_por: 'Tía Marcela Valenzuela'
  },
  {
    id: 'BIT-002',
    id_nino: 'NI-1002',
    periodo: 'Quincena 1 · Noviembre 2026',
    fecha_corte: '2026-11-08',
    resumen_ejecutivo: 'La párvula [NI-1002] sostiene un desarrollo armónico y progresivo. Sobresale en lenguajes artísticos mediante la experimentación de texturas y mezclas cromáticas, acompañado de una maduración sostenida en hábitos de autocuidado e higiene.',
    desarrollo_personal_social: 'Realiza el lavado de manos y servido de líquidos con mínima supervisión adulta, demostrando satisfacción por sus logros cotidianos.',
    comunicacion_integral: 'Expresa sus preferencias artísticas con fluidez corporal y gráfica. Explora mezclas secundarias de témpera asociándolas a elementos cotidianos (verde = pasto).',
    interaccion_entorno: 'Reconoce relaciones espaciales básicas (arriba/abajo, adentro/afuera) durante el ordenamiento guiado del material pedagógico.',
    estrategia_aula_sugerida: 'Facilitar soportes de papel de gran formato en caballetes verticales para fortalecer el tono muscular de tren superior y muñeca.',
    observaciones_computadas: 7,
    estado: 'aprobada',
    fecha_aprobacion: '2026-11-08',
    firmado_por: 'Tía Marcela Valenzuela'
  },
  {
    id: 'BIT-003',
    id_nino: 'NI-1005',
    periodo: 'Quincena 1 · Noviembre 2026',
    fecha_corte: '2026-11-08',
    resumen_ejecutivo: 'El párvulo [NI-1005] cursa una etapa sensible de adaptación al grupo de pares. Aunque responde favorablemente a la contención afectiva de las educadoras guías, requiere andamiaje intencionado para transitar del juego paralelo o solitario a la interacción activa con pares.',
    desarrollo_personal_social: 'Durante el inicio de la jornada manifiesta apego intenso y episodios de angustia de separación que ceden con rutinas de acogida personalizada y objetos transicionales. En patio se mantiene en la periferia observando a sus pares.',
    comunicacion_integral: 'Comunica sus requerimientos principalmente mediante gestos y palabras aisladas dirigidas a la educadora de referencia.',
    interaccion_entorno: 'Muestra interés sostenido por libros ilustrados y texturas suaves, dedicando lapsos prolongados a pasar páginas con cuidado.',
    estrategia_aula_sugerida: 'Implementar bienvenida escalonada con su técnico de apego y organizar duetos lúdicos en rincones sensoriales con un par tranquilo (p.ej. [NI-1006]).',
    observaciones_computadas: 2,
    estado: 'borrador_ia'
  }
];

export const RECOMENDACIONES_INICIALES: RecomendacionNivel[] = [
  {
    id: 'REC-001',
    id_nino: 'NI-1001',
    fecha_generacion: '2026-11-08',
    tramo_actual: 'tramo_2_medio',
    decision_propuesta: 'avanzar',
    confianza_rubrica: 0.94,
    fundamentacion_pedagogica: 'El párvulo cumple con creces los indicadores del Tramo 2 (Nivel Medio Menor) en los 3 ámbitos curriculares. Sus habilidades de autorregulación, formulación de oraciones complejas y clasificación bifactorial corresponden a logros esperados para inicio de Medio Mayor / Tramo 2 consolidado.',
    evidencias: [
      {
        observacion_id: 'OBS-001',
        fecha: '2026-11-04',
        texto_cita: 'Logra apilar 7 bloques de madera con estabilidad y muestra orgullo por su logro.',
        nucleo: 'pensamiento_matematico',
        relevancia: 'Hito motor y cognitivo de alta precisión para 29 meses.'
      },
      {
        observacion_id: 'OBS-002',
        fecha: '2026-11-06',
        texto_cita: 'Invita espontáneamente a par ("tú empujas y yo subo las piñas") y alterna turnos pacíficamente por 15 min.',
        nucleo: 'convivencia_ciudadania',
        relevancia: 'Juego cooperativo estructurado, supera el nivel asociativo simple.'
      },
      {
        observacion_id: 'OBS-003',
        fecha: '2026-11-07',
        texto_cita: 'Clasificó hojas secas del patio según tamaño (grandes y chicas) e identificó colores café y amarillo.',
        nucleo: 'exploracion_natural',
        relevancia: 'Criterio taxonómico dual en elementos del medio ambiente.'
      }
    ],
    estado_educadora: 'confirmada',
    nota_educadora: 'Completamente de acuerdo. Lucas muestra madurez socioafectiva notable para sus 29 meses. Se iniciará transición gradual a experiencias de Medio Mayor.',
    fecha_decision: '2026-11-08'
  },
  {
    id: 'REC-002',
    id_nino: 'NI-1002',
    fecha_generacion: '2026-11-08',
    tramo_actual: 'tramo_2_medio',
    decision_propuesta: 'mantener',
    confianza_rubrica: 0.91,
    fundamentacion_pedagogica: 'La párvula presenta un desarrollo armónico y plenamente afianzado dentro de las expectativas del tramo Medio Menor. Se recomienda mantener el tramo para consolidar la prensión trípode y la autorregulación durante transiciones colectivas de sala.',
    evidencias: [
      {
        observacion_id: 'OBS-004',
        fecha: '2026-11-03',
        texto_cita: 'Prensión trípode incipiente en actividades plásticas y formulación de mezclas de color.',
        nucleo: 'lenguajes_artisticos',
        relevancia: 'Destreza motriz fina en proceso favorable de afirmación.'
      },
      {
        observacion_id: 'OBS-005',
        fecha: '2026-11-05',
        texto_cita: 'Sirve agua en vaso con jarra con mínima ayuda y pide "más agua por favor".',
        nucleo: 'identidad_autonomia',
        relevancia: 'Autonomía de autocuidado acorde a estándar del nivel.'
      }
    ],
    estado_educadora: 'confirmada',
    nota_educadora: 'Excelente. Mantener en consolidación con foco en prensión fina.',
    fecha_decision: '2026-11-08'
  },
  {
    id: 'REC-003',
    id_nino: 'NI-1005',
    fecha_generacion: '2026-11-08',
    tramo_actual: 'tramo_2_medio',
    decision_propuesta: 'reforzar',
    confianza_rubrica: 0.88,
    fundamentacion_pedagogica: 'Se sugiere activar plan de acompañamiento focalizado en Convivencia e Identidad. Las evidencias registran baja participación en dinámicas grupales y llanto prolongado en transiciones, requiriendo un plan de andamiaje socioemocional individualizado antes de exigir hitos curriculares avanzados.',
    evidencias: [
      {
        observacion_id: 'OBS-006',
        fecha: '2026-11-02',
        texto_cita: 'Dificultad en despedida matinal con 20 min de desregulación; uso indispensable de objeto transicional.',
        nucleo: 'identidad_autonomia',
        relevancia: 'Alerta temprana de necesidad de fortalecimiento del apego seguro institucional.'
      },
      {
        observacion_id: 'OBS-007',
        fecha: '2026-11-05',
        texto_cita: 'Observa el juego de pares desde la distancia sin integrarse activamente en el patio.',
        nucleo: 'convivencia_ciudadania',
        relevancia: 'Requiere puente pedagógico afectivo para el juego cooperativo.'
      }
    ],
    estado_educadora: 'pendiente'
  }
];

export const REPORTE_DIRECCION_INICIAL: ReporteDireccion = {
  jardin_id: 'JAR-0009',
  jardin_nombre: 'Jardín Infantil Los Copihues',
  sala: 'SG-A (Medio Menor)',
  total_ninos: 19,
  cobertura_observaciones_pct: 84.2, // 16 de 19 con cobertura adecuada u óptima
  observaciones_totales_quincena: 98,
  horas_semanales_ahorradas_estimadas: 3.8, // Por educadora de sala
  distribucion_ambitos: {
    desarrollo_personal: 42,
    comunicacion_integral: 31,
    interaccion_entorno: 25
  },
  distribucion_recomendaciones: {
    avanzar: 4,
    mantener: 13,
    reforzar: 2
  },
  alertas_atencion_temprana: [
    {
      id_nino: 'NI-1005',
      motivo: 'Regulación emocional en separación matinal y juego solitario en patio.',
      prioridad: 'alta'
    },
    {
      id_nino: 'NI-1015',
      motivo: 'Solo 1 observación en la quincena; riesgo de sub-registro por inasistencias.',
      prioridad: 'media'
    }
  ]
};
