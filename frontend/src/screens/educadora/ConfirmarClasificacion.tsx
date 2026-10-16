// ConfirmarClasificacion - revisa nivel y dominios propuestos por el modelo.
// Las manifestaciones se derivan automáticamente del catálogo E-1 y no se
// editan manualmente.

import { useMemo, useState, type FormEvent } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api";
import type {
  ConfirmarClasificacionBody,
  Dominio,
  Observacion,
} from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";
import { DOMINIOS, ETIQUETA_DOMINIO } from "../etiquetas";

interface EstadoNavegacion {
  observacion?: Observacion;
}

function mismosDominios(a: Dominio[], b: Dominio[]): boolean {
  return [...a].sort().join("|") === [...b].sort().join("|");
}

export function ConfirmarClasificacion() {
  const { idObservacion = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const observacion = (location.state as EstadoNavegacion | null)?.observacion;
  const propuesta = observacion?.clasificacion;

  const [nivel, setNivel] = useState<number>(propuesta?.nivel_estimado ?? 1);
  const [dominios, setDominios] = useState<Dominio[]>(propuesta?.dominios ?? []);
  const manifestaciones = propuesta?.manifestaciones ?? [];

  const { cargando, error, datos, ejecutar } = useAccionApi(
    (id: string, body: ConfirmarClasificacionBody) =>
      api.confirmarClasificacion(id, body),
  );
  const confirmada = datos as Observacion | null;

  const mostrarSugerencia = useMemo(
    () =>
      Boolean(
        propuesta?.pendiente_clasificacion_manual ||
          (propuesta ? propuesta.confianza < 0.5 : false),
      ),
    [propuesta],
  );

  function alternarDominio(dominio: Dominio) {
    setDominios((actuales) =>
      actuales.includes(dominio)
        ? actuales.filter((item) => item !== dominio)
        : [...actuales, dominio],
    );
  }

  async function confirmar(e: FormEvent) {
    e.preventDefault();
    const fueCorregida =
      nivel !== (propuesta?.nivel_estimado ?? 1) ||
      !mismosDominios(dominios, propuesta?.dominios ?? []);
    const body: ConfirmarClasificacionBody = {
      accion: fueCorregida ? "corregir" : "confirmar",
      nivel_estimado: nivel,
      dominios,
      // Estos IDs fueron vinculados por el backend contra el catálogo E-1.
      manifestaciones,
    };
    const resultado = await ejecutar(idObservacion, body);
    if (resultado) {
      navigate("/educadora/capturar", {
        replace: true,
        state: { mensajeExito: "La observación se subió correctamente." },
      });
    }
  }

  if (!observacion) {
    return (
      <section className="pantalla">
        <h1 className="pantalla__titulo">Confirmar clasificación</h1>
        <p className="texto-vacio">
          No hay una clasificación propuesta. Vuelve a «Capturar observación».
        </p>
      </section>
    );
  }

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Confirmar clasificación</h1>
      <p className="pantalla__descripcion">
        Revisa la propuesta para <code>{observacion.id_observacion}</code>. Puedes
        ajustar el nivel y los dominios; las evidencias observables las determina
        automáticamente el modelo usando el catálogo E-1.
      </p>

      {mostrarSugerencia ? (
        <div className="sugerencia" role="note">
          <span className="sugerencia__icono" aria-hidden="true">💡</span>
          <span>
            La confianza de la propuesta es baja. Revisa nivel y dominios antes
            de confirmar.
          </span>
        </div>
      ) : null}

      {propuesta ? (
        <p className="campo__ayuda">
          Confianza del modelo: {Math.round(propuesta.confianza * 100)} %
        </p>
      ) : null}

      {confirmada ? (
        <p className="texto-exito" role="status">
          Clasificación confirmada correctamente.
        </p>
      ) : null}

      <form className="formulario" onSubmit={confirmar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="nivel">
            Nivel estimado (1–9)
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
          <div className="chip-grupo chip-grupo--dominios">
            {DOMINIOS.map((dominio) => {
              const seleccionado = dominios.includes(dominio);
              return (
                <label
                  key={dominio}
                  className={`chip chip--selector touch-target${
                    seleccionado ? " chip--seleccionado" : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={seleccionado}
                    onChange={() => alternarDominio(dominio)}
                  />
                  <span>{ETIQUETA_DOMINIO[dominio]}</span>
                </label>
              );
            })}
          </div>
          <span className="campo__ayuda">
            Seleccionados: {dominios.length} de {DOMINIOS.length}.
          </span>
        </fieldset>

        <section className="campo" aria-labelledby="evidencias-modelo">
          <h2 id="evidencias-modelo" className="campo__etiqueta">
            Evidencias observables sugeridas por IA
          </h2>
          {manifestaciones.length > 0 ? (
            <div className="chip-grupo">
              {manifestaciones.map((manifestacion) => (
                <span key={manifestacion} className="chip">
                  {manifestacion}
                </span>
              ))}
            </div>
          ) : (
            <span className="campo__ayuda">
              El modelo no vinculó evidencias observables; revisa nivel y dominios.
            </span>
          )}
          <span className="campo__ayuda">
            El catálogo se vincula automáticamente y no se edita manualmente.
          </span>
        </section>

        <div className="barra-acciones">
          <button
            type="submit"
            className="touch-target boton-primario"
            disabled={cargando || dominios.length === 0}
          >
            Confirmar clasificación
          </button>
        </div>
      </form>

      {cargando ? (
        <IndicadorCarga mensaje="Guardando la clasificación…" />
      ) : null}
      {error ? <MensajeError mensaje={error} /> : null}
    </section>
  );
}
