// useAccionApi — hook de presentación que ejecuta una llamada a la API y expone
// estado de carga/error para que las pantallas muestren el IndicadorCarga de
// inmediato (Requirement 9.3) y un MensajeError sin descartar datos ante fallo o
// timeout (Requirement 9.7). No contiene lógica de negocio.

import { useCallback, useRef, useState } from "react";
import { ApiError } from "../api/client";

interface EstadoAccion<T> {
  cargando: boolean;
  error: string | null;
  datos: T | null;
}

export function useAccionApi<Args extends unknown[], T>(
  accion: (...args: Args) => Promise<T>,
) {
  const [estado, setEstado] = useState<EstadoAccion<T>>({
    cargando: false,
    error: null,
    datos: null,
  });

  // Evita condiciones de carrera: solo la última ejecución actualiza el estado.
  const ejecucionRef = useRef(0);

  const ejecutar = useCallback(
    async (...args: Args): Promise<T | null> => {
      const ejecucionActual = ++ejecucionRef.current;
      // El indicador de progreso se activa de forma síncrona (≤100 ms).
      setEstado((prev) => ({ ...prev, cargando: true, error: null }));
      try {
        const datos = await accion(...args);
        if (ejecucionActual === ejecucionRef.current) {
          setEstado({ cargando: false, error: null, datos });
        }
        return datos;
      } catch (err) {
        const mensaje =
          err instanceof ApiError
            ? err.message
            : "Ocurrió un error inesperado. Tus datos no se han perdido; intenta nuevamente.";
        if (ejecucionActual === ejecucionRef.current) {
          // Importante: NO se tocan los datos del formulario del llamador.
          setEstado((prev) => ({ ...prev, cargando: false, error: mensaje }));
        }
        return null;
      }
    },
    [accion],
  );

  const limpiarError = useCallback(() => {
    setEstado((prev) => ({ ...prev, error: null }));
  }, []);

  return { ...estado, ejecutar, limpiarError };
}
