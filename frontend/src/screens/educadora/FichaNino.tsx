// FichaNino - ficha y trayectoria de un nino/a (Requirement 8.2) con el flujo
// "¿Puede subir de nivel?" (recomendacion de nivel: la rubrica decide, la IA
// argumenta). Sin logica de negocio en el cliente (Requirement 9.6).

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../api";
import type {
  Dominio,
  FichaNino as FichaNinoDTO,
  Recomendacion,
} from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";
import {
  ETIQUETA_DECISION,
  ETIQUETA_DOMINIO,
  claseEstadoDecision,
  formatearFecha,
  nombreCompletoNino,
} from "../etiquetas";

// Decision humana final: texto libre en el backend (DecisionEducadoraIn).
const DECISIONES_EDUCADORA: { valor: string; etiqueta: string }[] = [
  { valor: "acepto", etiqueta: "Aceptar" },
  { valor: "ajusto", etiqueta: "Ajustar" },
  { valor: "rechazo", etiqueta: "Rechazar" },
];

// Educadora de demo e id para generar la recomendacion.
const ID_EDUCADORA_DEMO = "EDU-0001";

export function FichaNino() {
  const { idNino = "" } = useParams();
  const [nivelActual, setNivelActual] = useState(1);

  const ficha = useAccionApi((id: string) => api.obtenerFichaNino(id));
  const recomendacion = useAccionApi((id: string, nivel: number) =>
    api.generarRecomendacion(id, {
      id_educadora: ID_EDUCADORA_DEMO,
      nivel_actual: nivel,
    }),
  );
  const decision = useAccionApi((idRec: string, d: string) =>
    api.registrarDecisionRecomendacion(idRec, { decision_educadora: d }),
  );

  useEffect(() => {
    if (idNino) void ficha.ejecutar(idNino);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idNino]);

  const datosFicha = ficha.datos as FichaNinoDTO | null;
  const rec = recomendacion.datos as Recomendacion | null;
  const decisionRegistrada = decision.datos;

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">
        {datosFicha ? `Ficha de ${nombreCompletoNino(datosFicha.nino)}` : "Ficha del niño/a"}
      </h1>
      <p className="pantalla__descripcion">
        Trayectoria de desarrollo y recomendaciones pedagógicas.
      </p>
      {ficha.cargando ? (
        <IndicadorCarga mensaje="Cargando ficha..." />
      ) : ficha.error ? (
        <MensajeError
          mensaje={ficha.error}
          onReintentar={() => void ficha.ejecutar(idNino)}
        />
      ) : datosFicha ? (
        <>
          <div className="tarjeta">
            <span className="tarjeta__meta">
              <span>Sala: {datosFicha.nino.sala_grupo}</span>
              <span>Jardín: {datosFicha.nino.id_jardin}</span>
              <span>Ingreso: {formatearFecha(datosFicha.nino.fecha_ingreso)}</span>
            </span>
          </div>

          <section className="seccion">
            <h2 className="seccion__titulo">¿Puede subir de nivel?</h2>
            <div className="campo">
              <label className="campo__etiqueta" htmlFor="nivel">
                Nivel actual (1-9)
              </label>
              <input
                id="nivel"
                type="number"
                min={1}
                max={9}
                value={nivelActual}
                onChange={(e) => setNivelActual(Number(e.target.value))}
              />
            </div>
            <div className="barra-acciones">
              <button
                type="button"
                className="touch-target boton-primario"
                disabled={recomendacion.cargando}
                onClick={() => void recomendacion.ejecutar(idNino, nivelActual)}
              >
                Evaluar recomendación
              </button>
            </div>

            {recomendacion.cargando ? (
              <IndicadorCarga mensaje="Evaluando la trayectoria…" />
            ) : null}
            {recomendacion.error ? (
              <MensajeError mensaje={recomendacion.error} />
            ) : null}

            {rec ? (
              <PanelRecomendacion
                rec={rec}
                decisionRegistrada={decisionRegistrada?.decision_educadora ?? null}
                cargandoDecision={decision.cargando}
                errorDecision={decision.error}
                onDecidir={(d) => {
                  if (rec.id_recomendacion)
                    void decision.ejecutar(rec.id_recomendacion, d);
                }}
              />
            ) : null}
          </section>

          <section className="seccion">
            <h2 className="seccion__titulo">Trayectoria</h2>
            {datosFicha.trayectoria.length > 0 ? (
              <ul className="lista">
                {datosFicha.trayectoria.map((obs) => (
                  <li key={obs.id_observacion} className="tarjeta">
                    <span className="tarjeta__meta">
                      <span>{formatearFecha(obs.fecha_observacion)}</span>
                      <span>Formato: {obs.formato_captura}</span>
                      {obs.nivel_estimado !== null ? (
                        <span>Nivel: {obs.nivel_estimado}</span>
                      ) : null}
                    </span>
                    {obs.nota_breve ? (
                      <p className="texto-pre">{obs.nota_breve}</p>
                    ) : null}
                    {obs.clasificacion ? (
                      <span className="chip-grupo">
                        {obs.clasificacion.dominios.map((d: Dominio) => (
                          <span key={d} className="chip">
                            {ETIQUETA_DOMINIO[d]}
                          </span>
                        ))}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="texto-vacio">
                Este nino/a aun no tiene observaciones registradas.
              </p>
            )}
          </section>
        </>
      ) : null}
    </section>
  );
}

function PanelRecomendacion({
  rec,
  decisionRegistrada,
  cargandoDecision,
  errorDecision,
  onDecidir,
}: {
  rec: Recomendacion;
  decisionRegistrada: string | null;
  cargandoDecision: boolean;
  errorDecision: string | null;
  onDecidir: (d: string) => void;
}) {
  if (rec.datos_insuficientes || rec.decision === null) {
    return (
      <div className="tarjeta">
        <span className="estado estado--insuficiente">Datos insuficientes</span>
        <p className="texto-pre">
          Aun no hay evidencia suficiente para recomendar un cambio de nivel.
          Registra mas observaciones (faltan {rec.observaciones_faltantes}).
        </p>
      </div>
    );
  }

  return (
    <div className="tarjeta">
      <span className={claseEstadoDecision(rec.decision)}>
        {ETIQUETA_DECISION[rec.decision]}
      </span>
      <span className="tarjeta__meta">
        <span>Tramo: {rec.tramo ?? "-"}</span>
        <span>Nucleo: {rec.nucleo ?? "-"}</span>
        <span>Nivel actual: {rec.nivel_actual ?? "-"}</span>
      </span>
      {rec.argumento_ia ? <p className="texto-pre">{rec.argumento_ia}</p> : null}

      <div className="seccion">
        <h3 className="seccion__titulo">Decisión de la educadora</h3>
        {decisionRegistrada ? (
          <p className="texto-exito" role="status">
            Decisión registrada: {decisionRegistrada}.
          </p>
        ) : (
          <div className="barra-acciones">
            {DECISIONES_EDUCADORA.map((d) => (
              <button
                key={d.valor}
                type="button"
                className="touch-target boton-secundario"
                disabled={cargandoDecision}
                onClick={() => onDecidir(d.valor)}
              >
                {d.etiqueta}
              </button>
            ))}
          </div>
        )}
        {cargandoDecision ? (
          <IndicadorCarga compacto mensaje="Registrando decision..." />
        ) : null}
        {errorDecision ? <MensajeError mensaje={errorDecision} /> : null}
      </div>
    </div>
  );
}
