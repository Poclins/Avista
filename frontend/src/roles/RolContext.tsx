// Estado del rol activo (Requirement 8). Dos roles de UI mutuamente
// excluyentes: educadora y directora, sin autenticacion real (demo).
// Se persiste en localStorage para sobrevivir recargas de la PWA.

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { RolUI } from "../api/types";

const STORAGE_KEY = "jaimes.rol";

interface RolContextValue {
  rol: RolUI | null;
  setRol: (rol: RolUI | null) => void;
}

const RolContext = createContext<RolContextValue | undefined>(undefined);

function leerRolInicial(): RolUI | null {
  try {
    const guardado = localStorage.getItem(STORAGE_KEY);
    return guardado === "educadora" || guardado === "directora" ? guardado : null;
  } catch {
    return null;
  }
}

export function RolProvider({ children }: { children: ReactNode }) {
  const [rol, setRolState] = useState<RolUI | null>(leerRolInicial);

  const setRol = useCallback((nuevo: RolUI | null) => {
    setRolState(nuevo);
    try {
      if (nuevo) localStorage.setItem(STORAGE_KEY, nuevo);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Sin persistencia disponible: el rol vive solo en memoria.
    }
  }, []);

  const value = useMemo(() => ({ rol, setRol }), [rol, setRol]);

  return <RolContext.Provider value={value}>{children}</RolContext.Provider>;
}

export function useRol(): RolContextValue {
  const ctx = useContext(RolContext);
  if (!ctx) {
    throw new Error("useRol debe usarse dentro de <RolProvider>.");
  }
  return ctx;
}
