import React from 'react';
import { X, Plus, Calendar, BookOpen, GitPullRequest, Mic, FileText, Camera, Video, ShieldCheck } from 'lucide-react';
import { Parvulo, Observacion } from '../types/avista';

interface ParvuloDetailModalProps {
  parvulo: Parvulo | null;
  observaciones: Observacion[];
  onClose: () => void;
  onOpenCapture: (childId: string) => void;
  onGoToBitacoras: (childId: string) => void;
  onGoToRecomendacion: (childId: string) => void;
}

export const ParvuloDetailModal: React.FC<ParvuloDetailModalProps> = ({
  parvulo,
  observaciones,
  onClose,
  onOpenCapture,
  onGoToBitacoras,
  onGoToRecomendacion
}) => {
  if (!parvulo) return null;

  const childObservations = observaciones.filter(o => o.id_nino === parvulo.id);

  const countPersonal = childObservations.filter(o => o.ambito === 'desarrollo_personal').length;
  const countComunicacion = childObservations.filter(o => o.ambito === 'comunicacion_integral').length;
  const countEntorno = childObservations.filter(o => o.ambito === 'interaccion_entorno').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-3 sm:p-4 backdrop-blur-xs overflow-y-auto">
      <div className="w-full max-w-3xl bg-[#fdf9f4] rounded-[32px] shadow-product border border-[#ecedef] overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Header on Star White */}
        <div className="px-6 py-5 border-b border-[#ecedef] flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono font-semibold px-3 py-1 bg-[#f9efe4] text-[#3f434a] rounded-full border border-[#ecedef]">
              {parvulo.id}
            </span>
            <div>
              <h2 className="font-serif text-xl sm:text-2xl font-medium text-[#2d2f34]">
                {parvulo.alias_pedagogico}
              </h2>
              <p className="text-xs text-[#5e646e] mt-0.5 font-sans">
                {parvulo.nivel_actual} · {parvulo.edad_meses} meses · Sala {parvulo.sala} ({parvulo.jardin_nombre})
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#5e646e] hover:text-[#2d2f34] hover:bg-[#f9efe4] rounded-full transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Curricular Ambito Coverage Cards (Slite White Product cards with shadow) */}
          <div className="bg-[#f9efe4] p-5 rounded-[24px] border border-[#ecedef]">
            <span className="text-[11px] font-semibold text-[#5e646e] uppercase tracking-wider block mb-3">
              Cobertura Curricular (Bases Curriculares Integra)
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="bg-white p-4 rounded-2xl border border-[#ecedef] shadow-subtle">
                <span className="text-[#5e646e] block text-[11px] mb-1">Desarrollo Personal y Social</span>
                <div className="flex items-baseline justify-between">
                  <span className="font-serif text-2xl font-medium text-[#2d2f34] tabular-nums">{countPersonal}</span>
                  <span className="text-[10px] text-[#9da3af]">Identidad / Vínculo</span>
                </div>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-[#ecedef] shadow-subtle">
                <span className="text-[#5e646e] block text-[11px] mb-1">Comunicación Integral</span>
                <div className="flex items-baseline justify-between">
                  <span className="font-serif text-2xl font-medium text-[#2d2f34] tabular-nums">{countComunicacion}</span>
                  <span className="text-[10px] text-[#9da3af]">Lenguaje / Arte</span>
                </div>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-[#ecedef] shadow-subtle">
                <span className="text-[#5e646e] block text-[11px] mb-1">Interacción con el Entorno</span>
                <div className="flex items-baseline justify-between">
                  <span className="font-serif text-2xl font-medium text-[#2d2f34] tabular-nums">{countEntorno}</span>
                  <span className="text-[10px] text-[#9da3af]">Exploración / Números</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Row with Slite Pill Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => onOpenCapture(parvulo.id)}
              className="flex items-center gap-2 px-5 py-2.5 text-xs font-medium text-white bg-[#f67748] hover:bg-[#e46436] active:scale-95 rounded-full shadow-xs transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Registrar Nueva Observación</span>
            </button>
            <button
              onClick={() => onGoToBitacoras(parvulo.id)}
              className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-[#3f434a] hover:text-[#2d2f34] bg-white border border-[#d9dde6] hover:bg-[#f9efe4] rounded-full transition"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Ver Bitácora Quincenal</span>
            </button>
            <button
              onClick={() => onGoToRecomendacion(parvulo.id)}
              className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-[#3f434a] hover:text-[#2d2f34] bg-white border border-[#d9dde6] hover:bg-[#f9efe4] rounded-full transition"
            >
              <GitPullRequest className="w-3.5 h-3.5 text-[#f67748]" />
              <span>Ver Rúbrica & Evidencia</span>
            </button>
          </div>

          {/* Timeline of Observations */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-serif text-base font-medium text-[#2d2f34]">
                Línea de Tiempo Pedagógica ({childObservations.length} registros)
              </h3>
              <div className="flex items-center gap-1.5 text-xs text-[#5e646e]">
                <ShieldCheck className="w-3.5 h-3.5 text-[#479a53]" />
                <span>Textos anonimizados E-1</span>
              </div>
            </div>

            {childObservations.length === 0 ? (
              <div className="p-8 text-center bg-white rounded-2xl border border-dashed border-[#ecedef] text-[#9da3af] text-xs">
                Aún no hay observaciones para este párvulo en la quincena actual. Pulsa "Registrar Nueva Observación".
              </div>
            ) : (
              <div className="space-y-3">
                {childObservations.map((obs) => {
                  return (
                    <div
                      key={obs.id}
                      className="p-4 bg-white rounded-2xl border border-[#ecedef] shadow-subtle space-y-2"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-[#2d2f34] capitalize">
                            {obs.nucleo.replace('_', ' ')}
                          </span>
                          <span className="text-[#9da3af]">·</span>
                          <span className="text-[#5e646e] flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {obs.fecha} ({obs.hora})
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          {obs.formato === 'audio_voz' && (
                            <span className="flex items-center gap-1 text-[11px] text-[#3f434a] bg-[#f9efe4] px-2.5 py-0.5 rounded-full">
                              <Mic className="w-3 h-3 text-[#f67748]" /> Audio
                            </span>
                          )}
                          {obs.formato === 'foto_apunte' && (
                            <span className="flex items-center gap-1 text-[11px] text-[#3f434a] bg-[#f9efe4] px-2.5 py-0.5 rounded-full">
                              <Camera className="w-3 h-3 text-[#479a53]" /> Foto
                            </span>
                          )}
                          {obs.formato === 'video_registro' && (
                            <span className="flex items-center gap-1 text-[11px] text-[#3f434a] bg-[#f9efe4] px-2.5 py-0.5 rounded-full">
                              <Video className="w-3 h-3 text-[#74a6f1]" /> Video
                            </span>
                          )}
                          {obs.formato === 'nota_escrita' && (
                            <span className="flex items-center gap-1 text-[11px] text-[#3f434a] bg-[#f9efe4] px-2.5 py-0.5 rounded-full">
                              <FileText className="w-3 h-3" /> Nota
                            </span>
                          )}

                          <span className={`text-[11px] font-medium px-2.5 py-0.5 rounded-full border ${
                            obs.nivel_logrado === 'consolidado' 
                              ? 'text-[#479a53] border-[#bbf7d0] bg-[#fdf9f4]' 
                              : obs.nivel_logrado === 'en_inicio' 
                                ? 'text-[#f67748] border-[#f67748]/30 bg-[#fdf9f4]' 
                                : 'text-[#5e646e] border-[#ecedef] bg-[#fdf9f4]'
                          }`}>
                            {obs.nivel_logrado === 'consolidado' ? 'Consolidado' : obs.nivel_logrado === 'en_inicio' ? 'En Inicio' : 'En Desarrollo'}
                          </span>
                        </div>
                      </div>

                      <p className="text-xs sm:text-sm text-[#2d2f34] leading-relaxed font-sans font-normal">
                        "{obs.texto_anonimizado}"
                      </p>

                      <div className="flex items-center justify-between text-[11px] text-[#5e646e] pt-2 border-t border-[#ecedef]">
                        <span>Indicador: <strong className="text-[#3f434a]">{obs.indicador_logro}</strong></span>
                        <span>Registrado por: {obs.educadora_responsable}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#ecedef] bg-white flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 text-xs font-medium text-[#2d2f34] bg-[#f9efe4] hover:bg-[#ecedef] rounded-full transition"
          >
            Cerrar Ficha
          </button>
        </div>
      </div>
    </div>
  );
};
