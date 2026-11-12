import { GoogleGenAI } from '@google/genai';
import { AmbitoCurricular, NucleoCurricular, Observacion, Parvulo, BitacoraQuincenal, RecomendacionNivel, TipoFormato, EvidenciaCitada } from '../types/avista';
import { sanitizePedagogicalNote } from './privacyService';

export type ModoEjecucion = 'local_e1' | 'cloud_ia';

class AiService {
  private mode: ModoEjecucion = 'local_e1';
  private geminiClient: GoogleGenAI | null = null;

  constructor() {
    this.initGemini();
  }

  private initGemini() {
    // Verificamos si existe la variable de entorno expuesta en Vite o runtime
    const apiKey = (import.meta as unknown as { env: Record<string, string> }).env?.VITE_GEMINI_API_KEY || 
                   (import.meta as unknown as { env: Record<string, string> }).env?.GEMINI_API_KEY;
    if (apiKey && apiKey !== 'MY_GEMINI_API_KEY') {
      try {
        this.geminiClient = new GoogleGenAI({ apiKey });
      } catch (err) {
        console.warn('No se pudo inicializar Gemini client con la key configurada:', err);
      }
    }
  }

  public getMode(): ModoEjecucion {
    return this.mode;
  }

  public setMode(newMode: ModoEjecucion): void {
    this.mode = newMode;
  }

  public hasLiveGemini(): boolean {
    return !!this.geminiClient;
  }

  /**
   * Clasifica una observación de aula en Ámbito, Núcleo, Indicador y Nivel
   */
  public async classifyObservation(
    textoCrudo: string,
    idNino: string,
    formato: TipoFormato
  ): Promise<{
    textoAnonimizado: string;
    ambito: AmbitoCurricular;
    nucleo: NucleoCurricular;
    indicadorLogro: string;
    nivelLogrado: 'en_inicio' | 'en_desarrollo' | 'consolidado';
    tags: string[];
    advertenciaPrivacidad?: string;
  }> {
    // Paso 1: Filtro estricto de privacidad antes de procesar
    const sanitization = sanitizePedagogicalNote(textoCrudo, idNino);
    const textoAnonimizado = sanitization.sanitizedText;
    const advertenciaPrivacidad = sanitization.wasSanitized
      ? `Se detectaron y protegieron ${sanitization.detectedEntities.length} datos sensibles (${sanitization.detectedEntities.map(d => d.type).join(', ')}) antes del análisis.`
      : undefined;

    // Si está en modo Cloud y hay cliente Gemini disponible
    if (this.mode === 'cloud_ia' && this.geminiClient) {
      try {
        const prompt = `Actúa como un motor de IA pedagógica especializado en las Bases Curriculares de la Educación Parvularia de Chile (Fundación Integra).
Analiza el siguiente registro de observación de aula para el párvulo con seudónimo ${idNino}:
"${textoAnonimizado}"

Responde ESTRICTAMENTE con un objeto JSON válido con los siguientes campos:
{
  "ambito": "desarrollo_personal" | "comunicacion_integral" | "interaccion_entorno",
  "nucleo": "identidad_autonomia" | "convivencia_ciudadania" | "corporalidad_movimiento" | "lenguaje_verbal" | "lenguajes_artisticos" | "exploracion_natural" | "comprension_sociocultural" | "pensamiento_matematico",
  "indicadorLogro": "texto breve del indicador pedagógico observado acorde a BCEP",
  "nivelLogrado": "en_inicio" | "en_desarrollo" | "consolidado",
  "tags": ["tag1", "tag2", "tag3"]
}`;

        const response = await this.geminiClient.models.generateContent({
          model: 'gemini-2.5-flash',
          contents: prompt,
          config: {
            responseMimeType: 'application/json'
          }
        });

        const parsed = JSON.parse(response.text || '{}');
        return {
          textoAnonimizado,
          ambito: parsed.ambito || 'desarrollo_personal',
          nucleo: parsed.nucleo || 'convivencia_ciudadania',
          indicadorLogro: parsed.indicadorLogro || 'Conducta exploratoria en el aula',
          nivelLogrado: parsed.nivelLogrado || 'en_desarrollo',
          tags: parsed.tags || ['observación', 'aula'],
          advertenciaPrivacidad
        };
      } catch (err) {
        console.warn('Error llamando a Gemini, fallback a enchufe local E-1:', err);
      }
    }

    // Enchufe Local determinista (Dataset E-1 heuristic matching)
    return this.classifyLocalHeuristic(textoAnonimizado, advertenciaPrivacidad);
  }

  private classifyLocalHeuristic(
    texto: string, 
    advertenciaPrivacidad?: string
  ): {
    textoAnonimizado: string;
    ambito: AmbitoCurricular;
    nucleo: NucleoCurricular;
    indicadorLogro: string;
    nivelLogrado: 'en_inicio' | 'en_desarrollo' | 'consolidado';
    tags: string[];
    advertenciaPrivacidad?: string;
  } {
    const t = texto.toLowerCase();

    if (t.includes('bloque') || t.includes('apilar') || t.includes('torre') || t.includes('contar') || t.includes('forma') || t.includes('tamaño') || t.includes('número')) {
      return {
        textoAnonimizado: texto,
        ambito: 'interaccion_entorno',
        nucleo: 'pensamiento_matematico',
        indicadorLogro: 'Resolución de desafíos lúdicos y coordinación visomotriz con material estructurado',
        nivelLogrado: t.includes('no logra') || t.includes('dificultad') ? 'en_inicio' : 'consolidado',
        tags: ['construcción', 'pensamiento matemático', 'motricidad'],
        advertenciaPrivacidad
      };
    }

    if (t.includes('pint') || t.includes('dibuj') || t.includes('color') || t.includes('música') || t.includes('témpera') || t.includes('canción') || t.includes('plastilina')) {
      return {
        textoAnonimizado: texto,
        ambito: 'comunicacion_integral',
        nucleo: 'lenguajes_artisticos',
        indicadorLogro: 'Expresión plástica y experimentación sensorial mediante materiales artísticos',
        nivelLogrado: 'consolidado',
        tags: ['arte', 'creatividad', 'exploración sensorial'],
        advertenciaPrivacidad
      };
    }

    if (t.includes('habla') || t.includes('dijo') || t.includes('palabra') || t.includes('frase') || t.includes('relat') || t.includes('cuento') || t.includes('pregunt')) {
      return {
        textoAnonimizado: texto,
        ambito: 'comunicacion_integral',
        nucleo: 'lenguaje_verbal',
        indicadorLogro: 'Estructuración fonológica y verbal en interacciones cotidianas',
        nivelLogrado: 'consolidado',
        tags: ['lenguaje verbal', 'comunicación', 'diálogo'],
        advertenciaPrivacidad
      };
    }

    if (t.includes('llora') || t.includes('llanto') || t.includes('angustia') || t.includes('solo') || t.includes('separación') || t.includes('mamá') || t.includes('despedida')) {
      return {
        textoAnonimizado: texto,
        ambito: 'desarrollo_personal',
        nucleo: 'identidad_autonomia',
        indicadorLogro: 'Autorregulación emocional y adaptación afectiva al espacio institucional',
        nivelLogrado: 'en_inicio',
        tags: ['adaptación', 'socioemocional', 'contención'],
        advertenciaPrivacidad
      };
    }

    if (t.includes('comparte') || t.includes('compañero') || t.includes('amigo') || t.includes('patio') || t.includes('juego') || t.includes('turno')) {
      return {
        textoAnonimizado: texto,
        ambito: 'desarrollo_personal',
        nucleo: 'convivencia_ciudadania',
        indicadorLogro: 'Participación cooperativa y respeto por normas de convivencia en juegos compartidos',
        nivelLogrado: 'consolidado',
        tags: ['convivencia', 'juego cooperativo', 'socialización'],
        advertenciaPrivacidad
      };
    }

    if (t.includes('planta') || t.includes('hoja') || t.includes('bicho') || t.includes('tierra') || t.includes('agua') || t.includes('animal')) {
      return {
        textoAnonimizado: texto,
        ambito: 'interaccion_entorno',
        nucleo: 'exploracion_natural',
        indicadorLogro: 'Curiosidad y exploración guiada del entorno natural y seres vivos',
        nivelLogrado: 'consolidado',
        tags: ['naturaleza', 'exploración', 'medio ambiente'],
        advertenciaPrivacidad
      };
    }

    // Default
    return {
      textoAnonimizado: texto,
      ambito: 'desarrollo_personal',
      nucleo: 'identidad_autonomia',
      indicadorLogro: 'Despliegue de iniciativa personal en las rutinas de la jornada pedagógica',
      nivelLogrado: 'en_desarrollo',
      tags: ['rutina de sala', 'autonomía'],
      advertenciaPrivacidad
    };
  }

  /**
   * Genera borrador quincenal de bitácora integrando las observaciones del período
   */
  public async generateBitacora(
    parvulo: Parvulo,
    observaciones: Observacion[]
  ): Promise<BitacoraQuincenal> {
    const obsText = observaciones
      .map(o => `[${o.fecha}] (${o.nucleo}): ${o.texto_anonimizado}`)
      .join('\n');

    if (this.mode === 'cloud_ia' && this.geminiClient && observaciones.length > 0) {
      try {
        const prompt = `Genera un borrador pedagógico de BITÁCORA QUINCENAL para Fundación Integra (Chile).
Párvulo: ${parvulo.id} (${parvulo.alias_pedagogico}), Nivel: ${parvulo.nivel_actual}, Edad: ${parvulo.edad_meses} meses.
Observaciones registradas en la quincena:
${obsText}

Devuelve un JSON estrictamente con la siguiente estructura:
{
  "resumen_ejecutivo": "párrafo formal sintetizando el progreso global del párvulo",
  "desarrollo_personal_social": "síntesis de avances en autonomía, convivencia y corporalidad",
  "comunicacion_integral": "síntesis de avances en lenguaje verbal y expresiones artísticas",
  "interaccion_entorno": "síntesis de avances en exploración natural y pensamiento lógico",
  "estrategia_aula_sugerida": "recomendación concreta de andamiaje para la educadora en sala"
}`;

        const response = await this.geminiClient.models.generateContent({
          model: 'gemini-2.5-flash',
          contents: prompt,
          config: {
            responseMimeType: 'application/json'
          }
        });

        const parsed = JSON.parse(response.text || '{}');
        return {
          id: `BIT-${Date.now().toString().slice(-4)}`,
          id_nino: parvulo.id,
          periodo: 'Quincena 1 · Noviembre 2026',
          fecha_corte: new Date().toISOString().split('T')[0],
          resumen_ejecutivo: parsed.resumen_ejecutivo || `El párvulo ${parvulo.id} sostiene un desempeño acorde a su nivel en la sala ${parvulo.sala}.`,
          desarrollo_personal_social: parsed.desarrollo_personal_social || 'Consolidación gradual de rutinas de aula y participación.',
          comunicacion_integral: parsed.comunicacion_integral || 'Comunicación asertiva con educadoras y compañeros.',
          interaccion_entorno: parsed.interaccion_entorno || 'Participa en actividades de exploración sensorial del entorno.',
          estrategia_aula_sugerida: parsed.estrategia_aula_sugerida || 'Mantener experiencias guiadas y fomentar trabajo en rincones.',
          observaciones_computadas: observaciones.length,
          estado: 'borrador_ia'
        };
      } catch (err) {
        console.warn('Fallo generación con Gemini, usando motor local:', err);
      }
    }

    // Generador Local pedagógico sintético E-1
    return {
      id: `BIT-${Date.now().toString().slice(-4)}`,
      id_nino: parvulo.id,
      periodo: 'Quincena 1 · Noviembre 2026',
      fecha_corte: new Date().toISOString().split('T')[0],
      resumen_ejecutivo: `Durante la primera quincena de noviembre, el párvulo [${parvulo.id}] ha evidenciado un progreso constante en ${parvulo.nivel_actual}. Con ${observaciones.length} observaciones registradas, destaca su desenvolvimiento autónomo y su curiosidad frente a materiales novedosos.`,
      desarrollo_personal_social: `En el ámbito de Desarrollo Personal y Social, [${parvulo.id}] muestra una adecuada adaptación a los momentos clave de la jornada (ingreso, alimentación e higiene), afianzando vínculos de confianza con su educadora y participando en dinámicas colectivas.`,
      comunicacion_integral: `Demuestra interés por cuentos dialogados y canciones grupales. Se expresa mediante combinaciones de palabras y gestos significativos para manifestar necesidades, gustos y descubrimientos plásticos.`,
      interaccion_entorno: `Explora el espacio de sala clasificando objetos por atributos inmediatos (color, tamaño) y mostrando persistencia en actividades lúdicas de encaje y equilibrio.`,
      estrategia_aula_sugerida: `Proponer actividades de exploración sensorial en pequeños grupos y modelar vocabulario descriptivo durante las experiencias pedagógicas al aire libre.`,
      observaciones_computadas: observaciones.length,
      estado: 'borrador_ia'
    };
  }

  /**
   * Genera recomendación de nivel fundamentada en evidencias concretas
   */
  public generateRecommendation(
    parvulo: Parvulo,
    observaciones: Observacion[]
  ): RecomendacionNivel {
    const consolidadas = observaciones.filter(o => o.nivel_logrado === 'consolidado');
    const enInicio = observaciones.filter(o => o.nivel_logrado === 'en_inicio');

    let decision: 'avanzar' | 'mantener' | 'reforzar' = 'mantener';
    let fundamentacion = '';
    let confianza = 0.88;

    if (enInicio.length >= 2 || (observaciones.length > 0 && enInicio.length / observaciones.length >= 0.4)) {
      decision = 'reforzar';
      confianza = 0.92;
      fundamentacion = `Se recomienda activar plan de refuerzo y andamiaje singularizado para [${parvulo.id}]. Las observaciones denotan alertas de apoyo en áreas críticas de autorregulación o lenguaje básico que requieren acompañamiento pedagógico antes de transitar a nuevos desafíos.`;
    } else if (consolidadas.length >= 4 && parvulo.edad_meses >= 28) {
      decision = 'avanzar';
      confianza = 0.95;
      fundamentacion = `El párvulo [${parvulo.id}] demuestra una consolidación sistemática en múltiples núcleos curriculares con autonomía y lenguaje expresivo que cumplen los indicadores para dar el paso a experiencias del tramo superior con andamiaje inicial.`;
    } else {
      decision = 'mantener';
      confianza = 0.90;
      fundamentacion = `El párvulo [${parvulo.id}] progresa de manera armónica dentro de las expectativas del tramo actual (${parvulo.nivel_actual}). Se sugiere consolidar hábitos de prensión, turnos de juego y autonomía cotidiana en sala.`;
    }

    // Seleccionar evidencias reales citables
    const evidencias: EvidenciaCitada[] = observaciones.slice(0, 3).map(o => ({
      observacion_id: o.id,
      fecha: o.fecha,
      texto_cita: o.texto_anonimizado.slice(0, 120) + (o.texto_anonimizado.length > 120 ? '...' : ''),
      nucleo: o.nucleo,
      relevancia: o.nivel_logrado === 'consolidado' ? 'Demuestra dominio pleno del indicador' : 'Área de oportunidad para andamiaje de aula'
    }));

    return {
      id: `REC-${Date.now().toString().slice(-4)}`,
      id_nino: parvulo.id,
      fecha_generacion: new Date().toISOString().split('T')[0],
      tramo_actual: parvulo.tramo,
      decision_propuesta: decision,
      confianza_rubrica: confianza,
      fundamentacion_pedagogica: fundamentacion,
      evidencias,
      estado_educadora: 'pendiente'
    };
  }
}

export const aiService = new AiService();
