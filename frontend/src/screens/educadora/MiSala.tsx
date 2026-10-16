// MiSala — lista los niños/as de una sala (Requirement 8.2).
// Consume GET /ninos?sala=... vía la capa de servicios API. Sin lógica de
// negocio: solo pide la sala, muestra el resultado y enlaza a cada ficha
// (Requirement 9.6).

import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import type { Nino } from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";

export function MiSala() {
  const [sala, setSala] = useState("");
  const [salaConsultada, setSalaConsultada] = useState<string | null>(null);
  const { cargando, error, datos, ejecutar } = useAccionApi(
    api.listarNinosPorSala,
  );

  const ninos = (datos ?? []) as Nino[];

  function consultar(e: FormEvent) {
    e.preventDefault();
    const valor = sala.trim();
    if (!valor) return;
    setSalaConsultada(valor);
    void ejecutar(valor);
  }

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Mi sala</h1>
      <p className="pantalla__descripcion">
        Ingresa el identificador de la sala para ver a los niños y niñas y abrir
        su ficha.
      </p>

      <form className="formulario" onSubmit={consultar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="sala">
            Sala
          </label>
          <input
            id="sala"
            name="sala"
            value={sala}
            onChange={(e) => setSala(e.target.value)}
            placeholder="Ej.: Nivel Medio A"
            autoComplete="off"
          />
        </div>
        <div className="barra-acciones">
          <button
            type="submit"
            className="touch-target boton-primario"
            disabled={cargando || sala.trim() === ""}
          >
            Ver sala
          </button>
        </div>
      </form>

      {cargando ? <IndicadorCarga mensaje="Cargando niños y niñas…" /> : null}

      {error ? (
        <MensajeError
          mensaje={error}
          onReintentar={
            salaConsultada ? () => void ejecutar(salaConsultada) : undefined
          }
        />
      ) : null}

      {!cargando && !error && salaConsultada !== null ? (
        ninos.length > 0 ? (
          <ul className="lista">
            {ninos.map((nino) => (
              <li key={nino.id_nino}>
                <Link
                  to={`/educadora/ninos/${encodeURIComponent(nino.id_nino)}`}
                  className="tarjeta tarjeta--enlace touch-target"
                >
                  <span className="tarjeta__titulo">{nino.id_nino}</span>
                  <span className="tarjeta__meta">
                    <span>Sala: {nino.sala}</span>
                    {nino.tramo ? <span>Tramo: {nino.tramo}</span> : null}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="texto-vacio">
            No se encontraron niños ni niñas para la sala “{salaConsultada}”.
          </p>
        )
      ) : null}
    </section>
  );
}
