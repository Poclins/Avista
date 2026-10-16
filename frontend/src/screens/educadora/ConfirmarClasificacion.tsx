// ConfirmarClasificacion â€” revisa la clasificaciÃ³n PROPUESTA por el backend y
// permite confirmarla o corregirla (Requirement 8.2). Si el backend marcÃ³ la
// propuesta como de baja confianza / pendiente de clasificaciÃ³n manual, muestra
// una SUGERENCIA PROACTIVA para que la educadora la revise. Persiste vÃ­a
// PATCH /observaciones/{id}/clasificacion.
//
// Sin lÃ³gica de negocio (Requirement 9.6): la clasificaciÃ³n la propone el
// backend; el cliente solo presenta los valores y envÃ­a la confirmaciÃ³n/correcciÃ³n.

import { useMemo, useState, type FormEvent } from "react";
import { useLocation, useParams } from "react-router-dom";
import { api } from "../../api";
import type {
  Dominio,
  Observacion,
  ConfirmarClasificacionBody,
} from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";
import { DOMINIOS, ETIQUETA_DOMINIO } from "../etiquetas";

interface EstadoNavegacion {
  observacion?: Observacion;
}

export function ConfirmarClasificacion() {
  const { idObservacion = "" } = useParams();
  const location = useLocation();
  const observacion = (location.state as EstadoNavegacion | null)?.observacion;
  const propuesta = observacion?.clasificacion;

  const [nivel, setNivel] = useState<number>(propuesta?.nivel_estimado ?? 1);
  const [dominios, setDominios] = useState<Dominio[]>(
    propuesta?.dominios ?? [],
  );
  const [manifestaciones, setManifestaciones] = useState<string>(
    (propuesta?.manifestaciones ?? []).join(", "),
  );

  const { cargando, error, datos, ejecutar } = useAccionApi(
    (id: string, body: ConfirmarClasificacionBody) =>
      api.confirmarClasificacion(id, body),
  );
  const confirmada = datos as Observacion | null;

  // Sugerencia proactiva cuando el backend indica baja confianza / revisiÃ³n manual.
  const mostrarSugerencia = useMemo(
    () =>
      Boolean(propuesta?.pendiente_clasificacion_manual || (propuesta ? propuesta.confianza < 0.5 : false)),
    [observacion, propuesta],
  );

  function alternarDominio(d: Dominio) {
    setDominios((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d],
    );
  }

  function confirmar(e: FormEvent) {
    e.preventDefault();
    const body: ConfirmarClasificacionBody = {
      accion: "corregir",
      nivel_estimado: nivel,
      dominios,
      manifestaciones: manifestaciones
        .split(",")
        .map((m) => m.trim())
        .filter((m) => m !== ""),
    };
    void ejecutar(idObservacion, body);
  }

  if (!observacion) {
    return (
      <section className="pantalla">
        <h1 className="pantalla__titulo">Confirmar clasificaciÃ³n</h1>
        <p className="texto-vacio">
          No hay una clasificaciÃ³n propuesta disponible. Vuelve a â€œCapturarâ€
          para registrar una observaciÃ³n y obtener una propuesta.
        </p>
      </section>
    );
  }

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Confirmar clasificaciÃ³n</h1>
      <p className="pantalla__descripcion">
        Revisa la clasificaciÃ³n propuesta para la observaciÃ³n{" "}
        <code>{observacion.id_observacion}</code> y confÃ­rmala o corrÃ­gela.
      </p>

      {mostrarSugerencia ? (
        <div className="sugerencia" role="note">
          <span className="sugerencia__icono" aria-hidden="true">
            ðŸ’¡
          </span>
          <span>
            El sistema no estÃ¡ seguro de esta clasificaciÃ³n. Te recomendamos
            revisar el nivel y los dominios antes de confirmar.
          </span>
        </div>
      ) : null}

      {confirmada ? (
        <p className="texto-exito" role="status">
          ClasificaciÃ³n confirmada correctamente.
        </p>
      ) : null}

      <form className="formulario" onSubmit={confirmar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="nivel">
            Nivel estimado (1â€“9)
          </label>
          <input
            id="nivel"
            type="number"
            min={1}
            max={9}
            value={nivel}
            onChange={(e) => setNivel(Number(e.target.value))}
          />
        </div>

        <fieldset className="campo">
          <legend className="campo__etiqueta">Dominios</legend>
          <div className="chip-grupo">
            {DOMINIOS.map((d) => {
              const seleccionado = dominios.includes(d);
              return (
                <button
                  key={d}
                  type="button"
                  className={`chip touch-target${
                    seleccionado ? " chip--seleccionado" : ""
                  }`}
                  aria-pressed={seleccionado}
                  onClick={() => alternarDominio(d)}
                >
                  {ETIQUETA_DOMINIO[d]}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div className="campo">
          <label className="campo__etiqueta" htmlFor="manifestaciones">
            Manifestaciones vinculadas
          </label>
          <input
            id="manifestaciones"
            value={manifestaciones}
            onChange={(e) => setManifestaciones(e.target.value)}
            placeholder="Identificadores separados por coma"
          />
          <span className="campo__ayuda">
            Separa los identificadores de manifestaciÃ³n con comas.
          </span>
        </div>

        <div className="barra-acciones">
          <button
            type="submit"
            className="touch-target boton-primario"
            disabled={cargando}
          >
            Confirmar clasificaciÃ³n
          </button>
        </div>
      </form>

      {cargando ? (
        <IndicadorCarga mensaje="Guardando la clasificaciÃ³nâ€¦" />
      ) : null}

      {error ? <MensajeError mensaje={error} /> : null}
    </section>
  );
}



