import React, { useState } from 'react';
import { BarChart3, Clock, AlertTriangle, Printer, CheckCircle2 } from 'lucide-react';
import { ReporteDireccion, Parvulo, Observacion } from '../types/avista';
import { JARDIN_ACTUAL } from '../data/datasetE1';

interface DireccionDashboardProps {
  reporte: ReporteDireccion;
  parvulos: Parvulo[];
  observaciones: Observacion[];
}

export const DireccionDashboard: React.FC<DireccionDashboardProps> = ({
  reporte,
  parvulos,
  observaciones
}) => {
  const [salaSeleccionada, setSalaSeleccionada] = useState<string>('SG-A');
  const [showPrintModal, setShowPrintModal] = useState<boolean>(false);

  const totalObs = observaciones.length;
  const countPersonal = observaciones.filter(o => o.ambito === 'desarrollo_personal').length;
  const countComunicacion = observaciones.filter(o => o.ambito === 'comunicacion_integral').length;
  const countEntorno = observaciones.filter(o => o.ambito === 'interaccion_entorno').length;

  const totalAmbitos = countPersonal + countComunicacion + countEntorno || 1;
  const pctPersonal = Math.round((countPersonal / totalAmbitos) * 100);
  const pctComunicacion = Math.round((countComunicacion / totalAmbitos) * 100);
  const pctEntorno = Math.round((countEntorno / totalAmbitos) * 100);

  return (
    <div className="space-y-8 max-w-[1200px] mx-auto">
      {/* Garden Header Card on Cream Parchment */}
      <div className="bg-[#f9efe4] rounded-[32px] border border-[#ecedef] p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-[#f67748] block mb-1">
            Fundación Integra · Panel de Supervisión Directiva
          </span>
          <h1 className="font-serif text-2xl sm:text-3xl font-medium text-[#2d2f34]">
            {JARDIN_ACTUAL.nombre}
          </h1>
          <p className="text-xs sm:text-sm text-[#5e646e] mt-1 font-sans">
            {JARDIN_ACTUAL.direccion} · {JARDIN_ACTUAL.region} · Código institucional: {JARDIN_ACTUAL.id}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Sala Selector Pills */}
          <div className="flex items-center gap-1.5 p-1 bg-white border border-[#ecedef] rounded-full">
            {JARDIN_ACTUAL.salasDisponibles.map((s) => (
              <button
                key={s}
                onClick={() => setSalaSeleccionada(s)}
                className={`min-h-[36px] px-3.5 py-1 text-xs font-medium rounded-full transition-all ${
                  salaSeleccionada === s
                    ? 'bg-[#2d2f34] text-white shadow-xs'
                    : 'text-[#5e646e] hover:text-[#2d2f34]'
                }`}
              >
                Sala {s} {s === 'SG-A' ? '(Demo)' : ''}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowPrintModal(true)}
            className="min-h-[44px] px-5 py-2 bg-[#f67748] hover:bg-[#e46436] active:scale-95 text-white text-xs sm:text-sm font-medium rounded-full flex items-center gap-2 shadow-xs transition"
          >
            <Printer className="w-4 h-4" />
            <span className="hidden sm:inline">Generar Reporte Institucional</span>
            <span className="sm:hidden">Reporte</span>
          </button>
        </div>
      </div>

      {/* 4 Director KPIs on Star White Product cards (32px radius with 3-layer subtle shadow) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* KPI 1 */}
        <div className="bg-white p-6 rounded-[32px] border border-[#ecedef] shadow-product space-y-2">
          <div className="flex items-center justify-between text-xs text-[#5e646e]">
            <span className="font-semibold uppercase tracking-wider">Cobertura de Párvulos</span>
            <CheckCircle2 className="w-4 h-4 text-[#479a53]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-serif text-3xl sm:text-4xl font-medium text-[#2d2f34] tabular-nums">
              {reporte.cobertura_observaciones_pct}%
            </span>
            <span className="text-xs text-[#479a53] font-medium">+6.2% vs anterior</span>
          </div>
          <p className="text-xs text-[#5e646e]">
            16 de 19 niños de Sala SG-A con observaciones suficientes para informe.
          </p>
        </div>

        {/* KPI 2: Time saved */}
        <div className="bg-white p-6 rounded-[32px] border border-[#ecedef] shadow-product space-y-2">
          <div className="flex items-center justify-between text-xs text-[#5e646e]">
            <span className="font-semibold uppercase tracking-wider">Tiempo Devuelto a Sala</span>
            <Clock className="w-4 h-4 text-[#f67748]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-serif text-3xl sm:text-4xl font-medium text-[#f67748] tabular-nums">
              3.8 hrs
            </span>
            <span className="text-xs text-[#5e646e]">sem / educadora</span>
          </div>
          <p className="text-xs text-[#5e646e]">
            Aproximadamente <strong>76 horas al mes</strong> liberadas de papeleo en el jardín.
          </p>
        </div>

        {/* KPI 3 */}
        <div className="bg-white p-6 rounded-[32px] border border-[#ecedef] shadow-product space-y-2">
          <div className="flex items-center justify-between text-xs text-[#5e646e]">
            <span className="font-semibold uppercase tracking-wider">Registros Computados</span>
            <BarChart3 className="w-4 h-4 text-[#74a6f1]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-serif text-3xl sm:text-4xl font-medium text-[#2d2f34] tabular-nums">
              {totalObs}
            </span>
            <span className="text-xs text-[#5e646e]">notas, audios y fotos</span>
          </div>
          <p className="text-xs text-[#5e646e]">
            Promedio de 5.1 observaciones por niño en este ciclo quincenal.
          </p>
        </div>

        {/* KPI 4 */}
        <div className="bg-white p-6 rounded-[32px] border border-[#ecedef] shadow-product space-y-2">
          <div className="flex items-center justify-between text-xs text-[#5e646e]">
            <span className="font-semibold uppercase tracking-wider">Alertas Tempranas</span>
            <AlertTriangle className="w-4 h-4 text-[#f67748]" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-serif text-3xl sm:text-4xl font-medium text-[#f67748] tabular-nums">
              {reporte.alertas_atencion_temprana.length}
            </span>
            <span className="text-xs text-[#6a707c]">casos prioritarios</span>
          </div>
          <p className="text-xs text-[#5e646e]">
            Para revisión y andamiaje conjunto con la educadora de sala.
          </p>
        </div>
      </div>

      {/* Middle Grid: Curricular Balance + Decision Rubric Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Curricular Balance (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-8 shadow-product space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-lg font-medium text-[#2d2f34]">
              Distribución por Ámbitos Curriculares (BCEP Integra)
            </h2>
            <span className="text-xs text-[#6a707c]">
              {totalObs} observaciones
            </span>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs font-medium mb-1.5">
                <span className="text-[#3f434a]">Desarrollo Personal y Social</span>
                <span className="font-mono text-[#2d2f34] tabular-nums">{countPersonal} ({pctPersonal}%)</span>
              </div>
              <div className="w-full h-2 bg-[#f9efe4] rounded-full overflow-hidden">
                <div className="h-full bg-[#479a53] rounded-full transition-all duration-500" style={{ width: `${pctPersonal}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium mb-1.5">
                <span className="text-[#3f434a]">Comunicación Integral</span>
                <span className="font-mono text-[#2d2f34] tabular-nums">{countComunicacion} ({pctComunicacion}%)</span>
              </div>
              <div className="w-full h-2 bg-[#f9efe4] rounded-full overflow-hidden">
                <div className="h-full bg-[#74a6f1] rounded-full transition-all duration-500" style={{ width: `${pctComunicacion}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-medium mb-1.5">
                <span className="text-[#3f434a]">Interacción y Comprensión del Entorno</span>
                <span className="font-mono text-[#2d2f34] tabular-nums">{countEntorno} ({pctEntorno}%)</span>
              </div>
              <div className="w-full h-2 bg-[#f9efe4] rounded-full overflow-hidden">
                <div className="h-full bg-[#f67748] rounded-full transition-all duration-500" style={{ width: `${pctEntorno}%` }} />
              </div>
            </div>
          </div>

          <p className="p-4 bg-[#fdf9f4] rounded-2xl border border-[#ecedef] text-xs text-[#3f434a] leading-relaxed font-sans">
            💡 <strong>Diagnóstico de Sala:</strong> Se observa una cobertura curricular balanceada. La educadora de SG-A mantiene un registro continuo de hitos con énfasis en regulación afectiva y lenguaje verbal.
          </p>
        </div>

        {/* Decision Breakdown (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-8 shadow-product space-y-4">
          <h2 className="font-serif text-lg font-medium text-[#2d2f34]">
            Recomendaciones de Nivel en Sala
          </h2>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 rounded-2xl bg-[#fdf9f4] border border-[#ecedef]">
              <div>
                <span className="text-xs font-semibold text-[#2d2f34] block">Consolidar en Tramo 2</span>
                <span className="text-[11px] text-[#5e646e]">Progreso acorde a edad</span>
              </div>
              <div className="text-right">
                <span className="font-serif text-xl font-medium text-[#2d2f34] tabular-nums">
                  {reporte.distribucion_recomendaciones.mantener}
                </span>
                <span className="text-[10px] text-[#5e646e] block">68.4%</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 rounded-2xl bg-[#fdf9f4] border border-[#ecedef]">
              <div>
                <span className="text-xs font-semibold text-[#2d2f34] block">Listos para Avanzar</span>
                <span className="text-[11px] text-[#479a53]">Hitos de Medio Mayor afianzados</span>
              </div>
              <div className="text-right">
                <span className="font-serif text-xl font-medium text-[#479a53] tabular-nums">
                  {reporte.distribucion_recomendaciones.avanzar}
                </span>
                <span className="text-[10px] text-[#5e646e] block">21.1%</span>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 rounded-2xl bg-[#fdf9f4] border border-[#ecedef]">
              <div>
                <span className="text-xs font-semibold text-[#2d2f34] block">Refuerzo Pedagógico</span>
                <span className="text-[11px] text-[#f67748]">Andamiaje individualizado</span>
              </div>
              <div className="text-right">
                <span className="font-serif text-xl font-medium text-[#f67748] tabular-nums">
                  {reporte.distribucion_recomendaciones.reforzar}
                </span>
                <span className="text-[10px] text-[#5e646e] block">10.5%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Early Attention Alerts Section */}
      <div className="bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-8 shadow-product space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[#f67748]" />
            <h2 className="font-serif text-lg font-medium text-[#2d2f34]">
              Alertas de Atención Temprana · Sala SG-A
            </h2>
          </div>
          <span className="text-xs text-[#6a707c]">
            Revisión colaborativa Directora - Educadora
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reporte.alertas_atencion_temprana.map((alerta, idx) => {
            const child = parvulos.find(p => p.id === alerta.id_nino);
            return (
              <div
                key={idx}
                className="p-4 rounded-2xl border border-[#ecedef] bg-[#fdf9f4] space-y-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-medium text-[#2d2f34]">{alerta.id_nino}</span>
                    <span className="text-[#3f434a]">({child?.alias_pedagogico})</span>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium uppercase bg-[#f9efe4] text-[#f67748] border border-[#ecedef]">
                    Prioridad {alerta.prioridad}
                  </span>
                </div>
                <p className="text-xs text-[#3f434a] leading-relaxed font-sans">
                  {alerta.motivo}
                </p>
                <div className="pt-2 border-t border-[#ecedef] flex items-center justify-between text-[11px] text-[#5e646e]">
                  <span>Acción: Protocolo de acogida y acompañamiento</span>
                  <span className="font-medium text-[#2d2f34]">Revisar con Tía Marcela</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Modal Reporte Institucional Imprimible */}
      {showPrintModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs overflow-y-auto">
          <div className="w-full max-w-2xl bg-[#fdf9f4] rounded-[32px] shadow-product p-8 border border-[#ecedef] space-y-6 my-auto max-h-[90vh] overflow-y-auto">
            {/* Header Institucional */}
            <div className="border-b-2 border-[#2d2f34] pb-4 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold uppercase text-[#f67748] tracking-wider block">
                  Fundación Integra · Región Metropolitana
                </span>
                <h3 className="font-serif text-xl font-medium text-[#2d2f34]">
                  Informe Quincenal de Cobertura y Progreso Curricular
                </h3>
                <span className="text-xs text-[#5e646e]">
                  {JARDIN_ACTUAL.nombre} ({JARDIN_ACTUAL.id}) · Sala {salaSeleccionada}
                </span>
              </div>
              <div className="text-right text-xs text-[#6a707c] font-mono">
                <span>08/11/2026</span><br />
                <span>Dataset E-1 Oficial</span>
              </div>
            </div>

            {/* Content summary */}
            <div className="space-y-4 text-xs leading-relaxed text-[#3f434a] font-sans">
              <p>
                El presente informe sintetiza las observaciones pedagógicas levantadas mediante el sistema Avista en la sala {salaSeleccionada}, registrando <strong>{totalObs} observaciones seudonimizadas</strong> en el período.
              </p>
              <div className="bg-white p-4 rounded-2xl border border-[#ecedef] grid grid-cols-2 gap-3 text-xs">
                <div><span className="text-[#5e646e]">Párvulos Matriculados:</span> <strong className="text-[#2d2f34]">19</strong></div>
                <div><span className="text-[#5e646e]">Cobertura Quincenal:</span> <strong className="text-[#479a53]">{reporte.cobertura_observaciones_pct}%</strong></div>
                <div><span className="text-[#5e646e]">Horas Docentes Liberadas:</span> <strong className="text-[#f67748]">~76 hrs/mes</strong></div>
                <div><span className="text-[#5e646e]">Casos en Alerta:</span> <strong className="text-[#2d2f34]">2</strong></div>
              </div>
              <p>
                <strong>Observación de Supervisión:</strong> La herramienta Avista ha permitido reducir la dedicación administrativa a la redacción manual de bitácoras, devolviendo tiempo presencial al equipo pedagógico de sala.
              </p>
            </div>

            {/* Signature blocks */}
            <div className="pt-6 border-t border-[#ecedef] grid grid-cols-2 gap-6 text-center text-xs text-[#3f434a]">
              <div className="pt-8 border-t border-dashed border-[#d9dde6]">
                <span className="font-semibold block text-[#2d2f34]">Tía Marcela Valenzuela</span>
                <span className="text-[11px] text-[#5e646e]">Educadora Guía Sala SG-A</span>
              </div>
              <div className="pt-8 border-t border-dashed border-[#d9dde6]">
                <span className="font-semibold block text-[#2d2f34]">Directora del Jardín</span>
                <span className="text-[11px] text-[#5e646e]">Jardín Infantil Los Copihues</span>
              </div>
            </div>

            {/* Buttons */}
            <div className="flex items-center justify-end gap-3 pt-2 border-t border-[#ecedef]">
              <button
                onClick={() => setShowPrintModal(false)}
                className="px-4 py-2 text-xs font-medium text-[#5e646e] hover:text-[#2d2f34]"
              >
                Cerrar
              </button>
              <button
                onClick={() => window.print()}
                className="px-6 py-2.5 text-xs font-medium text-white bg-[#f67748] hover:bg-[#e46436] rounded-full flex items-center gap-2"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Imprimir Documento</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
