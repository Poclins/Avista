import React, { useState } from 'react';
import { Camera, Mic, Sparkles, Check, Image, FileText, ArrowRight, Eye, RefreshCw } from 'lucide-react';
import confetti from 'canvas-confetti';
import { Parvulo, Observacion, AnalisisGarabato } from '../types/avista';

interface AnalisisMultimodalProps {
  parvulos: Parvulo[];
  onSaveObservation: (nuevaObs: Observacion) => void;
}

const MUESTRAS_ARTE: AnalisisGarabato[] = [
  {
    id: 'ART-01',
    imagen_url: '/images/pedagogical_notes_capture_1794283481387.jpg',
    titulo_obra: 'Garabateo Circular y Mezcla de Témpera (Martina S. · 31 meses)',
    estadio_lowenfeld: 'garabateo_circular',
    estadio_nombre_comun: 'Garabateo Circular Controlado',
    rango_etario_tipico: '28 a 36 meses',
    prension_motriz_observada: 'Prensión trípode estática incipiente; utiliza muñeca en lugar de todo el brazo.',
    distribucion_espacial: 'Ocupa la zona central del soporte de papel con bucles concéntricos continuos.',
    intencionalidad_simbolica: 'Nombra verbalmente su producción: "el sol redondo y las flores verdes".',
    indicador_bcep_asociado: 'Experimenta con diversos materiales gráficos explorando mezclas cromáticas y trazos intencionados (Lenguajes Artísticos).',
    observacion_sugerida: 'En experiencia plástica libre, Martina sostiene el pincel con prensión trípode incipiente. Realiza trazos circulares continuos y experimenta mezclando azul con amarillo descubriendo el verde, atribuyendo significado verbal a su creación ("sol y flores").'
  },
  {
    id: 'ART-02',
    imagen_url: '/images/avista_kinder_classroom_1794283481000.jpg',
    titulo_obra: 'Construcción Tridimensional con Bloques (Lucas M. · 29 meses)',
    estadio_lowenfeld: 'exploracion_cromatica',
    estadio_nombre_comun: 'Juego Constructivo Simbólico',
    rango_etario_tipico: '24 a 32 meses',
    prension_motriz_observada: 'Coordinación óculo-manual fina; ajuste postural y pinza digital para colocar piezas superiores.',
    distribucion_espacial: 'Construcción vertical de 7 niveles con base simétrica de 2 columnas.',
    intencionalidad_simbolica: 'Manifiesta verbalmente: "es el castillo del oso que no se cae".',
    indicador_bcep_asociado: 'Resuelve problemas prácticos de estabilidad y relaciones espaciales mediante material concreto (Pensamiento Matemático).',
    observacion_sugerida: 'Durante el rincón de construcción, Lucas ensambla de forma autónoma una estructura vertical de 7 bloques de madera. Demuestra control inhibitorio al modular la fuerza de apoyo para evitar el derrumbe y comparte el logro con sus compañeros.'
  },
  {
    id: 'ART-03',
    imagen_url: '/images/pedagogical_notes_capture_1794283481387.jpg',
    titulo_obra: 'Garabateo Longitudinal y Modelado en Masa (Mateo V. · 25 meses)',
    estadio_lowenfeld: 'garabateo_longitudinal',
    estadio_nombre_comun: 'Garabateo Longitudinal / Barrido',
    rango_etario_tipico: '20 a 28 meses',
    prension_motriz_observada: 'Prensión palmar cilíndrica; movimiento motor originado principalmente desde el hombro y codo.',
    distribucion_espacial: 'Líneas paralelas de izquierda a derecha sin límite de borde de página.',
    intencionalidad_simbolica: 'Disfrute cinestésico del movimiento; aún sin asociación verbal previa al trazo.',
    indicador_bcep_asociado: 'Descubre las propiedades plásticas y sensoriales de mezclas y pigmentos mediante el movimiento corporal (Corporalidad y Movimiento).',
    observacion_sugerida: 'Mateo experimenta con masa y crayones gruesos realizando barridos longitudinales vigorosos. Muestra placer sensorial en la repetición del trazo motriz y responde favorablemente a la mediación de la tía al facilitarle hojas de gran formato.'
  }
];

export const AnalisisMultimodal: React.FC<AnalisisMultimodalProps> = ({
  parvulos,
  onSaveObservation
}) => {
  const [muestraSeleccionada, setMuestraSeleccionada] = useState<AnalisisGarabato>(MUESTRAS_ARTE[0]);
  const [selectedChildId, setSelectedChildId] = useState<string>('NI-1002'); // Martina
  const [guardadoExito, setGuardadoExito] = useState(false);

  // Flight dictation state
  const [isRecordingDictado, setIsRecordingDictado] = useState(false);
  const [dictadoSeconds, setDictadoSeconds] = useState(0);
  const [dictadoInterval, setDictadoInterval] = useState<any>(null);
  const [textoDictado, setTextoDictado] = useState('');
  const [dictadoProcesado, setDictadoProcesado] = useState<{
    idNino: string;
    texto: string;
    indicador: string;
  } | null>(null);

  const startFlightDictado = () => {
    setIsRecordingDictado(true);
    setDictadoSeconds(0);
    const int = setInterval(() => {
      setDictadoSeconds(prev => prev + 1);
    }, 1000);
    setDictadoInterval(int);
  };

  const stopFlightDictado = () => {
    if (dictadoInterval) clearInterval(dictadoInterval);
    setIsRecordingDictado(false);

    // Audio simulado realista de aula chilena
    const ejemplos = [
      {
        idNino: 'NI-1001',
        texto: '[NI-1001] en el rincón de biblioteca tomó el cuento del gato con botas, pasó las páginas de una en una y le mostró las ilustraciones a Tomás nombrándole "el miau miau".',
        indicador: 'Iniciación a la lectura compartida y coordinación fina de hojeo'
      },
      {
        idNino: 'NI-1005',
        texto: '[NI-1005] en la mesa sensorial aceptó tocar la masa tibia con olor a vainilla durante 5 minutos guiado por la tía, sonriendo al hundir sus dedos.',
        indicador: 'Tolerancia sensorial progresiva y apertura al andamiaje afectivo'
      },
      {
        idNino: 'NI-1004',
        texto: '[NI-1004] en el almuerzo sostuvo la cuchara con prensión palmar limpia y colocó su plato en la bandeja al finalizar sin ayuda.',
        indicador: 'Autonomía en rutinas cotidianas de alimentación'
      }
    ];

    const pick = ejemplos[Math.floor(Math.random() * ejemplos.length)];
    setTextoDictado(pick.texto);
    setDictadoProcesado(pick);
  };

  const handleConvertirEnObservacion = () => {
    const fechaHoy = new Date().toISOString().split('T')[0];
    const horaActual = new Date().toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });

    const nueva: Observacion = {
      id: `OBS-ART-${Date.now().toString().slice(-4)}`,
      id_nino: selectedChildId,
      fecha: fechaHoy,
      hora: horaActual,
      formato: 'foto_apunte',
      texto_crudo: muestraSeleccionada.observacion_sugerida,
      texto_anonimizado: muestraSeleccionada.observacion_sugerida.replace(/Martina|Lucas|Mateo/g, `[${selectedChildId}]`),
      ambito: 'comunicacion_integral',
      nucleo: 'lenguajes_artisticos',
      indicador_logro: muestraSeleccionada.indicador_bcep_asociado,
      nivel_logrado: 'consolidado',
      educadora_responsable: 'Tía Marcela Valenzuela',
      validado_por_educadora: true,
      tags: ['análisis de dibujo', muestraSeleccionada.estadio_nombre_comun, 'motricidad'],
      adjunto_url: muestraSeleccionada.imagen_url
    };

    onSaveObservation(nueva);
    setGuardadoExito(true);
    try {
      confetti({ particleCount: 40, spread: 50, origin: { y: 0.7 } });
    } catch (e) {}
    setTimeout(() => setGuardadoExito(false), 3000);
  };

  const handleGuardarDictado = () => {
    if (!dictadoProcesado) return;
    const fechaHoy = new Date().toISOString().split('T')[0];
    const horaActual = new Date().toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });

    const nueva: Observacion = {
      id: `OBS-VOZ-${Date.now().toString().slice(-4)}`,
      id_nino: dictadoProcesado.idNino,
      fecha: fechaHoy,
      hora: horaActual,
      formato: 'audio_voz',
      duracion_audio: `${dictadoSeconds || 12}s`,
      texto_crudo: dictadoProcesado.texto,
      texto_anonimizado: dictadoProcesado.texto,
      ambito: 'desarrollo_personal',
      nucleo: 'identidad_autonomia',
      indicador_logro: dictadoProcesado.indicador,
      nivel_logrado: 'consolidado',
      educadora_responsable: 'Tía Marcela Valenzuela',
      validado_por_educadora: true,
      tags: ['dictado al vuelo', 'audio rápido']
    };

    onSaveObservation(nueva);
    setDictadoProcesado(null);
    setTextoDictado('');
    try {
      confetti({ particleCount: 30, spread: 45, origin: { y: 0.7 } });
    } catch (e) {}
  };

  return (
    <div className="space-y-8 max-w-[1200px] mx-auto">
      {/* Banner */}
      <div className="bg-[#f9efe4] border border-[#ecedef] rounded-[32px] p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#f67748]" />
            <span className="text-xs font-semibold uppercase tracking-wider text-[#f67748]">
              Multimodalidad con Visión & Voz Inteligente
            </span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-medium text-[#2d2f34]">
            Análisis de Garabateo Infantil & Dictado al Vuelo
          </h1>
          <p className="text-xs sm:text-sm text-[#3f434a] leading-relaxed font-sans">
            Captura la realidad viva de la sala: analiza fotografías de dibujos y modelados según los estadios evolutivos del arte infantil 
            (escala Lowenfeld) o dicta audios de 10 segundos mientras acompañas a los niños.
          </p>
        </div>

        <div className="bg-white p-5 rounded-[24px] border border-[#ecedef] shadow-subtle shrink-0 min-w-[200px]">
          <span className="text-xs text-[#5e646e] block font-sans">Capacidades de Visión</span>
          <span className="font-serif text-2xl font-medium text-[#2d2f34]">Estadios BCEP</span>
          <span className="text-[11px] text-[#479a53] block mt-0.5">Prensión · Espacio · Simbolismo</span>
        </div>
      </div>

      {/* Seccion 1: Galería y Análisis de Garabatos */}
      <div className="bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-8 shadow-product space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#ecedef] pb-4">
          <div>
            <h2 className="font-serif text-xl font-medium text-[#2d2f34]">
              Análisis Evolutivo de Dibujo y Creación Plástica
            </h2>
            <p className="text-xs text-[#5e646e] mt-0.5">
              Identifica prensión motriz, control inhibitorio y simbolismo gráfico en creaciones de sala
            </p>
          </div>

          {/* Child Picker */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#5e646e]">Asignar a:</span>
            <select
              value={selectedChildId}
              onChange={(e) => setSelectedChildId(e.target.value)}
              className="text-xs bg-[#fdf9f4] border border-[#ecedef] rounded-full px-3 py-1.5 font-medium text-[#2d2f34]"
            >
              {parvulos.map(p => (
                <option key={p.id} value={p.id}>
                  {p.id} ({p.alias_pedagogico})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 3 Artwork Samples */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {MUESTRAS_ARTE.map(muestra => {
            const isSelected = muestra.id === muestraSeleccionada.id;
            return (
              <button
                key={muestra.id}
                type="button"
                onClick={() => setMuestraSeleccionada(muestra)}
                className={`p-4 rounded-[24px] border text-left transition-all flex flex-col justify-between space-y-3 ${
                  isSelected
                    ? 'border-[#f67748] bg-[#f9efe4] ring-1 ring-[#f67748] shadow-xs'
                    : 'border-[#ecedef] bg-[#fdf9f4] hover:bg-white'
                }`}
              >
                <div className="space-y-2">
                  <div className="h-32 w-full rounded-2xl overflow-hidden border border-[#ecedef] bg-white">
                    <img
                      src={muestra.imagen_url}
                      alt={muestra.titulo_obra}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <span className="text-[10px] font-mono text-[#f67748] uppercase font-semibold block">
                    {muestra.estadio_nombre_comun}
                  </span>
                  <h3 className="font-serif text-sm font-medium text-[#2d2f34] line-clamp-1">
                    {muestra.titulo_obra}
                  </h3>
                </div>

                <div className="flex items-center justify-between text-[11px] text-[#5e646e] pt-2 border-t border-[#ecedef]/80 w-full">
                  <span>Edad típica: {muestra.rango_etario_tipico}</span>
                  <span className="text-[#2d2f34] font-medium">{isSelected ? 'Seleccionada' : 'Ver análisis'}</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Artwork Deep Pedagogical Analysis */}
        <div className="p-6 bg-[#fdf9f4] rounded-[24px] border border-[#ecedef] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="text-[11px] font-semibold text-[#f67748] uppercase tracking-wider block mb-0.5">
                Diagnóstico de Desarrollo Motriz y Gráfico
              </span>
              <h3 className="font-serif text-lg font-medium text-[#2d2f34]">
                {muestraSeleccionada.estadio_nombre_comun} (Escala Lowenfeld / BCEP)
              </h3>
            </div>

            <button
              type="button"
              onClick={handleConvertirEnObservacion}
              className="px-5 py-2 text-xs font-medium text-white bg-[#f67748] hover:bg-[#e46436] active:scale-95 rounded-full shadow-xs transition flex items-center gap-1.5 self-start sm:self-auto"
            >
              <Check className="w-3.5 h-3.5" />
              <span>{guardadoExito ? '¡Guardada en Ficha!' : 'Convertir en Observación Oficial'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-sans">
            <div className="p-3.5 bg-white rounded-xl border border-[#ecedef]">
              <span className="font-semibold text-[#2d2f34] block mb-1">Prensión y Motricidad Fina</span>
              <p className="text-[#3f434a] leading-relaxed">{muestraSeleccionada.prension_motriz_observada}</p>
            </div>
            <div className="p-3.5 bg-white rounded-xl border border-[#ecedef]">
              <span className="font-semibold text-[#2d2f34] block mb-1">Distribución en el Soporte</span>
              <p className="text-[#3f434a] leading-relaxed">{muestraSeleccionada.distribucion_espacial}</p>
            </div>
            <div className="p-3.5 bg-white rounded-xl border border-[#ecedef]">
              <span className="font-semibold text-[#2d2f34] block mb-1">Intencionalidad Simbólica</span>
              <p className="text-[#3f434a] leading-relaxed">{muestraSeleccionada.intencionalidad_simbolica}</p>
            </div>
          </div>

          <div className="p-4 bg-white rounded-xl border border-[#ecedef] text-xs">
            <span className="text-[11px] font-semibold text-[#5e646e] uppercase tracking-wider block mb-1">
              Redacción Pedagógica para la Bitácora Quincenal:
            </span>
            <p className="text-[#2d2f34] leading-relaxed italic font-sans">
              "{muestraSeleccionada.observacion_sugerida}"
            </p>
          </div>
        </div>
      </div>

      {/* Seccion 2: Dictado al Vuelo (Fast Mic in Classroom) */}
      <div className="bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-8 shadow-product space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="font-serif text-xl font-medium text-[#2d2f34]">
              "Dictado al Vuelo" (Audio Rápido de Sala)
            </h2>
            <p className="text-xs text-[#5e646e] mt-0.5">
              Habla mientras estás de pie en el aula; Avista limpia el audio, detecta al niño y archiva el registro.
            </p>
          </div>

          <button
            type="button"
            onClick={isRecordingDictado ? stopFlightDictado : startFlightDictado}
            className={`min-h-[44px] px-6 py-2.5 rounded-full text-xs font-medium flex items-center gap-2 transition shadow-xs ${
              isRecordingDictado
                ? 'bg-rose-600 text-white animate-pulse'
                : 'bg-[#2d2f34] hover:bg-[#3f434a] text-white'
            }`}
          >
            <Mic className="w-4 h-4 text-[#f67748]" />
            <span>{isRecordingDictado ? `Grabando (${dictadoSeconds}s) · Pulsa al terminar` : 'Iniciar Dictado de Voz (10s)'}</span>
          </button>
        </div>

        {dictadoProcesado && (
          <div className="p-5 bg-[#f9efe4] rounded-2xl border border-[#ecedef] space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-serif font-semibold text-[#2d2f34]">
                Audio Transcrito & Anonimizado
              </span>
              <span className="font-mono text-[#f67748] font-medium">Párvulo {dictadoProcesado.idNino}</span>
            </div>

            <p className="text-xs sm:text-sm text-[#3f434a] leading-relaxed bg-white p-3.5 rounded-xl border border-[#ecedef] font-sans">
              "{dictadoProcesado.texto}"
            </p>

            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-[#5e646e]">
                Indicador: <strong className="text-[#2d2f34]">{dictadoProcesado.indicador}</strong>
              </span>

              <button
                type="button"
                onClick={handleGuardarDictado}
                className="px-5 py-2 text-xs font-medium text-white bg-[#f67748] hover:bg-[#e46436] rounded-full shadow-xs transition flex items-center gap-1.5"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Confirmar y Guardar Registro</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
