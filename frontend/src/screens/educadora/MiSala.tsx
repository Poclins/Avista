// MiSala - lista los ninos/as de una sala (Requirement 8.2).
// Consume GET /ninos?jardin=...&sala=... (ambos requeridos por el backend).

import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import type { Nino } from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";
import { nombreCompletoNino } from "../etiquetas";

export function MiSala() {
  const [jardin, setJardin] = useState("");
  const [sala, setSala] = useState("");
  const [consultado, setConsultado] = useState<{ jardin: string; sala: string } | null>(null);
  const { cargando, error, datos, ejecutar } = useAccionApi(api.listarNinosPorSala);

  const ninos = (datos ?? []) as Nino[];

  function consultar(e: FormEvent) {
    e.preventDefault();
    const j = jardin.trim();
    const s = sala.trim();
    if (!j || !s) return;
    setConsultado({ jardin: j, sala: s });
    void ejecutar(j, s);
  }

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Mi sala</h1>
      <p className="pantalla__descripcion">
        Ingresa el jardin y la sala para ver a los niños y niñas y abrir su ficha.
      </p>

      <form className="formulario" onSubmit={consultar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="jardin">Jardín</label>
          <input id="jardin" name="jardin" value={jardin}
            onChange={(e) => setJardin(e.target.value)}
            placeholder="Ej.: JAR-0013" autoComplete="off" />
        </div>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="sala">Sala</label>
          <input id="sala" name="sala" value={sala}
            onChange={(e) => setSala(e.target.value)}
            placeholder="Ej.: SG-C" autoComplete="off" />
        </div>
        <div className="barra-acciones">
          <button type="submit" className="touch-target boton-primario"
            disabled={cargando || jardin.trim() === "" || sala.trim() === ""}>
            Ver sala
          </button>
        </div>
      </form>

      {cargando ? <IndicadorCarga mensaje="Cargando niños y niñas…" /> : null}

      {error ? (
        <MensajeError mensaje={error}
          onReintentar={consultado ? () => void ejecutar(consultado.jardin, consultado.sala) : undefined} />
      ) : null}

      {!cargando && !error && consultado !== null ? (
        ninos.length > 0 ? (
          <ul className="lista">
            {ninos.map((nino) => (
              <li key={nino.id_nino}>
                <Link to={`/educadora/ninos/${encodeURIComponent(nino.id_nino)}`}
                  className="tarjeta tarjeta--enlace touch-target">
                  <span className="tarjeta__titulo">{nombreCompletoNino(nino)}</span>
                  <span className="tarjeta__meta">
                    <span>Sala: {nino.sala_grupo}</span>
                    <span>Jardín: {nino.id_jardin}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="texto-vacio">
            No se encontraron niños ni niñas para la sala "{consultado.sala}" del jardín "{consultado.jardin}".
          </p>
        )
      ) : null}
    </section>
  );
}
