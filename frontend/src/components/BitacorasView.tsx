import React, { useState } from 'react';
import { BookOpen, Check, Edit3, Sparkles, Printer, RotateCcw, FileText } from 'lucide-react';
import confetti from 'canvas-confetti';
import { BitacoraQuincenal, Parvulo, Observacion } from '../types/avista';
import { aiService } from '../services/aiService';

interface BitacorasViewProps {
  bitacoras: BitacoraQuincenal[];
  parvulos: Parvulo[];
  observaciones: Observacion[];
  onUpdateBitacora: (bitacora: BitacoraQuincenal) => void;
  onAddBitacora: (bitacora: BitacoraQuincenal) => void;
  initialSelectedChildId?: string;
}

export const BitacorasView: React.FC<BitacorasViewProps> = ({
  bitacoras,
  parvulos,
  observaciones,
  onUpdateBitacora,
  onAddBitacora,
  initialSelectedChildId
}) => {
  const [selectedChildId, setSelectedChildId] = useState<string>(
    initialSelectedChildId || parvulos[0]?.id || 'NI-1001'
  );
  const [isEditing, setIsEditing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const currentChild = parvulos.find(p => p.id === selectedChildId) || parvulos[0];
  const currentBitacora = bitacoras.find(b => b.id_nino === selectedChildId);
  const childObs = observaciones.filter(o => o.id_nino === selectedChildId);

  const [resumen, setResumen] = useState('');
  const [personalSocial, setPersonalSocial] = useState('');
  const [comunicacion, setComunicacion] = useState('');
  const [entorno, setEntorno] = useState('');
  const [estrategia, setEstrategia] = useState('');

  React.useEffect(() => {
    if (currentBitacora) {
      setResumen(currentBitacora.resumen_ejecutivo);
      setPersonalSocial(currentBitacora.desarrollo_personal_social);
      setComunicacion(currentBitacora.comunicacion_integral);
      setEntorno(currentBitacora.interaccion_entorno);
      setEstrategia(currentBitacora.estrategia_aula_sugerida);
      setIsEditing(false);
    }
  }, [currentBitacora, selectedChildId]);

  const handleGenerateWithAI = async () => {
    setIsGenerating(true);
    try {
      const generated = await aiService.generateBitacora(currentChild, childObs);
      onAddBitacora(generated);
      setResumen(generated.resumen_ejecutivo);
      setPersonalSocial(generated.desarrollo_personal_social);
      setComunicacion(generated.comunicacion_integral);
      setEntorno(generated.interaccion_entorno);
      setEstrategia(generated.estrategia_aula_sugerida);
    } catch (err) {
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAprobar = () => {
    if (!currentBitacora) return;
    const updated: BitacoraQuincenal = {
      ...currentBitacora,
      resumen_ejecutivo: resumen,
      desarrollo_personal_social: personalSocial,
      comunicacion_integral: comunicacion,
      interaccion_entorno: entorno,
      estrategia_aula_sugerida: estrategia,
      estado: 'aprobada',
      fecha_aprobacion: new Date().toISOString().split('T')[0],
      firmado_por: 'Tía Marcela Valenzuela (Educadora Guía Sala SG-A)'
    };
    onUpdateBitacora(updated);
    setIsEditing(false);

    try {
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.7 }
      });
    } catch (e) {}
  };

  const handleGuardarCambios = () => {
    if (!currentBitacora) return;
    const updated: BitacoraQuincenal = {
      ...currentBitacora,
      resumen_ejecutivo: resumen,
      desarrollo_personal_social: personalSocial,
      comunicacion_integral: comunicacion,
      interaccion_entorno: entorno,
      estrategia_aula_sugerida: estrategia,
      estado: 'en_revision'
    };
    onUpdateBitacora(updated);
    setIsEditing(false);
  };

  return (
    <div className="space-y-8 max-w-[1200px] mx-auto">
      {/* Editorial Principle Banner in Dust Sand */}
      <div className="bg-[#f9efe4] border border-[#ecedef] rounded-[32px] p-6 flex flex-col sm:flex-row items-start gap-4">
        <div className="w-10 h-10 rounded-full bg-[#f67748] text-white flex items-center justify-center shrink-0 shadow-xs">
          <BookOpen className="w-5 h-5" />
        </div>
        <div className="space-y-1">
          <h2 className="font-serif text-lg font-medium text-[#2d2f34]">
            Cuaderno Pedagógico Quincenal · "Human-in-the-Loop"
          </h2>
          <p className="text-xs sm:text-sm text-[#3f434a] leading-relaxed font-sans">
            Avista redacta un borrador fundamentado en las observaciones de aula de la quincena.{' '}
            <strong className="text-[#2d2f34]">La decisión final siempre es de la persona:</strong> la educadora revisa, ajusta cada párrafo o aprueba con su firma. La IA propone; el criterio humano decide.
          </p>
        </div>
      </div>

      {/* Main Grid: Selector column + Bitácora Document */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Children list (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold text-[#5e646e] uppercase tracking-wider">
              Párvulos Sala SG-A
            </span>
            <span className="text-xs text-[#3f434a] font-medium">
              {bitacoras.filter(b => b.estado === 'aprobada').length} de {parvulos.length} visadas
            </span>
          </div>

          <div className="bg-white rounded-[24px] border border-[#ecedef] divide-y divide-[#ecedef] max-h-[620px] overflow-y-auto shadow-subtle">
            {parvulos.map((p) => {
              const b = bitacoras.find(bit => bit.id_nino === p.id);
              const isSelected = p.id === selectedChildId;
              const obsCount = observaciones.filter(o => o.id_nino === p.id).length;

              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedChildId(p.id)}
                  className={`w-full p-3.5 text-left transition-all flex items-center justify-between min-h-[58px] ${
                    isSelected ? 'bg-[#f9efe4] border-l-2 border-[#f67748]' : 'hover:bg-[#fdf9f4]'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-full bg-[#fdf9f4] border border-[#ecedef] text-[#2d2f34] text-[11px] font-mono font-medium flex items-center justify-center">
                      {p.id.replace('NI-', '')}
                    </span>
                    <div>
                      <span className="text-xs font-semibold text-[#2d2f34] block truncate max-w-[150px]">
                        {p.alias_pedagogico}
                      </span>
                      <span className="text-[11px] text-[#5e646e]">
                        {obsCount} obs · {p.edad_meses}m
                      </span>
                    </div>
                  </div>

                  {b ? (
                    b.estado === 'aprobada' ? (
                      <span className="text-[10px] font-medium text-[#479a53] bg-[#fdf9f4] border border-[#bbf7d0] px-2.5 py-0.5 rounded-full">
                        Visada
                      </span>
                    ) : (
                      <span className="text-[10px] font-medium text-[#f67748] bg-[#fdf9f4] border border-[#f67748]/30 px-2.5 py-0.5 rounded-full">
                        Borrador IA
                      </span>
                    )
                  ) : (
                    <span className="text-[10px] text-[#9da3af]">Sin borrador</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Bitácora Document (8 cols) — Slite White Product Card */}
        <div className="lg:col-span-8">
          {currentBitacora ? (
            <div className="bg-white rounded-[32px] border border-[#ecedef] shadow-product overflow-hidden">
              {/* Document Top Bar */}
              <div className="px-6 py-5 border-b border-[#ecedef] flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#fdf9f4]/60">
                <div>
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs px-2.5 py-0.5 bg-[#f9efe4] rounded-full font-medium text-[#3f434a] border border-[#ecedef]">
                      {currentChild.id}
                    </span>
                    <h3 className="font-serif text-xl font-medium text-[#2d2f34]">
                      {currentChild.alias_pedagogico}
                    </h3>
                  </div>
                  <p className="text-xs text-[#5e646e] mt-0.5">
                    {currentBitacora.periodo} · {currentBitacora.observaciones_computadas} observaciones computadas
                  </p>
                </div>

                {/* Status Indicator */}
                <div>
                  {currentBitacora.estado === 'aprobada' ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#fdf9f4] text-[#479a53] border border-[#bbf7d0] rounded-full text-xs font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#479a53]" />
                      Visada por Educadora
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#fdf9f4] text-[#f67748] border border-[#f67748]/30 rounded-full text-xs font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#f67748]" />
                      Borrador propuesto por IA
                    </span>
                  )}
                </div>
              </div>

              {/* Document Editorial Content */}
              <div className="p-6 sm:p-8 space-y-6 text-xs sm:text-sm">
                {/* Resumen Ejecutivo */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="font-serif text-sm font-semibold text-[#2d2f34]">
                      Síntesis de Progreso General
                    </label>
                    {!isEditing && (
                      <button
                        onClick={() => setIsEditing(true)}
                        className="text-xs text-[#3f434a] hover:text-[#2d2f34] flex items-center gap-1 font-medium bg-[#f9efe4] px-3 py-1 rounded-full border border-[#ecedef]"
                      >
                        <Edit3 className="w-3 h-3" /> Editar Párrafos
                      </button>
                    )}
                  </div>
                  {isEditing ? (
                    <textarea
                      value={resumen}
                      onChange={(e) => setResumen(e.target.value)}
                      rows={3}
                      className="w-full p-3.5 text-xs sm:text-sm bg-[#fdf9f4] border border-[#ecedef] rounded-2xl focus:ring-1 focus:ring-[#f67748] focus:border-[#f67748] text-[#2d2f34] leading-relaxed"
                    />
                  ) : (
                    <p className="text-[#3f434a] leading-relaxed bg-[#fdf9f4] p-4 rounded-2xl border border-[#ecedef] font-sans">
                      {resumen}
                    </p>
                  )}
                </div>

                {/* 3 Ámbitos Curriculares */}
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-semibold text-[#5e646e] uppercase tracking-wider block mb-1.5">
                      1. Ámbito Desarrollo Personal y Social
                    </label>
                    {isEditing ? (
                      <textarea
                        value={personalSocial}
                        onChange={(e) => setPersonalSocial(e.target.value)}
                        rows={2}
                        className="w-full p-3 text-xs sm:text-sm bg-[#fdf9f4] border border-[#ecedef] rounded-2xl focus:ring-1 focus:ring-[#f67748]"
                      />
                    ) : (
                      <p className="text-[#3f434a] leading-relaxed bg-[#fdf9f4] p-3.5 rounded-2xl border border-[#ecedef] font-sans">
                        {personalSocial}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-[#5e646e] uppercase tracking-wider block mb-1.5">
                      2. Ámbito Comunicación Integral
                    </label>
                    {isEditing ? (
                      <textarea
                        value={comunicacion}
                        onChange={(e) => setComunicacion(e.target.value)}
                        rows={2}
                        className="w-full p-3 text-xs sm:text-sm bg-[#fdf9f4] border border-[#ecedef] rounded-2xl focus:ring-1 focus:ring-[#f67748]"
                      />
                    ) : (
                      <p className="text-[#3f434a] leading-relaxed bg-[#fdf9f4] p-3.5 rounded-2xl border border-[#ecedef] font-sans">
                        {comunicacion}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-[#5e646e] uppercase tracking-wider block mb-1.5">
                      3. Ámbito Interacción y Comprensión del Entorno
                    </label>
                    {isEditing ? (
                      <textarea
                        value={entorno}
                        onChange={(e) => setEntorno(e.target.value)}
                        rows={2}
                        className="w-full p-3 text-xs sm:text-sm bg-[#fdf9f4] border border-[#ecedef] rounded-2xl focus:ring-1 focus:ring-[#f67748]"
                      />
                    ) : (
                      <p className="text-[#3f434a] leading-relaxed bg-[#fdf9f4] p-3.5 rounded-2xl border border-[#ecedef] font-sans">
                        {entorno}
                      </p>
                    )}
                  </div>
                </div>

                {/* Estrategia de Aula en Dust Sand callout */}
                <div className="p-4 bg-[#f9efe4] rounded-2xl border border-[#ecedef]">
                  <label className="font-serif text-sm font-semibold text-[#2d2f34] block mb-1">
                    Estrategia de Andamiaje Sugerida para el Aula
                  </label>
                  {isEditing ? (
                    <textarea
                      value={estrategia}
                      onChange={(e) => setEstrategia(e.target.value)}
                      rows={2}
                      className="w-full p-3 text-xs sm:text-sm bg-white border border-[#ecedef] rounded-xl focus:ring-1 focus:ring-[#f67748]"
                    />
                  ) : (
                    <p className="text-[#3f434a] leading-relaxed font-sans">
                      {estrategia}
                    </p>
                  )}
                </div>

                {/* Signature Block */}
                {currentBitacora.firmado_por && (
                  <div className="pt-4 border-t border-[#ecedef] flex items-center justify-between text-xs text-[#5e646e]">
                    <span>Firmado pedagógicamente por: <strong className="text-[#2d2f34]">{currentBitacora.firmado_por}</strong></span>
                    <span>Fecha: {currentBitacora.fecha_aprobacion || currentBitacora.fecha_corte}</span>
                  </div>
                )}
              </div>

              {/* Action Toolbar */}
              <div className="px-6 py-4 border-t border-[#ecedef] bg-[#fdf9f4] flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => window.print()}
                    className="min-h-[40px] px-4 py-2 text-xs font-medium text-[#2d2f34] hover:bg-[#f9efe4] border border-[#d9dde6] rounded-full transition flex items-center gap-1.5"
                  >
                    <Printer className="w-3.5 h-3.5 text-[#5e646e]" />
                    <span>Imprimir Documento</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleGenerateWithAI}
                    disabled={isGenerating}
                    className="min-h-[40px] px-4 py-2 text-xs font-medium text-[#3f434a] hover:text-[#2d2f34] bg-white border border-[#ecedef] hover:bg-[#f9efe4] rounded-full transition flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <RotateCcw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin text-[#f67748]' : ''}`} />
                    <span>{isGenerating ? 'Regenerando...' : 'Re-generar con IA'}</span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  {isEditing && (
                    <button
                      type="button"
                      onClick={handleGuardarCambios}
                      className="min-h-[40px] px-4 py-2 text-xs font-medium text-[#2d2f34] bg-[#f9efe4] hover:bg-[#ecedef] rounded-full transition"
                    >
                      Guardar Cambios
                    </button>
                  )}

                  {/* Primary CTA: Slite Ember Pill Button */}
                  <button
                    type="button"
                    onClick={handleAprobar}
                    className="min-h-[40px] px-6 py-2.5 text-xs sm:text-sm font-medium text-white bg-[#f67748] hover:bg-[#e46436] active:scale-95 rounded-full shadow-xs transition flex items-center gap-2"
                  >
                    <Check className="w-4 h-4" />
                    <span>Aprobar y Visar Bitácora</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Empty State */
            <div className="bg-white rounded-[32px] border border-[#ecedef] p-10 text-center space-y-4 shadow-product">
              <div className="w-12 h-12 rounded-full bg-[#f9efe4] text-[#2d2f34] flex items-center justify-center mx-auto">
                <FileText className="w-6 h-6 text-[#f67748]" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="font-serif text-lg font-medium text-[#2d2f34]">
                  Sin bitácora para {currentChild.alias_pedagogico}
                </h3>
                <p className="text-xs text-[#5e646e] leading-relaxed">
                  Hay {childObs.length} observaciones registradas para este párvulo en la quincena actual. 
                  Avista puede consolidarlas en un borrador formal listo para tu revisión.
                </p>
              </div>

              <button
                type="button"
                onClick={handleGenerateWithAI}
                disabled={isGenerating}
                className="min-h-[44px] px-6 py-2.5 bg-[#f67748] hover:bg-[#e46436] active:scale-95 text-white text-xs sm:text-sm font-medium rounded-full shadow-xs transition inline-flex items-center gap-2 disabled:opacity-50"
              >
                <Sparkles className={`w-4 h-4 ${isGenerating ? 'animate-spin' : ''}`} />
                <span>{isGenerating ? 'Redactando borrador con IA...' : 'Generar Borrador Quincenal con IA'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
