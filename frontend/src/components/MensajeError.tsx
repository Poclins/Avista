// MensajeError — muestra un mensaje de error en español cuando una solicitud
// falla o excede el timeout de 10 s (Requirement 9.7). No descarta datos: solo
// informa y, opcionalmente, ofrece reintentar.

interface MensajeErrorProps {
  mensaje: string;
  onReintentar?: () => void;
}

export function MensajeError({ mensaje, onReintentar }: MensajeErrorProps) {
  return (
    <div className="mensaje-error" role="alert">
      <p className="mensaje-error__texto">{mensaje}</p>
      {onReintentar ? (
        <button
          type="button"
          className="touch-target boton-secundario"
          onClick={onReintentar}
        >
          Reintentar
        </button>
      ) : null}
    </div>
  );
}
