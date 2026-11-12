import React from 'react';
import { Users, BookOpen, GitPullRequest, BarChart3, Plus, Compass, Sparkles, Image, Database } from 'lucide-react';

export type TabId = 
  | 'parvulos' 
  | 'zonas_ciegas' 
  | 'andamiaje' 
  | 'multimodal' 
  | 'red_integra' 
  | 'bitacoras' 
  | 'recomendaciones' 
  | 'direccion';

interface NavigationProps {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
  onOpenCapture: () => void;
  badgeBitacoras?: number;
  badgeRecomendaciones?: number;
  zonasCiegasCount?: number;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  setActiveTab,
  onOpenCapture,
  badgeBitacoras,
  badgeRecomendaciones,
  zonasCiegasCount = 2
}) => {
  return (
    <>
      {/* Secondary bar on parchment canvas with full feature pill tabs */}
      <nav className="bg-[#fdf9f4] border-b border-[#ecedef] sticky top-18 z-30">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 flex items-center justify-between gap-4">
          {/* Scrollable pill tab strip */}
          <div className="flex items-center gap-1.5 py-2.5 overflow-x-auto no-scrollbar scroll-smooth">
            <button
              onClick={() => setActiveTab('parvulos')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all whitespace-nowrap shrink-0 ${
                activeTab === 'parvulos'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#5e646e] hover:text-[#2d2f34] bg-white/60 hover:bg-[#f9efe4] border border-[#ecedef]'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>Párvulos (19)</span>
            </button>

            {/* Feature 1: Radar Zonas Ciegas */}
            <button
              onClick={() => setActiveTab('zonas_ciegas')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all whitespace-nowrap shrink-0 relative ${
                activeTab === 'zonas_ciegas'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#5e646e] hover:text-[#2d2f34] bg-white/60 hover:bg-[#f9efe4] border border-[#ecedef]'
              }`}
            >
              <Compass className="w-3.5 h-3.5 text-[#f67748]" />
              <span>Radar Zonas Ciegas</span>
              {zonasCiegasCount > 0 && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                  activeTab === 'zonas_ciegas' ? 'bg-[#f67748] text-white' : 'bg-[#f67748]/15 text-[#f67748]'
                }`}>
                  {zonasCiegasCount}
                </span>
              )}
            </button>

            {/* Feature 2: Andamiaje Lúdico */}
            <button
              onClick={() => setActiveTab('andamiaje')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all whitespace-nowrap shrink-0 ${
                activeTab === 'andamiaje'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#5e646e] hover:text-[#2d2f34] bg-white/60 hover:bg-[#f9efe4] border border-[#ecedef]'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-[#f67748]" />
              <span>Andamiaje de Aula</span>
            </button>

            {/* Feature 5: Multimodal & Dibujo */}
            <button
              onClick={() => setActiveTab('multimodal')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all whitespace-nowrap shrink-0 ${
                activeTab === 'multimodal'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#5e646e] hover:text-[#2d2f34] bg-white/60 hover:bg-[#f9efe4] border border-[#ecedef]'
              }`}
            >
              <Image className="w-3.5 h-3.5 text-[#74a6f1]" />
              <span>Visión & Garabateo</span>
            </button>

            {/* Feature 6: Banco Prácticas pgvector */}
            <button
              onClick={() => setActiveTab('red_integra')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all whitespace-nowrap shrink-0 ${
                activeTab === 'red_integra'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#5e646e] hover:text-[#2d2f34] bg-white/60 hover:bg-[#f9efe4] border border-[#ecedef]'
              }`}
            >
              <Database className="w-3.5 h-3.5 text-[#479a53]" />
              <span>Red Integra pgvector</span>
            </button>

            {/* Core Bitacoras */}
            <button
              onClick={() => setActiveTab('bitacoras')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all whitespace-nowrap shrink-0 relative ${
                activeTab === 'bitacoras'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#5e646e] hover:text-[#2d2f34] bg-white/60 hover:bg-[#f9efe4] border border-[#ecedef]'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Bitácoras Quincenales</span>
              {badgeBitacoras && badgeBitacoras > 0 ? (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                  activeTab === 'bitacoras' ? 'bg-[#f67748] text-white' : 'bg-[#f9efe4] text-[#3f434a]'
                }`}>
                  {badgeBitacoras}
                </span>
              ) : null}
            </button>

            {/* Core Recomendaciones */}
            <button
              onClick={() => setActiveTab('recomendaciones')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all whitespace-nowrap shrink-0 ${
                activeTab === 'recomendaciones'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#5e646e] hover:text-[#2d2f34] bg-white/60 hover:bg-[#f9efe4] border border-[#ecedef]'
              }`}
            >
              <GitPullRequest className="w-3.5 h-3.5" />
              <span>Rúbrica & Evidencia</span>
            </button>

            {/* Direccion */}
            <button
              onClick={() => setActiveTab('direccion')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all whitespace-nowrap shrink-0 ${
                activeTab === 'direccion'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#5e646e] hover:text-[#2d2f34] bg-white/60 hover:bg-[#f9efe4] border border-[#ecedef]'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Dirección</span>
            </button>
          </div>

          {/* Primary Ember CTA Button on Desktop */}
          <div className="py-2 shrink-0 hidden sm:block">
            <button
              onClick={onOpenCapture}
              className="flex items-center gap-2 px-5 py-2 bg-[#f67748] hover:bg-[#e46436] active:scale-95 text-white text-xs font-medium rounded-full shadow-xs transition-all whitespace-nowrap"
            >
              <Plus className="w-4 h-4" />
              <span>Registrar Observación</span>
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile fixed bottom navigation bar (Slite cream parchment) */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#fdf9f4]/95 backdrop-blur-md border-t border-[#ecedef] pb-safe">
        <div className="grid grid-cols-5 items-center h-16 px-1">
          {/* Párvulos */}
          <button
            onClick={() => setActiveTab('parvulos')}
            className={`min-h-[44px] flex flex-col items-center justify-center transition-colors ${
              activeTab === 'parvulos' ? 'text-[#2d2f34] font-semibold' : 'text-[#9da3af] hover:text-[#3f434a]'
            }`}
          >
            <Users className="w-5 h-5" />
            <span className="text-[10px] mt-1">Párvulos</span>
            {activeTab === 'parvulos' && <span className="w-1 h-1 rounded-full bg-[#f67748] mt-0.5" />}
          </button>

          {/* Zonas Ciegas */}
          <button
            onClick={() => setActiveTab('zonas_ciegas')}
            className={`min-h-[44px] flex flex-col items-center justify-center relative transition-colors ${
              activeTab === 'zonas_ciegas' ? 'text-[#2d2f34] font-semibold' : 'text-[#9da3af] hover:text-[#3f434a]'
            }`}
          >
            <Compass className="w-5 h-5" />
            <span className="text-[10px] mt-1">Radar</span>
            {activeTab === 'zonas_ciegas' && <span className="w-1 h-1 rounded-full bg-[#f67748] mt-0.5" />}
            {zonasCiegasCount > 0 && (
              <span className="absolute top-1.5 right-3 w-1.5 h-1.5 bg-[#f67748] rounded-full" />
            )}
          </button>

          {/* Central Ember Floating Action */}
          <div className="flex items-center justify-center">
            <button
              onClick={onOpenCapture}
              className="min-h-[48px] min-w-[48px] -mt-5 w-12 h-12 rounded-full bg-[#f67748] hover:bg-[#e46436] active:scale-90 text-white flex items-center justify-center shadow-md shadow-[#f67748]/25 transition transform"
              aria-label="Registrar nueva observación de aula"
            >
              <Plus className="w-6 h-6 stroke-[2.5]" />
            </button>
          </div>

          {/* Andamiaje */}
          <button
            onClick={() => setActiveTab('andamiaje')}
            className={`min-h-[44px] flex flex-col items-center justify-center relative transition-colors ${
              activeTab === 'andamiaje' ? 'text-[#2d2f34] font-semibold' : 'text-[#9da3af] hover:text-[#3f434a]'
            }`}
          >
            <Sparkles className="w-5 h-5" />
            <span className="text-[10px] mt-1">Andamiaje</span>
            {activeTab === 'andamiaje' && <span className="w-1 h-1 rounded-full bg-[#f67748] mt-0.5" />}
          </button>

          {/* Bitácoras */}
          <button
            onClick={() => setActiveTab('bitacoras')}
            className={`min-h-[44px] flex flex-col items-center justify-center relative transition-colors ${
              activeTab === 'bitacoras' ? 'text-[#2d2f34] font-semibold' : 'text-[#9da3af] hover:text-[#3f434a]'
            }`}
          >
            <BookOpen className="w-5 h-5" />
            <span className="text-[10px] mt-1">Bitácoras</span>
            {activeTab === 'bitacoras' && <span className="w-1 h-1 rounded-full bg-[#f67748] mt-0.5" />}
          </button>
        </div>
      </div>
    </>
  );
};
