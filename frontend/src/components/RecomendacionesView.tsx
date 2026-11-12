import React, { useState } from 'react';
import { GitPullRequest, Check, Award, MessageSquare, Quote, AlertTriangle, ArrowRight, Sparkles } from 'lucide-react';
import confetti from 'canvas-confetti';
import { RecomendacionNivel, Parvulo, Observacion, DecisionNivel } from '../types/avista';
import { aiService } from '../services/aiService';

interface RecomendacionesViewProps {
  recomendaciones: RecomendacionNivel[];
  parvulos: Parvulo[];
  observaciones: Observacion[];
  onUpdateRecomendacion: (rec: RecomendacionNivel) => void;
  onAddRecomendacion: (rec: RecomendacionNivel) => void;
  initialSelectedChildId?: string;
}

export const RecomendacionesView: React.FC<RecomendacionesViewProps> = ({
  recomendaciones,
  parvulos,
  observaciones,
  onUpdateRecomendacion,
  onAddRecomendacion
}) => {
  const [filtroDecision, setFiltroDecision] = useState<'todos' | 'avanzar' | 'mantener' | 'reforzar'>('todos');
  const [childToGenerate, setChildToGenerate] = useState<string>(parvulos[0]?.id || 'NI-1001');
  const [notaModalRecId, setNotaModalRecId] = useState<string | null>(null);
  const [notaTexto, setNotaTexto] = useState('');
  const [ajusteDecision, setAjusteDecision] = useState<DecisionNivel>('mantener');

  const filteredRecs = recomendaciones.filter(r => {
    if (filtroDecision === 'todos') return true;
    return r.decision_propuesta === filtroDecision;
  });

  const handleConfirmar = (rec: RecomendacionNivel) => {
    const updated: RecomendacionNivel = {
      ...rec,
      estado_educadora: 'confirmada',
      fecha_decision: new Date().toISOString().split('T')[0]
    };
    onUpdateRecomendacion(updated);
    try {
      confetti({ particleCount: 40, spread: 50, origin: { y: 0.7 } });
    } catch (e) {}
  };

  const handleAbrirAjuste = (rec: RecomendacionNivel) => {
    setNotaModalRecId(rec.id);
    setAjusteDecision(rec.decision_propuesta);
    setNotaTexto(rec.nota_educadora || '');
  };

  const handleGuardarAjuste = () => {
    if (!notaModalRecId) return;
    const target = recomendaciones.find(r => r.id === notaModalRecId);
    if (!target) return;

    const updated: RecomendacionNivel = {
      ...target,
      decision_propuesta: ajusteDecision,
      estado_educadora: 'ajustada',
      nota_educadora: notaTexto,
      fecha_decision: new Date().toISOString().split('T')[0]
    };
    onUpdateRecomendacion(updated);
    setNotaModalRecId(null);
  };

  const handleGenerarParaParvulo = () => {
    const child = parvulos.find(p => p.id === childToGenerate);
    if (!child) return;
    const childObs = observaciones.filter(o => o.id_nino === child.id);
    const nuevaRec = aiService.generateRecommendation(child, childObs);
    onAddRecomendacion(nuevaRec);
  };

  return (
    <div className="space-y-8 max-w-[1200px] mx-auto">
      {/* Editorial Principle Banner */}
      <div className="bg-[#f9efe4] border border-[#ecedef] rounded-[32px] p-6 flex flex-col sm:flex-row items-start gap-4">
        <div className="w-10 h-10 rounded-full bg-[#f67748] text-white flex items-center justify-center shrink-0 shadow-xs">
          <GitPullRequest className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h2 className="font-serif text-lg font-medium text-[#2d2f34]">
            Rúbrica Pedagógica con Citas de Evidencia Real
          </h2>
          <p className="text-xs sm:text-sm text-[#3f434a] leading-relaxed font-sans">
            Avista nunca decide sola ni clasifica a ciegas: cada recomendación cita los registros textuales de sala que la respaldan.{' '}
            <strong className="text-[#2d2f34]">La educadora confirma, ajusta o rechaza</strong> según su conocimiento diario de cada párvulo.
          </p>
        </div>
      </div>

      {/* Toolbar & Filters (Slite pill buttons) */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 p-1 bg-[#f9efe4] border border-[#ecedef] rounded-full overflow-x-auto">
          <button
            onClick={() => setFiltroDecision('todos')}
            className={`min-h-[34px] px-4 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
              filtroDecision === 'todos' ? 'bg-[#2d2f34] text-white shadow-xs' : 'text-[#5e646e] hover:text-[#2d2f34]'
            }`}
          >
            Todas ({recomendaciones.length})
          </button>
          <button
            onClick={() => setFiltroDecision('avanzar')}
            className={`min-h-[34px] px-4 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
              filtroDecision === 'avanzar' ? 'bg-[#2d2f34] text-white shadow-xs' : 'text-[#5e646e] hover:text-[#2d2f34]'
            }`}
          >
            Avanzar ({recomendaciones.filter(r => r.decision_propuesta === 'avanzar').length})
          </button>
          <button
            onClick={() => setFiltroDecision('mantener')}
            className={`min-h-[34px] px-4 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
              filtroDecision === 'mantener' ? 'bg-[#2d2f34] text-white shadow-xs' : 'text-[#5e646e] hover:text-[#2d2f34]'
            }`}
          >
            Mantener ({recomendaciones.filter(r => r.decision_propuesta === 'mantener').length})
          </button>
          <button
            onClick={() => setFiltroDecision('reforzar')}
            className={`min-h-[34px] px-4 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
              filtroDecision === 'reforzar' ? 'bg-[#2d2f34] text-white shadow-xs' : 'text-[#5e646e] hover:text-[#2d2f34]'
            }`}
          >
            Refuerzo Focalizado ({recomendaciones.filter(r => r.decision_propuesta === 'reforzar').length})
          </button>
        </div>

        {/* Generate recommendation for another child */}
        <div className="flex items-center gap-2">
          <select
            value={childToGenerate}
            onChange={(e) => setChildToGenerate(e.target.value)}
            className="text-xs bg-white border border-[#ecedef] rounded-full px-4 py-2 font-medium text-[#2d2f34] shadow-xs"
          >
            {parvulos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id} ({p.alias_pedagogico})
              </option>
            ))}
          </select>
          <button
            onClick={handleGenerarParaParvulo}
            className="min-h-[36px] px-4 py-1.5 text-xs font-medium text-[#2d2f34] hover:text-white hover:bg-[#f67748] border border-[#d9dde6] rounded-full transition-all flex items-center gap-1.5 whitespace-nowrap shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#f67748]" />
            <span>Evaluar Rúbrica</span>
          </button>
        </div>
      </div>

      {/* Recommendations Cards List (32px cards, Slite aesthetic) */}
      <div className="space-y-6">
        {filteredRecs.map((rec) => {
          const child = parvulos.find(p => p.id === rec.id_nino) || {
            alias_pedagogico: `Párvulo ${rec.id_nino}`,
            edad_meses: 30,
            nivel_actual: 'Medio Menor'
          };

          const isAvanzar = rec.decision_propuesta === 'avanzar';
          const isReforzar = rec.decision_propuesta === 'reforzar';

          return (
            <div
              key={rec.id}
              className="bg-white rounded-[32px] border border-[#ecedef] shadow-product overflow-hidden transition-all duration-150"
            >
              {/* Card Header */}
              <div className="p-6 sm:p-7 border-b border-[#ecedef] flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#fdf9f4]/60">
                <div className="flex items-center gap-3">
                  <span className="w-10 h-10 rounded-full bg-[#f9efe4] text-[#2d2f34] font-mono font-medium text-xs flex items-center justify-center border border-[#ecedef]">
                    {rec.id_nino.replace('NI-', '')}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-serif text-lg font-medium text-[#2d2f34]">
                        {child.alias_pedagogico}
                      </h3>
                      <span className="font-mono text-xs text-[#6a707c]">
                        {rec.id_nino}
                      </span>
                    </div>
                    <span className="text-xs text-[#5e646e]">
                      Nivel actual: {child.nivel_actual} · {child.edad_meses} meses
                    </span>
                  </div>
                </div>

                {/* Proposed decision badge */}
                <div className="flex items-center gap-3">
                  <span className={`px-3.5 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 border ${
                    isAvanzar 
                      ? 'bg-[#fdf9f4] text-[#479a53] border-[#bbf7d0]' 
                      : isReforzar 
                        ? 'bg-[#fdf9f4] text-[#f67748] border-[#f67748]/30' 
                        : 'bg-[#fdf9f4] text-[#3f434a] border-[#ecedef]'
                  }`}>
                    {isAvanzar && <Award className="w-3.5 h-3.5 text-[#479a53]" />}
                    {isReforzar && <AlertTriangle className="w-3.5 h-3.5 text-[#f67748]" />}
                    {!isAvanzar && !isReforzar && <ArrowRight className="w-3.5 h-3.5 text-[#74a6f1]" />}
                    <span className="capitalize">
                      Propuesta: {rec.decision_propuesta === 'avanzar' ? 'Avanzar de Tramo' : rec.decision_propuesta === 'reforzar' ? 'Refuerzo Focalizado' : 'Mantener y Consolidar'}
                    </span>
                  </span>

                  <span className="text-xs text-[#6a707c] tabular-nums font-mono">
                    {Math.round(rec.confianza_rubrica * 100)}% conf.
                  </span>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-6 sm:p-7 space-y-5 text-xs sm:text-sm">
                {/* Fundamentación */}
                <div>
                  <span className="text-[11px] font-semibold text-[#5e646e] uppercase tracking-wider block mb-1.5">
                    Fundamentación de la Rúbrica Pedagógica
                  </span>
                  <p className="text-[#3f434a] leading-relaxed bg-[#fdf9f4] p-4 rounded-2xl border border-[#ecedef] font-sans">
                    {rec.fundamentacion_pedagogica}
                  </p>
                </div>

                {/* Evidencias Reales Citadas */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Quote className="w-4 h-4 text-[#f67748]" />
                    <span className="font-serif text-sm font-semibold text-[#2d2f34]">
                      Evidencias Reales de Aula Citadas ({rec.evidencias.length})
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {rec.evidencias.map((ev, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 bg-[#fdf9f4] rounded-2xl border border-[#ecedef] space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-mono text-[#2d2f34] font-medium">{ev.observacion_id}</span>
                          <span className="text-[#6a707c]">{ev.fecha}</span>
                        </div>
                        <p className="text-xs text-[#3f434a] leading-relaxed font-sans">
                          "{ev.texto_cita}"
                        </p>
                        <div className="pt-1.5 border-t border-[#ecedef] text-[10px] text-[#5e646e]">
                          <strong>Relevancia:</strong> {ev.relevancia}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Nota de Educadora si existe */}
                {rec.nota_educadora && (
                  <div className="p-4 bg-[#f9efe4] rounded-2xl border border-[#ecedef] text-xs">
                    <span className="font-semibold text-[#2d2f34] block mb-0.5">Nota de la Educadora de Sala:</span>
                    <p className="text-[#3f434a] font-sans leading-relaxed">{rec.nota_educadora}</p>
                    {rec.fecha_decision && (
                      <span className="text-[10px] text-[#5e646e] mt-1 block">Visado el {rec.fecha_decision}</span>
                    )}
                  </div>
                )}
              </div>

              {/* Action Bar with Primary Ember CTA */}
              <div className="px-6 py-4 border-t border-[#ecedef] bg-[#fdf9f4] flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-[#5e646e]">Validación humana:</span>
                  <span className={`font-medium capitalize ${
                    rec.estado_educadora === 'confirmada' 
                      ? 'text-[#479a53]' 
                      : rec.estado_educadora === 'ajustada' 
                        ? 'text-[#74a6f1]' 
                        : 'text-[#f67748]'
                  }`}>
                    {rec.estado_educadora === 'confirmada' ? 'Confirmada por Educadora' : rec.estado_educadora === 'ajustada' ? 'Ajustada con Nota' : 'Pendiente de Revisión'}
                  </span>
                </div>

                <div className="flex items-center gap-2.5">
                  <button
                    onClick={() => handleAbrirAjuste(rec)}
                    className="min-h-[40px] px-4 py-2 text-xs font-medium text-[#2d2f34] hover:bg-[#f9efe4] border border-[#d9dde6] rounded-full transition flex items-center gap-1.5"
                  >
                    <MessageSquare className="w-3.5 h-3.5 text-[#5e646e]" />
                    <span>Ajustar / Agregar Nota</span>
                  </button>

                  <button
                    onClick={() => handleConfirmar(rec)}
                    className="min-h-[40px] px-5 py-2 text-xs sm:text-sm font-medium text-white bg-[#f67748] hover:bg-[#e46436] active:scale-95 rounded-full transition flex items-center gap-1.5 shadow-xs"
                  >
                    <Check className="w-4 h-4" />
                    <span>Confirmar Decisión</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Adjust Decision Modal */}
      {notaModalRecId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md bg-[#fdf9f4] rounded-[32px] shadow-product p-6 border border-[#ecedef] space-y-4">
            <h3 className="font-serif text-lg font-medium text-[#2d2f34]">
              Ajustar Decisión Pedagógica
            </h3>
            <div>
              <label className="text-xs font-semibold text-[#2d2f34] block mb-1.5">
                Decisión de la Educadora
              </label>
              <select
                value={ajusteDecision}
                onChange={(e) => setAjusteDecision(e.target.value as DecisionNivel)}
                className="w-full px-4 py-2 text-xs bg-white border border-[#ecedef] rounded-full font-medium text-[#2d2f34]"
              >
                <option value="avanzar">Avanzar de tramo / nivel</option>
                <option value="mantener">Mantener y afianzar tramo actual</option>
                <option value="reforzar">Refuerzo y andamiaje focalizado</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-[#2d2f34] block mb-1.5">
                Fundamentación o Nota de Sala
              </label>
              <textarea
                value={notaTexto}
                onChange={(e) => setNotaTexto(e.target.value)}
                rows={3}
                placeholder="Indica las razones pedagógicas del ajuste o plan de trabajo..."
                className="w-full p-3.5 text-xs bg-white border border-[#ecedef] rounded-2xl text-[#2d2f34]"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setNotaModalRecId(null)}
                className="px-4 py-2 text-xs font-medium text-[#5e646e] hover:text-[#2d2f34]"
              >
                Cancelar
              </button>
              <button
                onClick={handleGuardarAjuste}
                className="px-5 py-2 text-xs font-medium text-white bg-[#2d2f34] hover:bg-[#3f434a] rounded-full"
              >
                Guardar Decisión
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
