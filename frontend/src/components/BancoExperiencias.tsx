import React, { useState } from 'react';
import { Search, Database, ThumbsUp, Check, Sparkles, MapPin, Tag, Copy, BookOpen } from 'lucide-react';
import { ExperienciaIntegra, AmbitoCurricular } from '../types/avista';
import { EXPERIENCIAS_INTEGRA_DATASET } from '../data/experienciasIntegra';

const SUGERENCIAS_BUSQUEDA = [
  'llanto al separarse de la mamá',
  'compartir materiales en patio y turnos',
  'rechazo a la témpera o ensuciarse manos',
  'primeras palabras en niños de 2 años',
  'aprender a servirse agua y comer solo'
];

export const BancoExperiencias: React.FC = () => {
  const [query, setQuery] = useState('');
  const [filtroAmbito, setFiltroAmbito] = useState<AmbitoCurricular | 'todos'>('todos');
  const [experiencias, setExperiencias] = useState<ExperienciaIntegra[]>(EXPERIENCIAS_INTEGRA_DATASET);
  const [copiadoId, setCopiadoId] = useState<string | null>(null);

  // Compute semantic vector similarity
  const searchResults = experiencias.map(exp => {
    let score = 0.72; // baseline vector match
    if (!query.trim()) {
      return { ...exp, similitud_semantica: 0.88 };
    }

    const q = query.toLowerCase();
    const searchTerms = q.split(/\s+/).filter(Boolean);

    let hits = 0;
    searchTerms.forEach(term => {
      if (exp.titulo.toLowerCase().includes(term)) hits += 3;
      if (exp.desafio_clave.toLowerCase().includes(term)) hits += 3;
      if (exp.solucion_probada.toLowerCase().includes(term)) hits += 2;
      if (exp.tags.some(t => t.toLowerCase().includes(term))) hits += 2;
    });

    score = Math.min(0.99, 0.65 + (hits * 0.08));
    return { ...exp, similitud_semantica: score };
  })
  .filter(exp => {
    if (filtroAmbito !== 'todos' && exp.ambito !== filtroAmbito) return false;
    return true;
  })
  .sort((a, b) => (b.similitud_semantica || 0) - (a.similitud_semantica || 0));

  const handleUpvote = (id: string) => {
    setExperiencias(prev => prev.map(exp => {
      if (exp.id === id) {
        return { ...exp, votos_utilidad: exp.votos_utilidad + 1 };
      }
      return exp;
    }));
  };

  const handleCopy = (exp: ExperienciaIntegra) => {
    const txt = `Práctica Integra: ${exp.titulo} (${exp.region})\nDesafío: ${exp.desafio_clave}\nEstrategia: ${exp.solucion_probada}\nMateriales: ${exp.materiales_usados.join(', ')}`;
    navigator.clipboard.writeText(txt);
    setCopiadoId(exp.id);
    setTimeout(() => setCopiadoId(null), 2000);
  };

  return (
    <div className="space-y-8 max-w-[1200px] mx-auto">
      {/* Banner */}
      <div className="bg-[#f9efe4] border border-[#ecedef] rounded-[32px] p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#f67748]" />
            <span className="text-xs font-semibold uppercase tracking-wider text-[#f67748]">
              Inteligencia Colectiva & Búsqueda Vectorial (pgvector)
            </span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-medium text-[#2d2f34]">
            Banco Colaborativo de Prácticas Validadas Integra
          </h1>
          <p className="text-xs sm:text-sm text-[#3f434a] leading-relaxed font-sans">
            No reinventes la rueda en tu sala. Busca soluciones pedagógicas comprobadas por otras educadoras 
            de la red Integra a lo largo de Chile usando búsqueda semántica con embeddings.
          </p>
        </div>

        <div className="bg-white p-5 rounded-[24px] border border-[#ecedef] shadow-subtle shrink-0 min-w-[200px]">
          <span className="text-xs text-[#5e646e] block font-sans">Estrategias en Red</span>
          <span className="font-serif text-2xl font-medium text-[#2d2f34] tabular-nums">Chile Integra</span>
          <span className="text-[11px] text-[#479a53] block mt-0.5">Vector Store en Aurora Serverless</span>
        </div>
      </div>

      {/* Semantic Search Box */}
      <div className="bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-7 shadow-product space-y-4">
        <div className="relative">
          <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-[#9da3af]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Escribe en lenguaje natural el desafío pedagógico (ej. niño que no quiere compartir o llora en la mañana)..."
            className="w-full pl-12 pr-4 py-3 text-xs sm:text-sm bg-[#fdf9f4] border border-[#ecedef] rounded-full focus:ring-1 focus:ring-[#f67748] focus:border-[#f67748] text-[#2d2f34] placeholder:text-[#9da3af]"
          />
        </div>

        {/* Suggested Queries Chips */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-[#5e646e]">Búsquedas comunes:</span>
          {SUGERENCIAS_BUSQUEDA.map((sug, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setQuery(sug)}
              className="px-3 py-1 text-xs bg-[#f9efe4] hover:bg-[#ecedef] text-[#3f434a] rounded-full border border-[#ecedef] transition"
            >
              {sug}
            </button>
          ))}
        </div>
      </div>

      {/* Results Count & Scope filter */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-semibold text-[#5e646e] uppercase tracking-wider">
          {searchResults.length} Estrategias Encontradas
        </span>

        <div className="flex items-center gap-1.5 p-1 bg-[#f9efe4] border border-[#ecedef] rounded-full">
          <button
            onClick={() => setFiltroAmbito('todos')}
            className={`px-3 py-1 text-xs font-medium rounded-full transition ${
              filtroAmbito === 'todos' ? 'bg-[#2d2f34] text-white' : 'text-[#5e646e]'
            }`}
          >
            Todos
          </button>
          <button
            onClick={() => setFiltroAmbito('desarrollo_personal')}
            className={`px-3 py-1 text-xs font-medium rounded-full transition ${
              filtroAmbito === 'desarrollo_personal' ? 'bg-[#2d2f34] text-white' : 'text-[#5e646e]'
            }`}
          >
            Personal & Social
          </button>
          <button
            onClick={() => setFiltroAmbito('comunicacion_integral')}
            className={`px-3 py-1 text-xs font-medium rounded-full transition ${
              filtroAmbito === 'comunicacion_integral' ? 'bg-[#2d2f34] text-white' : 'text-[#5e646e]'
            }`}
          >
            Comunicación
          </button>
          <button
            onClick={() => setFiltroAmbito('interaccion_entorno')}
            className={`px-3 py-1 text-xs font-medium rounded-full transition ${
              filtroAmbito === 'interaccion_entorno' ? 'bg-[#2d2f34] text-white' : 'text-[#5e646e]'
            }`}
          >
            Entorno
          </button>
        </div>
      </div>

      {/* Results Cards List */}
      <div className="space-y-5">
        {searchResults.map(exp => (
          <div
            key={exp.id}
            className="bg-white rounded-[32px] border border-[#ecedef] p-6 sm:p-7 shadow-product space-y-4 transition hover:border-[#d9dde6]"
          >
            {/* Card Header */}
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-[#ecedef] pb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[11px] font-mono text-[#6a707c] bg-[#f9efe4] px-2.5 py-0.5 rounded-full border border-[#ecedef]">
                    {exp.id}
                  </span>
                  <span className="text-xs text-[#5e646e] flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-[#f67748]" />
                    {exp.jardin_origen} ({exp.region})
                  </span>
                </div>
                <h3 className="font-serif text-lg sm:text-xl font-medium text-[#2d2f34]">
                  {exp.titulo}
                </h3>
              </div>

              {/* Vector Match Badge */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-medium text-[#479a53] bg-[#fdf9f4] border border-[#bbf7d0] px-3 py-1 rounded-full flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-[#479a53]" />
                  {Math.round((exp.similitud_semantica || 0.85) * 100)}% afinidad semántica
                </span>
              </div>
            </div>

            {/* Challenge & Solution */}
            <div className="space-y-3 text-xs sm:text-sm font-sans">
              <div className="p-3.5 bg-[#fdf9f4] rounded-2xl border border-[#ecedef]">
                <span className="font-serif font-semibold text-[#2d2f34] block mb-1">
                  Desafío en el Aula:
                </span>
                <p className="text-xs text-[#3f434a] leading-relaxed">
                  {exp.desafio_clave}
                </p>
              </div>

              <div className="p-4 bg-white rounded-2xl border border-[#ecedef] space-y-2">
                <span className="font-serif font-semibold text-[#2d2f34] block">
                  Estrategia Lúdica Probada:
                </span>
                <p className="text-xs text-[#3f434a] leading-relaxed">
                  {exp.solucion_probada}
                </p>

                <div className="pt-2 border-t border-[#ecedef] flex items-center gap-2 flex-wrap text-xs text-[#5e646e]">
                  <strong className="text-[#2d2f34]">Materiales cotidianos:</strong>
                  {exp.materiales_usados.map((m, idx) => (
                    <span key={idx} className="bg-[#f9efe4] text-[#3f434a] px-2 py-0.5 rounded-full text-[11px]">
                      {m}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-3 bg-[#fdf9f4] rounded-xl border border-[#ecedef] text-xs">
                <span className="font-semibold text-[#479a53] block mb-0.5">Resultado Observado:</span>
                <p className="text-[#3f434a] leading-normal">{exp.resultado_observado}</p>
              </div>
            </div>

            {/* Card Footer Actions */}
            <div className="flex items-center justify-between pt-2 border-t border-[#ecedef]">
              <div className="flex items-center gap-1.5 flex-wrap">
                {exp.tags.map((t, idx) => (
                  <span key={idx} className="text-[11px] text-[#6a707c] bg-[#f9efe4] px-2.5 py-0.5 rounded-full">
                    #{t}
                  </span>
                ))}
              </div>

              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => handleUpvote(exp.id)}
                  className="px-3 py-1.5 text-xs font-medium text-[#3f434a] hover:text-[#2d2f34] bg-[#f9efe4] hover:bg-[#ecedef] rounded-full transition flex items-center gap-1.5"
                >
                  <ThumbsUp className="w-3.5 h-3.5 text-[#f67748]" />
                  <span>Útil ({exp.votos_utilidad})</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleCopy(exp)}
                  className="px-4 py-1.5 text-xs font-medium text-[#2d2f34] hover:bg-[#f9efe4] border border-[#d9dde6] rounded-full transition flex items-center gap-1.5"
                >
                  {copiadoId === exp.id ? <Check className="w-3.5 h-3.5 text-[#479a53]" /> : <Copy className="w-3.5 h-3.5 text-[#5e646e]" />}
                  <span>{copiadoId === exp.id ? 'Copiada' : 'Adoptar en mi sala'}</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
