import React, { useState } from 'react';
import { X, Mic, FileText, Camera, Video, Sparkles, ShieldCheck, Check, RefreshCw } from 'lucide-react';
import { Parvulo, TipoFormato, AmbitoCurricular, NucleoCurricular, Observacion } from '../types/avista';
import { aiService } from '../services/aiService';
import { sanitizePedagogicalNote } from '../services/privacyService';

interface CaptureModalProps {
  isOpen: boolean;
  onClose: () => void;
  parvulos: Parvulo[];
  selectedChildId?: string;
  onSaveObservation: (nuevaObs: Observacion) => void;
}

const PLANTILLAS_DEMO = [
  {
    titulo: 'Bloques y motricidad',
    texto: 'Durante el rincón de construcción, apiló 7 bloques de madera manteniendo el equilibrio sin que se derribaran. Al terminar sonrió y llamó a la tía para mostrarle su torre.'
  },
  {
    titulo: 'Juego cooperativo',
    texto: 'En el patio techado invitó a un compañero a jugar con la carretilla diciendo "ahora te toca a ti". Hubo respeto de turnos y diálogo fluido durante 15 minutos.'
  },
  {
    titulo: 'Prensión y arte',
    texto: 'Sostuvo el pincel grueso con prensión trípode incipiente y combinó témpera azul con amarilla para descubrir el verde, nombrándolo espontáneamente.'
  },
  {
    titulo: 'Adaptación matinal',
    texto: 'Al ingresar en la mañana manifestó resistencia a despedirse de su mamá con llanto moderado. Tras 10 minutos de contención con canción suave se integró a la mesa de dibujo.'
  }
];

export const CaptureModal: React.FC<CaptureModalProps> = ({
  isOpen,
  onClose,
  parvulos,
  selectedChildId,
  onSaveObservation
}) => {
  const [childId, setChildId] = useState<string>(selectedChildId || parvulos[0]?.id || 'NI-1001');
  const [formato, setFormato] = useState<TipoFormato>('nota_escrita');
  const [notaTexto, setNotaTexto] = useState<string>('');
  
  // Audio state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [recordingInterval, setRecordingInterval] = useState<any>(null);

  // AI Classification state
  const [isProcessing, setIsProcessing] = useState(false);
  const [clasificacionPropuesta, setClasificacionPropuesta] = useState<{
    ambito: AmbitoCurricular;
    nucleo: NucleoCurricular;
    indicadorLogro: string;
    nivelLogrado: 'en_inicio' | 'en_desarrollo' | 'consolidado';
    tags: string[];
    advertenciaPrivacidad?: string;
  } | null>(null);

  if (!isOpen) return null;

  const currentChild = parvulos.find(p => p.id === childId) || parvulos[0];
  const liveSanitization = sanitizePedagogicalNote(notaTexto, childId);

  const startVoiceRecording = () => {
    setIsRecording(true);
    setRecordingSeconds(0);
    const interval = setInterval(() => {
      setRecordingSeconds(prev => prev + 1);
    }, 1000);
    setRecordingInterval(interval);
  };

  const stopVoiceRecording = () => {
    if (recordingInterval) clearInterval(recordingInterval);
    setIsRecording(false);
    const transcriptions = [
      `Audio de sala grabado (${recordingSeconds}s): Párvulo ${childId} participó activamente en la ronda de bienvenida, nombró a tres de sus compañeros y compartió las maracas de madera de forma espontánea.`,
      `Audio de sala grabado (${recordingSeconds}s): Observé a ${childId} en el lavamanos reconociendo los pasos de higiene, enjabonó sus manos y se secó sin requerir asistencia física de la tía.`,
      `Audio de sala grabado (${recordingSeconds}s): En la experiencia de exploración sensorial descubrió hojas y cortezas de eucaliptus, comparando texturas ásperas y suaves con mucho entusiasmo.`
    ];
    const picked = transcriptions[Math.floor(Math.random() * transcriptions.length)];
    setNotaTexto(picked);
  };

  const handleAnalizarConIA = async () => {
    if (!notaTexto.trim()) return;
    setIsProcessing(true);
    try {
      const res = await aiService.classifyObservation(notaTexto, childId, formato);
      setClasificacionPropuesta({
        ambito: res.ambito,
        nucleo: res.nucleo,
        indicadorLogro: res.indicadorLogro,
        nivelLogrado: res.nivelLogrado,
        tags: res.tags,
        advertenciaPrivacidad: res.advertenciaPrivacidad
      });
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleGuardarObservacion = () => {
    if (!notaTexto.trim()) return;

    const fechaHoy = new Date().toISOString().split('T')[0];
    const horaActual = new Date().toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });

    const nueva: Observacion = {
      id: `OBS-${Date.now().toString().slice(-4)}`,
      id_nino: childId,
      fecha: fechaHoy,
      hora: horaActual,
      formato,
      texto_crudo: notaTexto,
      texto_anonimizado: liveSanitization.sanitizedText,
      ambito: clasificacionPropuesta?.ambito || 'desarrollo_personal',
      nucleo: clasificacionPropuesta?.nucleo || 'convivencia_ciudadania',
      indicador_logro: clasificacionPropuesta?.indicadorLogro || 'Conducta observada en la experiencia de sala',
      nivel_logrado: clasificacionPropuesta?.nivelLogrado || 'en_desarrollo',
      educadora_responsable: 'Tía Marcela Valenzuela',
      validado_por_educadora: true,
      tags: clasificacionPropuesta?.tags || ['observación de aula', 'registro pedagógico'],
      adjunto_url: formato === 'foto_apunte' ? '/images/pedagogical_notes_capture_1794283481387.jpg' : undefined,
      duracion_audio: formato === 'audio_voz' ? `${recordingSeconds || 24}s` : undefined
    };

    onSaveObservation(nueva);
    onClose();
    setNotaTexto('');
    setClasificacionPropuesta(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-3 sm:p-4 backdrop-blur-xs overflow-y-auto">
      <div className="w-full max-w-2xl bg-[#fdf9f4] rounded-[32px] shadow-product border border-[#ecedef] overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-[#ecedef] flex items-center justify-between bg-white">
          <div>
            <h2 className="font-serif text-xl font-medium text-[#2d2f34]">
              Captura Rápida de Observación
            </h2>
            <p className="text-xs text-[#5e646e] mt-0.5">
              Registra lo que ves de forma natural en sala. Avista clasifica y protege los datos.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#5e646e] hover:text-[#2d2f34] hover:bg-[#f9efe4] rounded-full transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-sm">
          {/* 1. Selector de Párvulo */}
          <div>
            <label className="block text-xs font-semibold text-[#2d2f34] mb-1.5">
              Párvulo observado (Sala {currentChild.sala})
            </label>
            <select
              value={childId}
              onChange={(e) => setChildId(e.target.value)}
              className="w-full px-4 py-2.5 text-sm bg-white border border-[#ecedef] rounded-full focus:ring-1 focus:ring-[#f67748] focus:border-[#f67748] font-medium text-[#2d2f34]"
            >
              {parvulos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id} · {p.alias_pedagogico} ({p.edad_meses} meses)
                </option>
              ))}
            </select>
          </div>

          {/* 2. Selector de Formato de Entrada (Slite Pill segmented format) */}
          <div>
            <label className="block text-xs font-semibold text-[#2d2f34] mb-1.5">
              Formato de captura
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                type="button"
                onClick={() => setFormato('nota_escrita')}
                className={`min-h-[44px] flex items-center justify-center gap-2 px-3 py-2 rounded-full border text-xs font-medium transition-all ${
                  formato === 'nota_escrita'
                    ? 'border-[#2d2f34] bg-[#2d2f34] text-white shadow-xs'
                    : 'border-[#ecedef] bg-white text-[#3f434a] hover:bg-[#f9efe4]'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Nota Escrita</span>
              </button>

              <button
                type="button"
                onClick={() => setFormato('audio_voz')}
                className={`min-h-[44px] flex items-center justify-center gap-2 px-3 py-2 rounded-full border text-xs font-medium transition-all ${
                  formato === 'audio_voz'
                    ? 'border-[#2d2f34] bg-[#2d2f34] text-white shadow-xs'
                    : 'border-[#ecedef] bg-white text-[#3f434a] hover:bg-[#f9efe4]'
                }`}
              >
                <Mic className="w-3.5 h-3.5" />
                <span>Audio / Voz</span>
              </button>

              <button
                type="button"
                onClick={() => setFormato('foto_apunte')}
                className={`min-h-[44px] flex items-center justify-center gap-2 px-3 py-2 rounded-full border text-xs font-medium transition-all ${
                  formato === 'foto_apunte'
                    ? 'border-[#2d2f34] bg-[#2d2f34] text-white shadow-xs'
                    : 'border-[#ecedef] bg-white text-[#3f434a] hover:bg-[#f9efe4]'
                }`}
              >
                <Camera className="w-3.5 h-3.5" />
                <span>Foto Apunte</span>
              </button>

              <button
                type="button"
                onClick={() => setFormato('video_registro')}
                className={`min-h-[44px] flex items-center justify-center gap-2 px-3 py-2 rounded-full border text-xs font-medium transition-all ${
                  formato === 'video_registro'
                    ? 'border-[#2d2f34] bg-[#2d2f34] text-white shadow-xs'
                    : 'border-[#ecedef] bg-white text-[#3f434a] hover:bg-[#f9efe4]'
                }`}
              >
                <Video className="w-3.5 h-3.5" />
                <span>Video Hito</span>
              </button>
            </div>
          </div>

          {/* Opciones según formato */}
          {formato === 'audio_voz' && (
            <div className="p-4 bg-white rounded-2xl border border-[#ecedef] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
                  className={`min-h-[44px] px-5 py-2 rounded-full text-xs font-medium flex items-center gap-2 transition ${
                    isRecording
                      ? 'bg-rose-600 text-white animate-pulse'
                      : 'bg-[#2d2f34] hover:bg-[#3f434a] text-white'
                  }`}
                >
                  <Mic className="w-3.5 h-3.5" />
                  <span>{isRecording ? `Detener (${recordingSeconds}s)` : 'Grabar Dictado de Voz'}</span>
                </button>
                <span className="text-xs text-[#5e646e]">
                  {isRecording ? 'Capturando audio...' : 'Pulsa para transcribir'}
                </span>
              </div>
            </div>
          )}

          {formato === 'foto_apunte' && (
            <div className="p-4 bg-white rounded-2xl border border-[#ecedef] flex items-center gap-3">
              <img
                src="/images/pedagogical_notes_capture_1794283481387.jpg"
                alt="Cuaderno pedagógico de notas"
                className="w-16 h-12 rounded-xl object-cover border border-[#ecedef]"
              />
              <div className="text-xs text-[#3f434a]">
                <span className="font-semibold block text-[#2d2f34]">Visión OCR de Apuntes</span>
                <span className="text-[#5e646e]">Extrae texto manuscrito directamente de la libreta de sala.</span>
              </div>
            </div>
          )}

          {/* Plantillas rápidas como Dust Tag Chips */}
          <div>
            <span className="text-xs font-semibold text-[#5e646e] block mb-2">
              Plantillas de aula predefinidas:
            </span>
            <div className="flex flex-wrap gap-2 mb-3">
              {PLANTILLAS_DEMO.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setNotaTexto(p.texto)}
                  className="px-3.5 py-1 text-xs bg-[#f9efe4] hover:bg-[#ecedef] text-[#3f434a] rounded-full border border-[#ecedef] transition"
                >
                  {p.titulo}
                </button>
              ))}
            </div>

            <textarea
              value={notaTexto}
              onChange={(e) => {
                setNotaTexto(e.target.value);
                setClasificacionPropuesta(null);
              }}
              rows={4}
              placeholder="Ej: En la colación, Lucas sirvió el agua solo con la jarra sin derramar y pidió 'más por favor'..."
              className="w-full p-4 text-xs sm:text-sm bg-white border border-[#ecedef] rounded-2xl focus:ring-1 focus:ring-[#f67748] focus:border-[#f67748] text-[#2d2f34] leading-relaxed resize-none shadow-xs"
            />
          </div>

          {/* Privacy Guard Indicator in warm Dust Sand */}
          {notaTexto.trim() && (
            <div className="p-3.5 rounded-2xl bg-[#f9efe4] border border-[#ecedef] space-y-1">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#2d2f34]">
                <ShieldCheck className="w-4 h-4 text-[#479a53] shrink-0" />
                <span>Avista Privacy Guard · Seudonimización preventiva</span>
              </div>
              <p className="text-xs text-[#5e646e] pl-6 font-sans">
                Texto procesado:{' '}
                <span className="text-[#2d2f34] font-medium">"{liveSanitization.sanitizedText}"</span>
              </p>
              {liveSanitization.wasSanitized && (
                <p className="text-[11px] text-[#f67748] font-medium pl-6">
                  ⚠️ Se protegieron {liveSanitization.detectedEntities.length} datos sensibles antes de cualquier procesamiento externo.
                </p>
              )}
            </div>
          )}

          {/* AI Trigger Button: Dark CTA Charcoal Pill */}
          {!clasificacionPropuesta && notaTexto.trim() && (
            <button
              type="button"
              onClick={handleAnalizarConIA}
              disabled={isProcessing}
              className="w-full min-h-[44px] py-2.5 px-5 bg-[#2d2f34] hover:bg-[#3f434a] active:scale-98 text-white text-xs sm:text-sm font-medium rounded-full flex items-center justify-center gap-2 shadow-xs transition disabled:opacity-50"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-[#f67748]" />
                  <span>Clasificando según Bases Curriculares Integra...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-[#f67748]" />
                  <span>Clasificar con IA (Ámbito, Núcleo y Nivel)</span>
                </>
              )}
            </button>
          )}

          {/* AI Proposed Classification Result (White Product card inside cream modal) */}
          {clasificacionPropuesta && (
            <div className="p-5 bg-white rounded-2xl border border-[#ecedef] shadow-product space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#f67748]" />
                  <span className="font-serif text-base font-medium text-[#2d2f34]">
                    Propuesta Curricular (BCEP)
                  </span>
                </div>
                <span className="text-[11px] font-medium text-[#479a53] bg-[#fdf9f4] border border-[#bbf7d0] px-2.5 py-0.5 rounded-full">
                  {clasificacionPropuesta.nivelLogrado === 'consolidado' ? 'Consolidado' : clasificacionPropuesta.nivelLogrado === 'en_inicio' ? 'En Inicio' : 'En Desarrollo'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                <div>
                  <span className="text-[#5e646e] block text-[10px] uppercase font-semibold">Ámbito</span>
                  <span className="font-medium text-[#2d2f34] capitalize">
                    {clasificacionPropuesta.ambito.replace('_', ' ')}
                  </span>
                </div>
                <div>
                  <span className="text-[#5e646e] block text-[10px] uppercase font-semibold">Núcleo</span>
                  <span className="font-medium text-[#2d2f34] capitalize">
                    {clasificacionPropuesta.nucleo.replace('_', ' ')}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-[#5e646e] block text-[10px] uppercase font-semibold">Indicador de Logro</span>
                <p className="text-xs font-normal text-[#3f434a]">
                  {clasificacionPropuesta.indicadorLogro}
                </p>
              </div>

              <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-[#ecedef]">
                {clasificacionPropuesta.tags.map((t, idx) => (
                  <span key={idx} className="text-[11px] text-[#5e646e] bg-[#f9efe4] px-2.5 py-0.5 rounded-full border border-[#ecedef]">
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer with Primary Ember Pill CTA */}
        <div className="px-6 py-4 border-t border-[#ecedef] bg-white flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-[#5e646e] hover:text-[#2d2f34] transition"
          >
            Cancelar
          </button>

          <button
            type="button"
            onClick={handleGuardarObservacion}
            disabled={!notaTexto.trim()}
            className="min-h-[44px] px-6 py-2.5 bg-[#f67748] hover:bg-[#e46436] active:scale-95 text-white text-xs sm:text-sm font-medium rounded-full flex items-center gap-2 shadow-xs transition disabled:opacity-40"
          >
            <Check className="w-4 h-4" />
            <span>Confirmar y Guardar Registro</span>
          </button>
        </div>
      </div>
    </div>
  );
};
