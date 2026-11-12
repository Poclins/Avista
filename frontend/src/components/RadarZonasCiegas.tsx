import React, { useState } from 'react';
import { EyeOff, AlertCircle, Compass, Sparkles, Check, ArrowRight, Plus, HelpCircle, ShieldCheck } from 'lucide-react';
import { Parvulo, Observacion, AmbitoCurricular, NucleoCurricular } from '../types/avista';

interface RadarZonasCiegasProps {
  parvulos: Parvulo[];
  observaciones: Observacion[];
  onOpenCaptureForParvulo: (childId: string) => void;
}

export const RadarZonasCiegas: React.FC<RadarZonasCiegasProps> = ({
  parvulos,
  observaciones,
  onOpenCaptureForParvulo
}) => {
  const [filtroUrgencia, setFiltroUrgencia] = useState<'todos' | 'alta' | 'media' | 'optima'>('todos');

  // Compute metrics per child
  const childrenMetrics = parvulos.map(p => {
    const childObs = observaciones.filter(o => o.id_nino === p.id);
    const countPersonal = childObs.filter(o => o.ambito === 'desarrollo_personal').length;
    const countComunicacion = childObs.filter(o => o.ambito === 'comunicacion_integral').length;
    const countEntorno = childObs.filter(o => o.ambito === 'interaccion_entorno').length;

    const ambitosVacios: AmbitoCurricular[] = [];
    if (countPersonal === 0) ambitosVacios.push('desarrollo_personal');
    if (countComunicacion === 0) ambitosVacios.push('comunicacion_integral');
    if (countEntorno === 0) ambitosVacios.push('interaccion_entorno');

    // Urgency level
    let urgencia: 'alta' | 'media' | 'optima' = 'optima';
    if (childObs.length <= 2 || ambitosVacios.length >= 2) {
      urgencia = 'alta';
    } else if (childObs.length <= 4 || ambitosVacios.length >= 1) {
      urgencia = 'media';
    }

    let sugerencia = '';
    if (urgencia === 'alta') {
      sugerencia = `Prioridad de aula: ${p.alias_pedagogico} tiene solo ${childObs.length} registros y no registra observaciones en ${ambitosVacios.map(a => a.replace('_', ' ')).join(', ')}.`;
    } else if (urgencia === 'media') {
      sugerencia = `Registrar en ${ambitosVacios[0]?.replace('_', ' ') || 'experiencia guiada'} para balancear su informe quincenal.`;
    } else {
      sugerencia = `Cobertura saludable en los 3 ámbitos curriculares.`;
    }

    return {
      parvulo: p,
      total: childObs.length,
      countPersonal,
      countComunicacion,
      countEntorno,
      ambitosVacios,
      urgencia,
      sugerencia
    };
  });

  const altas = childrenMetrics.filter(m => m.urgencia === 'alta');
  const medias = childrenMetrics.filter(m => m.urgencia === 'media');
  const optimas = childrenMetrics.filter(m => m.urgencia === 'optima');

  const filtered = childrenMetrics.filter(m => {
    if (filtroUrgencia === 'todos') return true;
    return m.urgencia === filtroUrgencia;
  });

  // Top 3 priority missions for today
  const misionesHoy = childrenMetrics
    .filter(m => m.urgencia === 'alta' || m.urgencia === 'media')
    .slice(0, 3);

  return (
    <div className="space-y-8 max-w-[1200px] mx-auto">
      {/* Editorial Header Banner */}
      <div className="bg-[#f9efe4] border border-[#ecedef] rounded-[32px] p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#f67748]" />
            <span className="text-xs font-semibold uppercase tracking-wider text-[#f67748]">
              Equidad & Cobertura Pedagógica en Sala
            </span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-medium text-[#2d2f34]">
            Radar de Zonas Ciegas de Sala
          </h1>
          <p className="text-xs sm:text-sm text-[#3f434a] leading-relaxed font-sans">
            Evita el fenómeno del "niño invisible". Avista monitorea en tiempo real qué párvulos y qué ámbitos curriculares 
            han quedado sin documentar para asegurar que ningún niño quede sin seguimiento antes del cierre quincenal.
          </p>
        </div>

        {/* Equity Score Pill */}
        <div className="bg-white p-5 rounded-[24px] border border-[#ecedef] shadow-subtle shrink-0 text-center min-w-[180px]">
          <span className="text-xs text-[#5e646e] block font-sans">Índice de Equidad Sala</span>
          <span className="font-serif text-3xl font-medium text-[#2d2f34] tabular-nums">
            {Math.round(((parvulos.length - altas.length) / parvulos.length) * 100)}%
          </span>
          <span className="text-[11px] text-[#479a53] block mt-0.5">
            {parvulos.length - altas.length} de {parvulos.length} con seguimiento
          </span>
        </div>
      </div>

      {/* "A quién observar hoy" — Proactive Morning Mission */}
      <div className="bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-7 shadow-product space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-[#f9efe4] text-[#f67748] flex items-center justify-center font-bold">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-serif text-lg font-medium text-[#2d2f34]">
                Misiones de Observación para la Jornada de Hoy
              </h2>
              <p className="text-xs text-[#5e646e]">
                3 focos proactivos para balancear la sala durante las experiencias de hoy
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {misionesHoy.map((m, idx) => (
            <div
              key={m.parvulo.id}
              className="p-5 bg-[#fdf9f4] rounded-2xl border border-[#ecedef] flex flex-col justify-between space-y-3"
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs px-2.5 py-0.5 bg-[#f9efe4] text-[#2d2f34] rounded-full border border-[#ecedef]">
                    {m.parvulo.id}
                  </span>
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                    m.urgencia === 'alta' ? 'bg-[#fdf9f4] text-[#f67748] border-[#f67748]/30' : 'bg-[#fdf9f4] text-[#74a6f1] border-[#74a6f1]/30'
                  }`}>
                    {m.urgencia === 'alta' ? 'Prioridad Alta' : 'Reforzar Ámbito'}
                  </span>
                </div>
                <h3 className="font-serif text-base font-medium text-[#2d2f34]">
                  {m.parvulo.alias_pedagogico}
                </h3>
                <p className="text-xs text-[#3f434a] leading-relaxed font-sans">
                  {m.sugerencia}
                </p>
              </div>

              <button
                type="button"
                onClick={() => onOpenCaptureForParvulo(m.parvulo.id)}
                className="w-full min-h-[36px] py-1.5 px-3 text-xs font-medium text-[#2d2f34] hover:text-white hover:bg-[#f67748] bg-white border border-[#d9dde6] rounded-full transition flex items-center justify-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Registrar en Sala</span>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Full Classroom Heatmap Table */}
      <div className="bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-7 shadow-product space-y-4">
        {/* Table Filters */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#ecedef]">
          <h2 className="font-serif text-lg font-medium text-[#2d2f34]">
            Matriz de Cobertura Curricular por Párvulo (19)
          </h2>

          <div className="flex items-center gap-1.5 p-1 bg-[#f9efe4] border border-[#ecedef] rounded-full overflow-x-auto">
            <button
              onClick={() => setFiltroUrgencia('todos')}
              className={`min-h-[32px] px-3.5 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
                filtroUrgencia === 'todos' ? 'bg-[#2d2f34] text-white shadow-xs' : 'text-[#5e646e] hover:text-[#2d2f34]'
              }`}
            >
              Todos (19)
            </button>
            <button
              onClick={() => setFiltroUrgencia('alta')}
              className={`min-h-[32px] px-3.5 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
                filtroUrgencia === 'alta' ? 'bg-[#2d2f34] text-white shadow-xs' : 'text-[#5e646e] hover:text-[#2d2f34]'
              }`}
            >
              Zonas Ciegas ({altas.length})
            </button>
            <button
              onClick={() => setFiltroUrgencia('media')}
              className={`min-h-[32px] px-3.5 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
                filtroUrgencia === 'media' ? 'bg-[#2d2f34] text-white shadow-xs' : 'text-[#5e646e] hover:text-[#2d2f34]'
              }`}
            >
              Parcial ({medias.length})
            </button>
            <button
              onClick={() => setFiltroUrgencia('optima')}
              className={`min-h-[32px] px-3.5 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
                filtroUrgencia === 'optima' ? 'bg-[#2d2f34] text-white shadow-xs' : 'text-[#5e646e] hover:text-[#2d2f34]'
              }`}
            >
              Equilibrado ({optimas.length})
            </button>
          </div>
        </div>

        {/* Heatmap Rows */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#ecedef] text-[#5e646e]">
                <th className="py-3 px-3 font-medium">Párvulo</th>
                <th className="py-3 px-3 font-medium text-center">Total Obs.</th>
                <th className="py-3 px-3 font-medium text-center">Desarrollo Personal</th>
                <th className="py-3 px-3 font-medium text-center">Comunicación</th>
                <th className="py-3 px-3 font-medium text-center">Entorno</th>
                <th className="py-3 px-3 font-medium">Estado de Cobertura</th>
                <th className="py-3 px-3 font-medium text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#ecedef]">
              {filtered.map(m => (
                <tr key={m.parvulo.id} className="hover:bg-[#fdf9f4]/80 transition">
                  <td className="py-3.5 px-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-[#6a707c] bg-[#f9efe4] px-2 py-0.5 rounded-full">
                        {m.parvulo.id}
                      </span>
                      <span className="font-medium text-[#2d2f34]">
                        {m.parvulo.alias_pedagogico}
                      </span>
                    </div>
                  </td>

                  <td className="py-3.5 px-3 text-center font-mono font-medium text-[#2d2f34] tabular-nums">
                    {m.total}
                  </td>

                  {/* Personal y Social Cell */}
                  <td className="py-3.5 px-3 text-center">
                    <span className={`inline-block px-2.5 py-1 rounded-full text-[11px] font-mono tabular-nums ${
                      m.countPersonal === 0 ? 'bg-[#f67748]/15 text-[#f67748] font-bold' : 'bg-[#f9efe4] text-[#2d2f34]'
                    }`}>
                      {m.countPersonal === 0 ? '0 ⚠️' : m.countPersonal}
                    </span>
                  </td>

                  {/* Comunicación Cell */}
                  <td className="py-3.5 px-3 text-center">
                    <span className={`inline-block px-2.5 py-1 rounded-full text-[11px] font-mono tabular-nums ${
                      m.countComunicacion === 0 ? 'bg-[#f67748]/15 text-[#f67748] font-bold' : 'bg-[#f9efe4] text-[#2d2f34]'
                    }`}>
                      {m.countComunicacion === 0 ? '0 ⚠️' : m.countComunicacion}
                    </span>
                  </td>

                  {/* Entorno Cell */}
                  <td className="py-3.5 px-3 text-center">
                    <span className={`inline-block px-2.5 py-1 rounded-full text-[11px] font-mono tabular-nums ${
                      m.countEntorno === 0 ? 'bg-[#f67748]/15 text-[#f67748] font-bold' : 'bg-[#f9efe4] text-[#2d2f34]'
                    }`}>
                      {m.countEntorno === 0 ? '0 ⚠️' : m.countEntorno}
                    </span>
                  </td>

                  <td className="py-3.5 px-3">
                    <span className={`text-[11px] font-medium px-2.5 py-0.5 rounded-full border ${
                      m.urgencia === 'alta'
                        ? 'bg-[#fdf9f4] text-[#f67748] border-[#f67748]/30'
                        : m.urgencia === 'media'
                          ? 'bg-[#fdf9f4] text-[#74a6f1] border-[#74a6f1]/30'
                          : 'bg-[#fdf9f4] text-[#479a53] border-[#bbf7d0]'
                    }`}>
                      {m.urgencia === 'alta' ? 'Zona Ciega' : m.urgencia === 'media' ? 'Falta 1 Ámbito' : 'Equilibrado'}
                    </span>
                  </td>

                  <td className="py-3.5 px-3 text-right">
                    <button
                      type="button"
                      onClick={() => onOpenCaptureForParvulo(m.parvulo.id)}
                      className="px-3 py-1 text-xs font-medium text-[#2d2f34] bg-[#f9efe4] hover:bg-[#ecedef] rounded-full transition"
                    >
                      + Observar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
