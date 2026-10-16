// IndicadorCarga — indicador visual de progreso (Requirement 9.3).
// Se muestra de inmediato (sin retardos artificiales) para que aparezca dentro
// de los 100 ms siguientes a la interacción, y se mantiene hasta recibir la
// respuesta del backend. Es puramente de presentación.

interface IndicadorCargaProps {
  /** Texto accesible y visible junto al spinner. */
  mensaje?: string;
  /** Variante compacta (en línea) para botones/listas. */
  compacto?: boolean;
}

export function IndicadorCarga({
  mensaje = "Procesando…",
  compacto = false,
}: IndicadorCargaProps) {
  return (
    <div
      className={`indicador-carga${compacto ? " indicador-carga--compacto" : ""}`}
      role="status"
      aria-live="polite"
    >
      <span className="indicador-carga__spinner" aria-hidden="true" />
      <span className="indicador-carga__texto">{mensaje}</span>
    </div>
  );
}
