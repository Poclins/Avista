// FichaNino — ficha y trayectoria de un niño/a (Requirement 8.2) con el flujo
// "¿Puede subir de nivel?" que muestra uno de 3 estados (avanzar / mantener /
// retroceder) y permite registrar la decisión de la educadora.
//
// Consume:
//   GET  /ninos/{id}                       → ficha + trayectoria
//   POST /ninos/{id}/recomendaciones       → recomendación de nivel (3 estados)
//   POST /recomendaciones/{id}/decision    → decisión de la educadora
//
// Sin lógica de negocio (Requirement 9.6): la decisión de nivel la calcula el
// backend (rúbrica determinista); el cliente solo la presenta y registra la
// respuesta de la educadora.

import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { api } from "../../api";
import type {
  DecisionEducadora,
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
} from "../etiquetas";
import type { Dominio } from "../../api/types";

const DECISIONES_EDUCADORA: { valor: DecisionEducadora; etiqueta: string }[] = [
  { valor: "acepto", etiqueta: "Aceptar" },
  { valor: "ajusto", etiqueta: "Ajustar" },
  { valor: "rechazo", etiqueta: "Rechazar" },
];

export function FichaNino() {
  const { idNino = "" } = useParams();

  const ficha = useAccionApi((id: string) => api.obtenerFichaNino(id));
  const recomendacion = useAccionApi((id: string) =>
    api.generarRecomendacion(id),
  );
  const decision = useAccionApi(
    (idRec: string, d: DecisionEducadora) =>
      api.registrarDecisionRecomendacion(idRec, { decision_educadora: d }),
  );

  useEffect(() => {
    if (idNino) void ficha.ejecutar(idNino);
    // Se recarga solo cuando cambia el niño/a.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idNino]);

  const datosFicha = ficha.datos as FichaNinoDTO | null;
  // La recomendación mostrada: la recién registrada con decisión o la generada.
  const rec = (decision.datos ?? recomendacion.datos) as Recomendacion | null;

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Ficha del niño/a</h1>
      <p className="pantalla__descripcion">
        Identificador <code>{idNino}</code>
      </p>

      {ficha.cargando ? (
        <IndicadorCarga mensaje="Cargando ficha…" />
      ) : ficha.error ? (
        <MensajeError
          mensaje={ficha.error}
          onReintentar={() => void ficha.ejecutar(idNino)}
        />
      ) : datosFicha ? (
        <>
          <div className="tarjeta">
            <span className="tarjeta__meta">
              <span>Sala: {datosFicha.nino.sala}</span>
              {datosFicha.nino.tramo ? (
                <span>Tramo: {datosFicha.nino.tramo}</span>
              ) : null}
            </span>
          </div>

          {/* --- "¿Puede subir de nivel?" --- */}
          <section className="seccion">
            <h2 className="seccion__titulo">¿Puede subir de nivel?</h2>
            <div className="barra-acciones">
              <button
                type="button"
                className="touch-target boton-primario"
                disabled={recomendacion.cargando}
                onClick={() => void recomendacion.ejecutar(idNino)}
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

            {rec ? <PanelRecomendacion rec={rec} decision={decision} /> : null}
          </section>

          {/* --- Trayectoria de observaciones --- */}
          <section className="seccion">
            <h2 className="seccion__titulo">Trayectoria</h2>
            {datosFicha.observaciones.length > 0 ? (
              <ul className="lista">
                {datosFicha.observaciones.map((obs) => (
                  <li key={obs.id_observacion} className="tarjeta">
                    <span className="tarjeta__meta">
                      <span>{formatearFecha(obs.fecha)}</span>
                      <span>Formato: {obs.formato_captura}</span>
                      {obs.clasificacion ? (
                        <span>Nivel: {obs.clasificacion.nivel_estimado}</span>
                      ) : null}
                    </span>
                    {obs.texto ? (
                      <p className="texto-pre">{obs.texto}</p>
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
                Este niño/a aún no tiene observaciones registradas.
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
  decision,
}: {
  rec: Recomendacion;
  decision: ReturnType<typeof useAccionApi<[string, DecisionEducadora], Recomendacion>>;
}) {
  if (rec.datos_insuficientes) {
    return (
      <div className="tarjeta">
        <span className="estado estado--insuficiente">Datos insuficientes</span>
        <p className="texto-pre">
          Aún no hay evidencia suficiente para recomendar un cambio de nivel.
          Registra más observaciones.
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
        <span>Tramo: {rec.tramo}</span>
        <span>Núcleo: {rec.nucleo}</span>
        <span>Nivel actual: {rec.nivel_actual}</span>
      </span>
      {rec.argumento ? <p className="texto-pre">{rec.argumento}</p> : null}

      <div className="seccion">
        <h3 className="seccion__titulo">Decisión de la educadora</h3>
        {rec.decision_educadora ? (
          <p className="texto-exito" role="status">
            Decisión registrada: {rec.decision_educadora}.
          </p>
        ) : (
          <div className="barra-acciones">
            {DECISIONES_EDUCADORA.map((d) => (
              <button
                key={d.valor}
                type="button"
                className="touch-target boton-secundario"
                disabled={decision.cargando}
                onClick={() =>
                  void decision.ejecutar(rec.id_recomendacion, d.valor)
                }
              >
                {d.etiqueta}
              </button>
            ))}
          </div>
        )}
        {decision.cargando ? (
          <IndicadorCarga compacto mensaje="Registrando decisión…" />
        ) : null}
        {decision.error ? <MensajeError mensaje={decision.error} /> : null}
      </div>
    </div>
  );
}
