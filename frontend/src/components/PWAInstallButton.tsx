import React, { useState } from 'react';
import { Download, Smartphone, X } from 'lucide-react';
import { usePWAInstall, useOnlineStatus } from '../hooks/usePWAInstall';

export const PWAInstallButton: React.FC = () => {
  const { isInstallable, isInstalled, isIOS, install } = usePWAInstall();
  const [showIOSGuide, setShowIOSGuide] = useState(false);

  if (isInstalled) {
    return null;
  }

  if (isInstallable) {
    return (
      <button
        onClick={install}
        className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-[#2d2f34] hover:bg-[#3f434a] active:scale-95 rounded-full shadow-xs transition"
        title="Instalar Avista PWA"
      >
        <Download className="w-3.5 h-3.5 text-[#f67748]" />
        <span className="whitespace-nowrap">Instalar App</span>
      </button>
    );
  }

  if (isIOS) {
    return (
      <>
        <button
          onClick={() => setShowIOSGuide(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#3f434a] bg-[#f9efe4] hover:bg-[#ecedef] border border-[#ecedef] rounded-full transition"
        >
          <Smartphone className="w-3.5 h-3.5" />
          <span className="whitespace-nowrap">Instalar en iOS</span>
        </button>

        {showIOSGuide && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-xs">
            <div className="w-full max-w-sm rounded-[32px] bg-[#fdf9f4] p-6 shadow-product border border-[#ecedef]">
              <div className="flex items-center justify-between pb-3 border-b border-[#ecedef]">
                <h3 className="font-serif text-lg font-medium text-[#2d2f34]">Instalar Avista en iOS</h3>
                <button 
                  onClick={() => setShowIOSGuide(false)}
                  className="p-1 text-[#5e646e] hover:text-[#2d2f34] rounded-full"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <p className="mt-3 text-xs text-[#3f434a] leading-relaxed font-sans">
                1. Toca el botón <strong>Compartir</strong> <span className="text-[#f67748]">⎋</span> en la barra de Safari.<br />
                2. Desplázate hacia abajo y selecciona <strong>Agregar al inicio</strong>.<br />
                3. Abre Avista como un cuaderno de sala que funciona incluso sin internet.
              </p>
              <button
                onClick={() => setShowIOSGuide(false)}
                className="mt-5 w-full rounded-full bg-[#2d2f34] py-2.5 text-xs font-medium text-white hover:bg-[#3f434a] transition"
              >
                Entendido
              </button>
            </div>
          </div>
        )}
      </>
    );
  }

  return null;
};

export const OfflineIndicator: React.FC = () => {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div className="fixed bottom-16 sm:bottom-4 left-4 right-4 sm:right-auto z-50 flex items-center gap-2 rounded-full bg-[#2d2f34] px-4 py-2 text-xs font-medium text-white shadow-product border border-[#ecedef]">
      <span className="h-2 w-2 rounded-full bg-[#f67748] animate-pulse" />
      <span>Modo Sin Conexión · Cuaderno local E-1 activo</span>
    </div>
  );
};
