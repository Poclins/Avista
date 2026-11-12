import React, { useState } from 'react';
import { Header } from './components/Header';
import { Navigation, TabId } from './components/Navigation';
import { ParvulosList } from './components/ParvulosList';
import { ParvuloDetailModal } from './components/ParvuloDetailModal';
import { CaptureModal } from './components/CaptureModal';
import { BitacorasView } from './components/BitacorasView';
import { RecomendacionesView } from './components/RecomendacionesView';
import { DireccionDashboard } from './components/DireccionDashboard';
import { ArchitectureModal } from './components/ArchitectureModal';
import { OfflineIndicator } from './components/PWAInstallButton';
import { RadarZonasCiegas } from './components/RadarZonasCiegas';
import { GeneradorAndamiaje } from './components/GeneradorAndamiaje';
import { AnalisisMultimodal } from './components/AnalisisMultimodal';
import { BancoExperiencias } from './components/BancoExperiencias';
import { 
  PARVULOS_DATASET_E1, 
  OBSERVACIONES_INICIALES, 
  BITACORAS_INICIALES, 
  RECOMENDACIONES_INICIALES, 
  REPORTE_DIRECCION_INICIAL 
} from './data/datasetE1';
import { Parvulo, Observacion, BitacoraQuincenal, RecomendacionNivel, ReporteDireccion } from './types/avista';
import { ModoEjecucion, aiService } from './services/aiService';

export default function App() {
  const [rol, setRol] = useState<'educadora' | 'directora'>('educadora');
  const [activeTab, setActiveTab] = useState<TabId>('parvulos');
  const [modoEjecucion, setModoEjecucion] = useState<ModoEjecucion>(aiService.getMode());

  // Master Data State
  const [parvulos, setParvulos] = useState<Parvulo[]>(PARVULOS_DATASET_E1);
  const [observaciones, setObservaciones] = useState<Observacion[]>(OBSERVACIONES_INICIALES);
  const [bitacoras, setBitacoras] = useState<BitacoraQuincenal[]>(BITACORAS_INICIALES);
  const [recomendaciones, setRecomendaciones] = useState<RecomendacionNivel[]>(RECOMENDACIONES_INICIALES);
  const [reporte, setReporte] = useState<ReporteDireccion>(REPORTE_DIRECCION_INICIAL);

  // Modals state
  const [selectedParvuloForDetail, setSelectedParvuloForDetail] = useState<Parvulo | null>(null);
  const [isCaptureModalOpen, setIsCaptureModalOpen] = useState(false);
  const [captureChildId, setCaptureChildId] = useState<string>('NI-1001');
  const [isArchitectureModalOpen, setIsArchitectureModalOpen] = useState(false);

  // Focus child for tab navigation
  const [targetChildForBitacora, setTargetChildForBitacora] = useState<string | undefined>(undefined);
  const [targetChildForRecomendacion, setTargetChildForRecomendacion] = useState<string | undefined>(undefined);

  // Switch role changes default tab if director
  const handleSetRol = (newRol: 'educadora' | 'directora') => {
    setRol(newRol);
    if (newRol === 'directora') {
      setActiveTab('direccion');
    } else if (activeTab === 'direccion') {
      setActiveTab('parvulos');
    }
  };

  const handleCambiarModo = (nuevoModo: ModoEjecucion) => {
    setModoEjecucion(nuevoModo);
    aiService.setMode(nuevoModo);
  };

  const handleOpenCapture = (childId?: string) => {
    setCaptureChildId(childId || parvulos[0]?.id || 'NI-1001');
    setIsCaptureModalOpen(true);
  };

  const handleSaveObservation = (nuevaObs: Observacion) => {
    // 1. Add to observations list
    setObservaciones(prev => [nuevaObs, ...prev]);

    // 2. Update child observation count and coverage
    setParvulos(prev => prev.map(p => {
      if (p.id === nuevaObs.id_nino) {
        const newCount = p.total_observaciones + 1;
        return {
          ...p,
          total_observaciones: newCount,
          estado_cobertura: newCount >= 5 ? 'optimo' : newCount >= 3 ? 'adecuado' : 'pendiente'
        };
      }
      return p;
    }));

    // 3. Update aggregated report
    setReporte(prev => {
      const isPersonal = nuevaObs.ambito === 'desarrollo_personal';
      const isComunicacion = nuevaObs.ambito === 'comunicacion_integral';
      const isEntorno = nuevaObs.ambito === 'interaccion_entorno';

      return {
        ...prev,
        observaciones_totales_quincena: prev.observaciones_totales_quincena + 1,
        distribucion_ambitos: {
          desarrollo_personal: prev.distribucion_ambitos.desarrollo_personal + (isPersonal ? 1 : 0),
          comunicacion_integral: prev.distribucion_ambitos.comunicacion_integral + (isComunicacion ? 1 : 0),
          interaccion_entorno: prev.distribucion_ambitos.interaccion_entorno + (isEntorno ? 1 : 0)
        }
      };
    });
  };

  const handleUpdateBitacora = (updated: BitacoraQuincenal) => {
    setBitacoras(prev => prev.map(b => (b.id === updated.id ? updated : b)));
  };

  const handleAddBitacora = (nueva: BitacoraQuincenal) => {
    setBitacoras(prev => {
      const filtered = prev.filter(b => b.id_nino !== nueva.id_nino);
      return [nueva, ...filtered];
    });
  };

  const handleUpdateRecomendacion = (updated: RecomendacionNivel) => {
    setRecomendaciones(prev => prev.map(r => (r.id === updated.id ? updated : r)));
  };

  const handleAddRecomendacion = (nueva: RecomendacionNivel) => {
    setRecomendaciones(prev => {
      const filtered = prev.filter(r => r.id_nino !== nueva.id_nino);
      return [nueva, ...filtered];
    });
  };

  const pendingBitacorasCount = bitacoras.filter(b => b.estado === 'en_revision' || b.estado === 'borrador_ia').length;
  const pendingRecsCount = recomendaciones.filter(r => r.estado_educadora === 'pendiente').length;

  return (
    <div className="min-h-screen bg-[#fdf9f4] text-[#2d2f34] flex flex-col font-sans">
      {/* 1. Header (Clean 3-zone contract with role & plug controls) */}
      <Header
        rol={rol}
        setRol={handleSetRol}
        modoEjecucion={modoEjecucion}
        setModoEjecucion={handleCambiarModo}
        onOpenArchitecture={() => setIsArchitectureModalOpen(true)}
      />

      {/* 2. Secondary Navigation (Desktop subheader + Mobile bottom tabs) */}
      <Navigation
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenCapture={() => handleOpenCapture()}
        badgeBitacoras={pendingBitacorasCount}
        badgeRecomendaciones={pendingRecsCount}
      />

      {/* 3. Main Workspace Canvas */}
      <main className="flex-1 max-w-[1200px] w-full mx-auto px-4 sm:px-6 py-6 pb-24 md:pb-16">
        {activeTab === 'parvulos' && (
          <ParvulosList
            parvulos={parvulos}
            observaciones={observaciones}
            onSelectParvulo={(p) => setSelectedParvuloForDetail(p)}
            onOpenCaptureForParvulo={(id) => handleOpenCapture(id)}
          />
        )}

        {/* Feature 1: Radar Zonas Ciegas */}
        {activeTab === 'zonas_ciegas' && (
          <RadarZonasCiegas
            parvulos={parvulos}
            observaciones={observaciones}
            onOpenCaptureForParvulo={(id) => handleOpenCapture(id)}
          />
        )}

        {/* Feature 2: Andamiaje Lúdico Situado */}
        {activeTab === 'andamiaje' && (
          <GeneradorAndamiaje
            parvulos={parvulos}
            observaciones={observaciones}
          />
        )}

        {/* Feature 5: Multimodal & Garabateo */}
        {activeTab === 'multimodal' && (
          <AnalisisMultimodal
            parvulos={parvulos}
            onSaveObservation={handleSaveObservation}
          />
        )}

        {/* Feature 6: Banco Colaborativo pgvector */}
        {activeTab === 'red_integra' && (
          <BancoExperiencias />
        )}

        {activeTab === 'bitacoras' && (
          <BitacorasView
            bitacoras={bitacoras}
            parvulos={parvulos}
            observaciones={observaciones}
            onUpdateBitacora={handleUpdateBitacora}
            onAddBitacora={handleAddBitacora}
            initialSelectedChildId={targetChildForBitacora}
          />
        )}

        {activeTab === 'recomendaciones' && (
          <RecomendacionesView
            recomendaciones={recomendaciones}
            parvulos={parvulos}
            observaciones={observaciones}
            onUpdateRecomendacion={handleUpdateRecomendacion}
            onAddRecomendacion={handleAddRecomendacion}
            initialSelectedChildId={targetChildForRecomendacion}
          />
        )}

        {activeTab === 'direccion' && (
          <DireccionDashboard
            reporte={reporte}
            parvulos={parvulos}
            observaciones={observaciones}
          />
        )}
      </main>

      {/* 4. Modals */}
      <ParvuloDetailModal
        parvulo={selectedParvuloForDetail}
        observaciones={observaciones}
        onClose={() => setSelectedParvuloForDetail(null)}
        onOpenCapture={(childId) => {
          setSelectedParvuloForDetail(null);
          handleOpenCapture(childId);
        }}
        onGoToBitacoras={(childId) => {
          setSelectedParvuloForDetail(null);
          setTargetChildForBitacora(childId);
          setActiveTab('bitacoras');
        }}
        onGoToRecomendacion={(childId) => {
          setSelectedParvuloForDetail(null);
          setTargetChildForRecomendacion(childId);
          setActiveTab('recomendaciones');
        }}
      />

      <CaptureModal
        isOpen={isCaptureModalOpen}
        onClose={() => setIsCaptureModalOpen(false)}
        parvulos={parvulos}
        selectedChildId={captureChildId}
        onSaveObservation={handleSaveObservation}
      />

      <ArchitectureModal
        isOpen={isArchitectureModalOpen}
        onClose={() => setIsArchitectureModalOpen(false)}
        modoActual={modoEjecucion}
        onCambiarModo={handleCambiarModo}
      />

      {/* 5. Offline PWA Indicator */}
      <OfflineIndicator />
    </div>
  );
}
