import React, { useState } from 'react';
import { Sparkles, Printer, Copy, Check, Users, Package, Clock, MessageCircle, HelpCircle, HeartHandshake } from 'lucide-react';
import { Parvulo, Observacion, RecetaAndamiaje, AmbitoCurricular, NucleoCurricular } from '../types/avista';

interface GeneradorAndamiajeProps {
  parvulos: Parvulo[];
  observaciones: Observacion[];
}

const MATERIALES_DISPONIBLES = [
  'Cajas de cartón y tubos',
  'Bloques de madera',
  'Piñas y elementos de la naturaleza',
  'Tapitas plásticas de colores',
  'Plasticina o masa casera',
  'Carretillas o triciclos',
  'Telas y mantas sensoriales',
  'Pinceles gruesos y témperas'
];

export const GeneradorAndamiaje: React.FC<GeneradorAndamiajeProps> = ({
  parvulos,
  observaciones
}) => {
  const [selectedChildId, setSelectedChildId] = useState<string>('NI-1005'); // Default to Mateo (apego/juego solitario)
  const [materialesSeleccionados, setMaterialesSeleccionados] = useState<string[]>([
    'Bloques de madera',
    'Cajas de cartón y tubos',
    'Telas y mantas sensoriales'
  ]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [recetaActual, setRecetaActual] = useState<RecetaAndamiaje | null>(null);
  const [copied, setCopied] = useState(false);

  const currentChild = parvulos.find(p => p.id === selectedChildId) || parvulos[0];
  const childObs = observaciones.filter(o => o.id_nino === selectedChildId);

  const toggleMaterial = (mat: string) => {
    if (materialesSeleccionados.includes(mat)) {
      setMaterialesSeleccionados(prev => prev.filter(m => m !== mat));
    } else {
      setMaterialesSeleccionados(prev => [...prev, mat]);
    }
  };

  const generarReceta = () => {
    setIsGenerating(true);
    setTimeout(() => {
      // Heurística pedagógica situada para párvulos Integra
      const isMateo = currentChild.id === 'NI-1005';
      const peer = parvulos.find(p => p.id === 'NI-1006') || parvulos[1]; // Emilia R.

      const nuevaReceta: RecetaAndamiaje = {
        id: `AND-${Date.now().toString().slice(-4)}`,
        id_nino: currentChild.id,
        alias_pedagogico: currentChild.alias_pedagogico,
        desafio_detectado: isMateo 
          ? 'Autorregulación emocional y transición de juego solitario hacia juego asociativo en patio.'
          : 'Consolidación de destrezas comunicativas y motricidad en dinámicas grupales.',
        ambito: isMateo ? 'desarrollo_personal' : 'comunicacion_integral',
        nucleo: isMateo ? 'convivencia_ciudadania' : 'lenguaje_verbal',
        titulo_actividad: isMateo 
          ? 'El Túnel Secreto de los Constructores (Dueto Guiado)'
          : 'El Taller de los Pequeños Arquitectos de Sala',
        materiales_integra: materialesSeleccionados.length > 0 ? materialesSeleccionados : ['Cajas de cartón', 'Bloques de madera'],
        duracion_sugerida: '15 a 20 minutos',
        momento_jornada: 'patio_techado',
        pasos_mediacion: [
          `Paso 1 (Acogida): La tía invita a ${currentChild.alias_pedagogico} y a ${peer.alias_pedagogico} a un espacio delimitado con telas suaves, evitando ruidos repentinos.`,
          `Paso 2 (Asignación de roles complementarios): Se le entrega a ${currentChild.alias_pedagogico} la responsabilidad de ser el "guardián de los bloques", pasándole los elementos grandes a su compañera.`,
          `Paso 3 (Andamiaje verbal): La educadora modela la interacción verbal con frases cortas: "¡Mira, tu compañero te agradece cuando le pasas el bloque amarillo!".`,
          `Paso 4 (Cierre reflexivo): Aplauso conjunto frente a la construcción terminada y fotografía para su bitácora.`
        ],
        pregunta_gatilladora: '¿Qué animal del jardín podría dormir adentro de este túnel si le agregamos un techo?',
        criterio_exito_observable: `Permanece al menos 8 minutos compartiendo materiales con su par sin retirarse al juego solitario.`,
        parvulo_companero_sugerido: peer.alias_pedagogico
      };

      setRecetaActual(nuevaReceta);
      setIsGenerating(false);
    }, 600);
  };

  const handleCopy = () => {
    if (!recetaActual) return;
    const txt = `${recetaActual.titulo_actividad}\nPara: ${recetaActual.alias_pedagogico}\nMateriales: ${recetaActual.materiales_integra.join(', ')}\nPasos:\n${recetaActual.pasos_mediacion.join('\n')}\nCriterio: ${recetaActual.criterio_exito_observable}`;
    navigator.clipboard.writeText(txt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-8 max-w-[1200px] mx-auto">
      {/* Banner */}
      <div className="bg-[#f9efe4] border border-[#ecedef] rounded-[32px] p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#f67748]" />
            <span className="text-xs font-semibold uppercase tracking-wider text-[#f67748]">
              De la Observación a la Acción Inmediata
            </span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-medium text-[#2d2f34]">
            Generador de Andamiaje Lúdico a la Medida
          </h1>
          <p className="text-xs sm:text-sm text-[#3f434a] leading-relaxed font-sans">
            No basta con saber que un niño necesita apoyo. Avista diseña micro-actividades lúdicas situadas 
            con los <strong>materiales cotidianos que ya tienes en la sala</strong>, indicando el paso a paso de mediación y la pregunta gatilladora.
          </p>
        </div>

        <div className="bg-white p-5 rounded-[24px] border border-[#ecedef] shadow-subtle shrink-0 min-w-[200px]">
          <span className="text-xs text-[#5e646e] block font-sans">Párvulos en Alerta de Apoyo</span>
          <span className="font-serif text-2xl font-medium text-[#f67748] tabular-nums">2 casos</span>
          <span className="text-[11px] text-[#5e646e] block mt-0.5">NI-1005 (Mateo) · NI-1015 (Gaspar)</span>
        </div>
      </div>

      {/* Configuration Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Form: Child & Materials (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-7 shadow-product space-y-5">
          <h2 className="font-serif text-lg font-medium text-[#2d2f34]">
            Configurar Experiencia de Sala
          </h2>

          <div>
            <label className="text-xs font-semibold text-[#2d2f34] block mb-1.5">
              1. Seleccionar párvulo que requiere andamiaje
            </label>
            <select
              value={selectedChildId}
              onChange={(e) => setSelectedChildId(e.target.value)}
              className="w-full px-4 py-2.5 text-xs sm:text-sm bg-[#fdf9f4] border border-[#ecedef] rounded-full font-medium text-[#2d2f34] focus:ring-1 focus:ring-[#f67748]"
            >
              {parvulos.map(p => (
                <option key={p.id} value={p.id}>
                  {p.id} · {p.alias_pedagogico} ({p.edad_meses}m) {p.id === 'NI-1005' ? '⚠️ (Refuerzo)' : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-[#2d2f34] block mb-2">
              2. Materiales disponibles en tu sala hoy
            </label>
            <div className="flex flex-wrap gap-2">
              {MATERIALES_DISPONIBLES.map(mat => {
                const isSelected = materialesSeleccionados.includes(mat);
                return (
                  <button
                    key={mat}
                    type="button"
                    onClick={() => toggleMaterial(mat)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-all ${
                      isSelected
                        ? 'bg-[#2d2f34] text-white border-[#2d2f34] shadow-xs'
                        : 'bg-[#fdf9f4] text-[#3f434a] border-[#ecedef] hover:bg-[#f9efe4]'
                    }`}
                  >
                    {mat}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            onClick={generarReceta}
            disabled={isGenerating}
            className="w-full min-h-[44px] py-2.5 px-5 bg-[#f67748] hover:bg-[#e46436] active:scale-95 text-white text-xs sm:text-sm font-medium rounded-full flex items-center justify-center gap-2 shadow-xs transition"
          >
            <Sparkles className="w-4 h-4" />
            <span>{isGenerating ? 'Generando receta pedagógica...' : 'Diseñar Experiencia de Andamiaje'}</span>
          </button>
        </div>

        {/* Right Card: Generated Scaffolding Recipe (7 cols) */}
        <div className="lg:col-span-7">
          {recetaActual ? (
            <div className="bg-white rounded-[32px] border border-[#ecedef] shadow-product p-6 sm:p-8 space-y-6">
              {/* Recipe Top Header */}
              <div className="border-b border-[#ecedef] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-[11px] font-mono text-[#f67748] bg-[#f9efe4] px-2.5 py-0.5 rounded-full inline-block mb-1">
                    Receta Situada #{recetaActual.id}
                  </span>
                  <h3 className="font-serif text-xl sm:text-2xl font-medium text-[#2d2f34]">
                    {recetaActual.titulo_actividad}
                  </h3>
                  <span className="text-xs text-[#5e646e] block mt-0.5">
                    Diseñada para {recetaActual.alias_pedagogico} · Momento: {recetaActual.momento_jornada.replace('_', ' ')}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopy}
                    className="p-2 text-[#5e646e] hover:text-[#2d2f34] bg-[#f9efe4] rounded-full transition"
                    title="Copiar receta"
                  >
                    {copied ? <Check className="w-4 h-4 text-[#479a53]" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => window.print()}
                    className="p-2 text-[#5e646e] hover:text-[#2d2f34] bg-[#f9efe4] rounded-full transition"
                    title="Imprimir ficha de aula"
                  >
                    <Printer className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Mediación pedagógica en 4 pasos */}
              <div className="space-y-4 text-xs sm:text-sm font-sans">
                {/* Desafío y Par Mediador */}
                <div className="p-4 bg-[#fdf9f4] rounded-2xl border border-[#ecedef] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-serif text-xs font-semibold text-[#2d2f34]">
                      Objetivo de Andamiaje
                    </span>
                    {recetaActual.parvulo_companero_sugerido && (
                      <span className="text-[11px] text-[#479a53] flex items-center gap-1 font-medium">
                        <HeartHandshake className="w-3.5 h-3.5" />
                        Par mediador: {recetaActual.parvulo_companero_sugerido}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#3f434a] leading-relaxed">
                    {recetaActual.desafio_detectado}
                  </p>
                </div>

                {/* Pasos */}
                <div>
                  <span className="text-xs font-semibold text-[#5e646e] uppercase tracking-wider block mb-2">
                    Protocolo de Mediación para la Educadora
                  </span>
                  <div className="space-y-2">
                    {recetaActual.pasos_mediacion.map((paso, idx) => (
                      <div key={idx} className="p-3 bg-white rounded-xl border border-[#ecedef] text-xs text-[#3f434a] leading-relaxed">
                        {paso}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Pregunta Gatilladora & Criterio */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                  <div className="p-3.5 bg-[#f9efe4] rounded-2xl border border-[#ecedef]">
                    <span className="text-[11px] font-semibold text-[#2d2f34] block mb-1">
                      Pregunta Gatilladora
                    </span>
                    <p className="text-xs text-[#3f434a] italic leading-normal">
                      "{recetaActual.pregunta_gatilladora}"
                    </p>
                  </div>

                  <div className="p-3.5 bg-[#fdf9f4] rounded-2xl border border-[#ecedef]">
                    <span className="text-[11px] font-semibold text-[#479a53] block mb-1">
                      Criterio Observable de Éxito
                    </span>
                    <p className="text-xs text-[#3f434a] leading-normal">
                      {recetaActual.criterio_exito_observable}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-[32px] border border-[#ecedef] p-10 text-center space-y-4 shadow-product">
              <div className="w-12 h-12 rounded-full bg-[#f9efe4] text-[#f67748] flex items-center justify-center mx-auto">
                <Sparkles className="w-6 h-6" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="font-serif text-lg font-medium text-[#2d2f34]">
                  Transforma el diagnóstico en una experiencia lúdica
                </h3>
                <p className="text-xs text-[#5e646e] leading-relaxed">
                  Selecciona a un párvulo y los materiales que tengas a mano. Avista generará un andamiaje paso a paso con preguntas y roles colaborativos.
                </p>
              </div>
              <button
                type="button"
                onClick={generarReceta}
                className="px-6 py-2.5 bg-[#2d2f34] hover:bg-[#3f434a] text-white text-xs sm:text-sm font-medium rounded-full shadow-xs transition"
              >
                Diseñar Experiencia para Mateo
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
