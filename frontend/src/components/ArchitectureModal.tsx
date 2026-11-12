import React, { useState } from 'react';
import { X, Layers, Server, Database, Cloud, Cpu, Check, Copy, Shield, Terminal, Zap } from 'lucide-react';
import { ModoEjecucion } from '../services/aiService';

interface ArchitectureModalProps {
  isOpen: boolean;
  onClose: () => void;
  modoActual: ModoEjecucion;
  onCambiarModo: (nuevoModo: ModoEjecucion) => void;
}

export const ArchitectureModal: React.FC<ArchitectureModalProps> = ({
  isOpen,
  onClose,
  modoActual,
  onCambiarModo
}) => {
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  if (!isOpen) return null;

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(label);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-3 sm:p-4 backdrop-blur-xs overflow-y-auto">
      <div className="w-full max-w-3xl bg-[#fdf9f4] rounded-[32px] shadow-product border border-[#ecedef] overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Header on White */}
        <div className="px-6 py-5 border-b border-[#ecedef] flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#f67748] flex items-center justify-center text-white shadow-xs">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-serif text-xl font-medium text-[#2d2f34]">
                Arquitectura Avista & "Enchufes" de IA
              </h2>
              <p className="text-xs text-[#5e646e] mt-0.5">
                Desafío "IA para el Desarrollo Infantil" · Fundación Integra · AWS Breaking Barriers 2026
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

        {/* Body on Parchment */}
        <div className="p-6 sm:p-8 overflow-y-auto space-y-6 text-xs sm:text-sm">
          {/* Active Plug Mode Switcher */}
          <div className="p-5 bg-white rounded-[24px] border border-[#ecedef] shadow-subtle space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-serif text-sm font-semibold text-[#2d2f34]">
                Selector de Enchufe Activo (Adapter)
              </span>
              <span className="text-xs text-[#5e646e]">
                Intercambio en caliente sin recarga
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => onCambiarModo('local_e1')}
                className={`p-4 rounded-2xl border text-left transition-all flex items-start gap-3 ${
                  modoActual === 'local_e1'
                    ? 'border-[#f67748] bg-[#f9efe4] ring-1 ring-[#f67748]'
                    : 'border-[#ecedef] bg-white hover:bg-[#fdf9f4]'
                }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                  modoActual === 'local_e1' ? 'bg-[#f67748] text-white' : 'bg-[#f9efe4] text-[#3f434a]'
                }`}>
                  <Terminal className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2 font-medium text-[#2d2f34] text-xs sm:text-sm">
                    <span>Modo Local (Dataset E-1)</span>
                    {modoActual === 'local_e1' && (
                      <span className="text-[10px] bg-[#2d2f34] text-white px-2 py-0.2 rounded-full">Activo</span>
                    )}
                  </div>
                  <p className="text-xs text-[#5e646e] mt-1 leading-normal font-sans">
                    Funciona 100% offline, sin credenciales de nube. Usa el dataset oficial seudonimizado E-1 de Fundación Integra.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => onCambiarModo('cloud_ia')}
                className={`p-4 rounded-2xl border text-left transition-all flex items-start gap-3 ${
                  modoActual === 'cloud_ia'
                    ? 'border-[#f67748] bg-[#f9efe4] ring-1 ring-[#f67748]'
                    : 'border-[#ecedef] bg-white hover:bg-[#fdf9f4]'
                }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                  modoActual === 'cloud_ia' ? 'bg-[#f67748] text-white' : 'bg-[#f9efe4] text-[#3f434a]'
                }`}>
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2 font-medium text-[#2d2f34] text-xs sm:text-sm">
                    <span>Modo Cloud / IA en Vivo</span>
                    {modoActual === 'cloud_ia' && (
                      <span className="text-[10px] bg-[#2d2f34] text-white px-2 py-0.2 rounded-full">Activo</span>
                    )}
                  </div>
                  <p className="text-xs text-[#5e646e] mt-1 leading-normal font-sans">
                    Clasificación pedagógica viva y redacción de bitácoras con Gemini / AWS Bedrock multiformato.
                  </p>
                </div>
              </button>
            </div>
          </div>

          {/* 3-Layer Kitchen Metaphor in Slite White Product cards */}
          <div>
            <span className="text-xs font-semibold text-[#5e646e] uppercase tracking-wider block mb-3">
              Estructura en 3 Capas Desacopladas
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              <div className="p-4 bg-white rounded-2xl border border-[#ecedef] shadow-subtle space-y-1.5">
                <div className="flex items-center gap-2 text-[#2d2f34] font-medium text-xs">
                  <Layers className="w-4 h-4 text-[#f67748]" />
                  <span>Capa 1 · Presentación</span>
                </div>
                <span className="text-[11px] text-[#6a707c] block font-mono">frontend/ (React PWA)</span>
                <p className="text-xs text-[#5e646e] leading-normal font-sans">
                  PWA móvil touch-first para sala cuna y jardín, accesible sin conexión.
                </p>
              </div>

              <div className="p-4 bg-white rounded-2xl border border-[#ecedef] shadow-subtle space-y-1.5">
                <div className="flex items-center gap-2 text-[#2d2f34] font-medium text-xs">
                  <Server className="w-4 h-4 text-[#74a6f1]" />
                  <span>Capa 2 · Lógica Negocio</span>
                </div>
                <span className="text-[11px] text-[#6a707c] block font-mono">backend/ (FastAPI)</span>
                <p className="text-xs text-[#5e646e] leading-normal font-sans">
                  Rúbrica determinista de decisión, compilador de bitácoras y suite de pruebas.
                </p>
              </div>

              <div className="p-4 bg-white rounded-2xl border border-[#ecedef] shadow-subtle space-y-1.5">
                <div className="flex items-center gap-2 text-[#2d2f34] font-medium text-xs">
                  <Database className="w-4 h-4 text-[#479a53]" />
                  <span>Capa 3 · Persistencia</span>
                </div>
                <span className="text-[11px] text-[#6a707c] block font-mono">Postgres + pgvector</span>
                <p className="text-xs text-[#5e646e] leading-normal font-sans">
                  Búsqueda vectorial con embeddings semánticos y aislamiento de privacidad.
                </p>
              </div>
            </div>
          </div>

          {/* AWS Services in Production in Dark Charcoal Pill Container */}
          <div className="p-5 bg-[#2d2f34] text-white rounded-[24px] space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-white font-medium text-xs sm:text-sm">
                <Cloud className="w-4 h-4 text-[#f67748]" />
                <span>Servicios de AWS en Modo Producción (Breaking Barriers 2026)</span>
              </div>
              <span className="text-[10px] text-[#9da3af] font-mono">CDK Infrastructure</span>
            </div>
            <p className="text-xs text-[#d9dde6] leading-relaxed font-sans">
              • <strong>Amazon Bedrock</strong> (Claude 3.5 Sonnet & Titan Embeddings) para redacción de bitácoras y búsqueda vectorial.<br />
              • <strong>Amazon Transcribe</strong> para audio de sala a texto pedagógico.<br />
              • <strong>Amazon Textract</strong> para OCR de libretas manuscritas.<br />
              • <strong>Amazon Rekognition</strong> para detección de hitos de juego.<br />
              • <strong>Aurora Serverless v2</strong> con extensión PostgreSQL pgvector.
            </p>
          </div>

          {/* 1-Command Local Test Box */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-[#5e646e] uppercase tracking-wider block">
              Comandos de Ejecución Rápida
            </span>
            <div className="space-y-2">
              <div className="p-3.5 bg-white border border-[#ecedef] text-[#2d2f34] rounded-2xl font-mono text-xs flex items-center justify-between gap-3 shadow-subtle">
                <code>powershell -ExecutionPolicy Bypass -File run_local.ps1</code>
                <button
                  type="button"
                  onClick={() => copyToClipboard('powershell -ExecutionPolicy Bypass -File run_local.ps1', 'ps1')}
                  className="px-3 py-1 text-xs bg-[#f9efe4] hover:bg-[#ecedef] text-[#3f434a] rounded-full transition shrink-0 flex items-center gap-1"
                >
                  {copiedCmd === 'ps1' ? <Check className="w-3.5 h-3.5 text-[#479a53]" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedCmd === 'ps1' ? 'Copiado' : 'Copiar'}</span>
                </button>
              </div>

              <div className="p-3.5 bg-white border border-[#ecedef] text-[#2d2f34] rounded-2xl font-mono text-xs flex items-center justify-between gap-3 shadow-subtle">
                <code>docker-compose up --build</code>
                <button
                  type="button"
                  onClick={() => copyToClipboard('docker-compose up --build', 'docker')}
                  className="px-3 py-1 text-xs bg-[#f9efe4] hover:bg-[#ecedef] text-[#3f434a] rounded-full transition shrink-0 flex items-center gap-1"
                >
                  {copiedCmd === 'docker' ? <Check className="w-3.5 h-3.5 text-[#479a53]" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedCmd === 'docker' ? 'Copiado' : 'Copiar'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#ecedef] bg-white flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-[#3f434a]">
            <Shield className="w-4 h-4 text-[#479a53]" />
            <span>Dataset sintético E-1 activo</span>
          </div>

          <button
            onClick={onClose}
            className="px-5 py-2 text-xs font-medium text-[#2d2f34] bg-[#f9efe4] hover:bg-[#ecedef] rounded-full transition"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
