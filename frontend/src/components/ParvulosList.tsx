import React, { useState } from 'react';
import { Search, Plus, Eye, CheckCircle2, Clock, Sparkles } from 'lucide-react';
import { Parvulo, Observacion } from '../types/avista';

interface ParvulosListProps {
  parvulos: Parvulo[];
  observaciones: Observacion[];
  onSelectParvulo: (parvulo: Parvulo) => void;
  onOpenCaptureForParvulo: (parvuloId: string) => void;
}

export const ParvulosList: React.FC<ParvulosListProps> = ({
  parvulos,
  observaciones,
  onSelectParvulo,
  onOpenCaptureForParvulo
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroCobertura, setFiltroCobertura] = useState<'todos' | 'optimo' | 'adecuado' | 'pendiente'>('todos');

  // Compute live count of observations per child
  const getObsCount = (id: string) => observaciones.filter(o => o.id_nino === id).length;

  const filtered = parvulos.filter(p => {
    const matchesSearch = 
      p.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.alias_pedagogico.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (!matchesSearch) return false;

    const count = getObsCount(p.id);
    let state: 'optimo' | 'adecuado' | 'pendiente' = 'adecuado';
    if (count >= 5) state = 'optimo';
    else if (count <= 2) state = 'pendiente';

    if (filtroCobertura === 'todos') return true;
    return state === filtroCobertura;
  });

  const totalObservaciones = observaciones.length;
  const pendientesCount = parvulos.filter(p => getObsCount(p.id) <= 2).length;

  return (
    <div className="space-y-10 max-w-[1200px] mx-auto">
      {/* Editorial Hero Header — Slite parchment aesthetic with terracotta scribble annotation */}
      <div className="text-center pt-4 pb-2 space-y-4 max-w-3xl mx-auto">
        {/* Dust Tag Chips Row */}
        <div className="flex items-center justify-center gap-2 flex-wrap">
          <span className="px-3.5 py-1 text-xs font-medium bg-[#f9efe4] text-[#3f434a] rounded-full border border-[#ecedef]">
            Fundación Integra · Sala SG-A
          </span>
          <span className="px-3.5 py-1 text-xs font-medium bg-[#f9efe4] text-[#3f434a] rounded-full border border-[#ecedef]">
            Dataset E-1 Oficial Seudonimizado
          </span>
          <span className="px-3.5 py-1 text-xs font-medium bg-[#f9efe4] text-[#479a53] rounded-full border border-[#ecedef] flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#479a53]" />
            Herramienta Pedagógica
          </span>
        </div>

        {/* Garnett/Lora Headline with Ember Scribble Annotation */}
        <h1 className="font-serif text-3xl sm:text-5xl text-[#2d2f34] tracking-tight leading-[1.25]">
          IA que{' '}
          <span className="relative inline-block px-1.5 mx-0.5">
            <span className="relative z-10">observa</span>
            {/* Hand-drawn terracotta oval stroke */}
            <svg 
              className="absolute -inset-x-2 -inset-y-1 w-[calc(100%+16px)] h-[calc(100%+10px)] text-[#f67748] pointer-events-none" 
              viewBox="0 0 120 44" 
              fill="none" 
              preserveAspectRatio="none"
            >
              <path 
                d="M8 22 C 16 8, 104 6, 114 18 C 120 28, 88 40, 32 38 C 12 37, 2 27, 20 16" 
                stroke="currentColor" 
                strokeWidth="1.8" 
                strokeLinecap="round" 
              />
            </svg>
          </span>{' '}
          junto a la educadora y le devuelve tiempo para los niños.
        </h1>

        <p className="text-base sm:text-lg text-[#3f434a] leading-relaxed max-w-2xl mx-auto font-sans font-normal">
          Convierte notas rápidas, audios de sala y fotos de apuntes en bitácoras quincenales listas para visar.
          Llevamos esas ~4 horas semanales de informes hacia casi cero.
        </p>

        {/* 4 Metric Summary in Cream Feature Container (32px radius) */}
        <div className="bg-[#f9efe4] rounded-[32px] p-5 sm:p-6 border border-[#ecedef] mt-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-left">
            <div>
              <span className="text-xs text-[#5e646e] block font-sans">Párvulos en Sala</span>
              <span className="font-serif text-2xl sm:text-3xl text-[#2d2f34] font-medium tabular-nums">19</span>
              <span className="text-[11px] text-[#5e646e] block mt-0.5">Nivel Medio Menor</span>
            </div>
            <div>
              <span className="text-xs text-[#5e646e] block font-sans">Observaciones Computadas</span>
              <span className="font-serif text-2xl sm:text-3xl text-[#2d2f34] font-medium tabular-nums">{totalObservaciones}</span>
              <span className="text-[11px] text-[#5e646e] block mt-0.5">En esta quincena</span>
            </div>
            <div>
              <span className="text-xs text-[#5e646e] block font-sans">Cobertura de Sala</span>
              <span className="font-serif text-2xl sm:text-3xl text-[#479a53] font-medium tabular-nums">
                {Math.round(((parvulos.length - pendientesCount) / parvulos.length) * 100)}%
              </span>
              <span className="text-[11px] text-[#5e646e] block mt-0.5">{parvulos.length - pendientesCount} de {parvulos.length} niños cubiertos</span>
            </div>
            <div>
              <span className="text-xs text-[#5e646e] block font-sans">Tiempo Ahorrado</span>
              <span className="font-serif text-2xl sm:text-3xl text-[#f67748] font-medium tabular-nums">~3.8 hrs</span>
              <span className="text-[11px] text-[#5e646e] block mt-0.5">Semanales devueltas</span>
            </div>
          </div>
        </div>
      </div>

      {/* Toolbar: Search and Dust Pill Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
        {/* Search Input on White Product surface */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9da3af]" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por seudónimo (ej. NI-1001) o alias..."
            className="w-full pl-10 pr-4 py-2 text-xs sm:text-sm bg-white border border-[#ecedef] rounded-full focus:ring-1 focus:ring-[#f67748] focus:border-[#f67748] text-[#2d2f34] placeholder:text-[#9da3af] shadow-xs"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 bg-[#f9efe4] border border-[#ecedef] rounded-full overflow-x-auto">
          <button
            onClick={() => setFiltroCobertura('todos')}
            className={`min-h-[34px] px-3.5 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
              filtroCobertura === 'todos'
                ? 'bg-[#2d2f34] text-white shadow-xs'
                : 'text-[#5e646e] hover:text-[#2d2f34]'
            }`}
          >
            Todos ({parvulos.length})
          </button>
          <button
            onClick={() => setFiltroCobertura('optimo')}
            className={`min-h-[34px] px-3.5 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
              filtroCobertura === 'optimo'
                ? 'bg-[#2d2f34] text-white shadow-xs'
                : 'text-[#5e646e] hover:text-[#2d2f34]'
            }`}
          >
            Óptima (5+)
          </button>
          <button
            onClick={() => setFiltroCobertura('adecuado')}
            className={`min-h-[34px] px-3.5 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
              filtroCobertura === 'adecuado'
                ? 'bg-[#2d2f34] text-white shadow-xs'
                : 'text-[#5e646e] hover:text-[#2d2f34]'
            }`}
          >
            Adecuada (3-4)
          </button>
          <button
            onClick={() => setFiltroCobertura('pendiente')}
            className={`min-h-[34px] px-3.5 py-1 text-xs font-medium rounded-full transition-all whitespace-nowrap ${
              filtroCobertura === 'pendiente'
                ? 'bg-[#2d2f34] text-white shadow-xs'
                : 'text-[#5e646e] hover:text-[#2d2f34]'
            }`}
          >
            Pendientes ({pendientesCount})
          </button>
        </div>
      </div>

      {/* Children Cards Grid (32px radius, Slite White Product cards with 3-layer subtle shadow) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((parvulo) => {
          const obsCount = getObsCount(parvulo.id);
          const isPending = obsCount <= 2;
          const isOptimo = obsCount >= 5;

          return (
            <div
              key={parvulo.id}
              className="bg-white rounded-[32px] border border-[#ecedef] p-6 flex flex-col justify-between shadow-product hover:border-[#d9dde6] transition-all duration-150 group"
            >
              <div className="space-y-4">
                {/* Card Top: Pseudonym badge + Alias */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="text-[11px] font-mono font-medium text-[#6a707c] bg-[#f9efe4] px-2.5 py-0.5 rounded-full inline-block mb-1.5">
                      {parvulo.id}
                    </span>
                    <h3 className="font-serif text-lg font-medium text-[#2d2f34] group-hover:text-[#f67748] transition-colors">
                      {parvulo.alias_pedagogico}
                    </h3>
                    <p className="text-xs text-[#5e646e] mt-0.5">
                      {parvulo.edad_meses} meses · {parvulo.genero_seudonimo === 'M' ? 'Párvulo' : 'Párvula'} · Sala {parvulo.sala}
                    </p>
                  </div>

                  <span className={`text-[11px] font-medium px-2.5 py-1 rounded-full border ${
                    isOptimo 
                      ? 'bg-[#fdf9f4] text-[#479a53] border-[#bbf7d0]' 
                      : isPending 
                        ? 'bg-[#fdf9f4] text-[#f67748] border-[#f67748]/30' 
                        : 'bg-[#fdf9f4] text-[#5e646e] border-[#ecedef]'
                  }`}>
                    {isOptimo ? 'Óptima' : isPending ? 'Atención' : 'Adecuada'}
                  </span>
                </div>

                {/* Unboxed Metadata & Metrics */}
                <div className="flex items-center gap-2 text-xs text-[#5e646e] pt-2 border-t border-[#ecedef]">
                  <span className="font-medium text-[#3f434a]">{parvulo.nivel_actual}</span>
                  <span className="text-[#9da3af]">·</span>
                  <span className="tabular-nums font-semibold text-[#2d2f34]">
                    {obsCount} {obsCount === 1 ? 'registro' : 'registros'}
                  </span>
                </div>

                {/* Observation Snippet (feels like handwritten classroom note) */}
                <div className="p-3 bg-[#fdf9f4] rounded-2xl border border-[#ecedef] min-h-[72px]">
                  {(() => {
                    const lastObs = observaciones.filter(o => o.id_nino === parvulo.id).slice(-1)[0];
                    if (!lastObs) {
                      return (
                        <p className="text-xs text-[#9da3af] italic py-2">
                          Sin observaciones registradas en el ciclo actual.
                        </p>
                      );
                    }
                    return (
                      <div>
                        <span className="text-[10px] text-[#6a707c] uppercase font-medium tracking-wider block mb-0.5">
                          Último apunte ({lastObs.fecha}):
                        </span>
                        <p className="text-xs text-[#3f434a] line-clamp-2 leading-relaxed font-sans">
                          "{lastObs.texto_anonimizado}"
                        </p>
                      </div>
                    );
                  })()}
                </div>
              </div>

              {/* Card Bottom Pill Actions */}
              <div className="flex items-center gap-2 pt-4 mt-2 border-t border-[#ecedef]">
                <button
                  type="button"
                  onClick={() => onSelectParvulo(parvulo)}
                  className="flex-1 min-h-[40px] px-3 py-2 text-xs font-medium text-[#2d2f34] bg-[#f9efe4] hover:bg-[#ecedef] rounded-full transition flex items-center justify-center gap-1.5"
                >
                  <Eye className="w-3.5 h-3.5 text-[#5e646e]" />
                  <span>Ver Ficha</span>
                </button>

                <button
                  type="button"
                  onClick={() => onOpenCaptureForParvulo(parvulo.id)}
                  className="min-h-[40px] px-4 py-2 text-xs font-medium text-[#2d2f34] hover:text-white hover:bg-[#f67748] border border-[#d9dde6] hover:border-transparent rounded-full transition-all flex items-center justify-center gap-1.5"
                  title="Añadir nota rápida"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Observar</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
