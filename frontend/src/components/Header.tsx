import React from 'react';
import { Cpu, ShieldCheck, Users, Building2 } from 'lucide-react';
import { PWAInstallButton } from './PWAInstallButton';
import { JARDIN_ACTUAL, SALA_ACTUAL } from '../data/datasetE1';
import { ModoEjecucion } from '../services/aiService';

interface HeaderProps {
  rol: 'educadora' | 'directora';
  setRol: (rol: 'educadora' | 'directora') => void;
  modoEjecucion: ModoEjecucion;
  setModoEjecucion: (modo: ModoEjecucion) => void;
  onOpenArchitecture: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  rol,
  setRol,
  modoEjecucion,
  setModoEjecucion,
  onOpenArchitecture
}) => {
  return (
    <header className="sticky top-0 z-40 bg-[#fdf9f4]/95 backdrop-blur-md border-b border-[#ecedef]">
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 h-18 flex items-center justify-between gap-4">
        {/* Brand Zone: Slite editorial style wordmark */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#f67748] flex items-center justify-center text-white font-serif font-bold text-base shadow-xs">
              A
            </div>
            <div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-serif text-xl font-medium tracking-tight text-[#2d2f34]">
                  Avista
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#f67748] inline-block" />
              </div>
              <span className="text-[11px] text-[#5e646e] font-sans block -mt-0.5 hidden sm:block">
                Fundación Integra · Cuaderno Pedagógico
              </span>
            </div>
          </div>

          <div className="hidden lg:flex items-center gap-2 pl-4 border-l border-[#ecedef] text-xs text-[#5e646e]">
            <span className="text-[#3f434a] font-medium">{JARDIN_ACTUAL.nombre}</span>
            <span className="text-[#9da3af]">·</span>
            <span className="bg-[#f9efe4] text-[#3f434a] px-2.5 py-0.5 rounded-full text-[11px] font-medium">
              {SALA_ACTUAL.codigo} (19 párvulos)
            </span>
          </div>
        </div>

        {/* Center / Navigation Controls: Role toggle & Mode selector */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Role selector: Slite pill segmented control */}
          <div className="flex items-center p-1 bg-[#f9efe4] border border-[#ecedef] rounded-full">
            <button
              onClick={() => setRol('educadora')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all ${
                rol === 'educadora'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#3f434a] hover:text-[#2d2f34]'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>Tía de Sala</span>
            </button>
            <button
              onClick={() => setRol('directora')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-full transition-all ${
                rol === 'directora'
                  ? 'bg-[#2d2f34] text-white shadow-xs'
                  : 'text-[#3f434a] hover:text-[#2d2f34]'
              }`}
            >
              <Building2 className="w-3.5 h-3.5" />
              <span>Directora</span>
            </button>
          </div>

          {/* Architecture trigger: Slite Outlined Pill button */}
          <button
            onClick={onOpenArchitecture}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-[#3f434a] hover:text-[#2d2f34] bg-transparent hover:bg-[#f9efe4] border border-[#d9dde6] rounded-full transition-all"
            title="Ver arquitectura de 3 capas y adaptadores de IA"
          >
            <Cpu className="w-3.5 h-3.5 text-[#f67748]" />
            <span className="hidden md:inline">Arquitectura & Enchufes</span>
            <span className="md:hidden">Enchufes</span>
          </button>
        </div>

        {/* Right Action Zone: PWA Install & Dust Tag Chip */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <div className="hidden xl:flex items-center gap-1.5 text-xs text-[#3f434a] bg-[#f9efe4] px-3 py-1 rounded-full border border-[#ecedef]">
            <ShieldCheck className="w-3.5 h-3.5 text-[#479a53]" />
            <span>Dataset E-1</span>
          </div>

          <PWAInstallButton />
        </div>
      </div>
    </header>
  );
};
