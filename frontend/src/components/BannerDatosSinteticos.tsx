// BannerDatosSinteticos — banner visible y persistente en todas las pantallas
// que indica que los datos son sintéticos y de uso pedagógico (Requirement 9.4).

export function BannerDatosSinteticos() {
  return (
    <div className="banner-sintetico" role="note" aria-live="polite">
      <span aria-hidden="true" className="banner-sintetico__icono">
        ⚠️
      </span>
      <span>
        Datos sintéticos de uso pedagógico. No corresponden a niños/as reales.
      </span>
    </div>
  );
}
