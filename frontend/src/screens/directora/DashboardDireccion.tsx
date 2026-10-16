// DashboardDireccion — reporte de dirección (Requirement 8.3): métricas
// agregadas, KPI de tiempo ahorrado y resumen ejecutivo para un jardín y período.
//
// Consume GET /jardines/{id}/reportes (query: periodo). Sin lógica de negocio
// (Requirement 9.6): todas las métricas vienen calculadas desde el backend
// (SQL + LLM); el cliente solo las presenta.

import { useState, type FormEvent } from "react";
import { api } from "../../api";
import type { ReporteDireccion } from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";

export function DashboardDireccion() {
  const [idJardin, setIdJardin] = useState("");
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFin, setPeriodoFin] = useState("");

  const { cargando, error, datos, ejecutar } = useAccionApi((id: string) =>
    api.obtenerReporteDireccion(id, {
      periodo_inicio: periodoInicio,
      periodo_fin: periodoFin,
    }),
  );
  const reporte = datos as ReporteDireccion | null;

  function consultar(e: FormEvent) {
    e.preventDefault();
    const id = idJardin.trim();
    if (!id || !periodoInicio || !periodoFin) return;
    void ejecutar(id);
  }

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Dashboard de dirección</h1>
      <p className="pantalla__descripcion">
        Métricas agregadas, KPI de tiempo ahorrado y resumen ejecutivo por
        jardín y período.
      </p>

      <form className="formulario" onSubmit={consultar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="id-jardin">
            Identificador del jardín
          </label>
          <input
            id="id-jardin"
            value={idJardin}
            onChange={(e) => setIdJardin(e.target.value)}
            placeholder="Ej.: jardin-001"
            autoComplete="off"
          />
        </div>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="rep-inicio">
            Período — inicio
          </label>
          <input
            id="rep-inicio"
            type="date"
            value={periodoInicio}
            onChange={(e) => setPeriodoInicio(e.target.value)}
          />
        </div>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="rep-fin">
            Período — fin
          </label>
          <input
            id="rep-fin"
            type="date"
            value={periodoFin}
            onChange={(e) => setPeriodoFin(e.target.value)}
          />
        </div>
        <div className="barra-acciones">
          <button
            type="submit"
            className="touch-target boton-primario"
            disabled={
              cargando ||
              idJardin.trim() === "" ||
              periodoInicio === "" ||
              periodoFin === ""
            }
          >
            Generar reporte
          </button>
        </div>
      </form>

      {cargando ? <IndicadorCarga mensaje="Generando el reporte…" /> : null}
      {error ? <MensajeError mensaje={error} /> : null}

      {reporte ? <VistaReporte reporte={reporte} /> : null}
    </section>
  );
}

function VistaReporte({ reporte }: { reporte: ReporteDireccion }) {
  return (
    <>
      <section className="seccion">
        <h2 className="seccion__titulo">Movimiento de niveles</h2>
        <div className="kpi-grid">
          <div className="kpi">
            <div className="kpi__valor">{reporte.subieron}</div>
            <div className="kpi__etiqueta">Subieron</div>
          </div>
          <div className="kpi">
            <div className="kpi__valor">{reporte.mantuvieron}</div>
            <div className="kpi__etiqueta">Mantuvieron</div>
          </div>
          <div className="kpi">
            <div className="kpi__valor">{reporte.bajaron}</div>
            <div className="kpi__etiqueta">Bajaron</div>
          </div>
        </div>
      </section>

      <section className="seccion">
        <h2 className="seccion__titulo">Indicadores</h2>
        <div className="kpi-grid">
          <div className="kpi">
            <div className="kpi__valor">
              {reporte.kpi_tiempo_ahorrado_horas}
            </div>
            <div className="kpi__etiqueta">Horas ahorradas</div>
          </div>
          <div className="kpi">
            <div className="kpi__valor">{reporte.total_observaciones}</div>
            <div className="kpi__etiqueta">Observaciones</div>
          </div>
          <div className="kpi">
            <div className="kpi__valor">{reporte.total_bitacoras}</div>
            <div className="kpi__etiqueta">Bitácoras</div>
          </div>
        </div>
      </section>

      <TablaDistribucion
        titulo="Distribución por sala"
        datos={reporte.distribucion_por_sala}
      />
      <TablaDistribucion
        titulo="Distribución por dominio"
        datos={reporte.distribucion_por_dominio}
      />

      <section className="seccion">
        <h2 className="seccion__titulo">Alertas</h2>
        <h3 className="seccion__titulo">Retroceso</h3>
        {reporte.alertas_retroceso.length > 0 ? (
          <ul className="lista">
            {reporte.alertas_retroceso.map((a, i) => (
              <li key={`r-${i}`} className="tarjeta">
                {a}
              </li>
            ))}
          </ul>
        ) : (
          <p className="texto-vacio">Sin alertas de retroceso.</p>
        )}
        <h3 className="seccion__titulo">Inactividad</h3>
        {reporte.alertas_inactividad.length > 0 ? (
          <ul className="lista">
            {reporte.alertas_inactividad.map((a, i) => (
              <li key={`i-${i}`} className="tarjeta">
                {a}
              </li>
            ))}
          </ul>
        ) : (
          <p className="texto-vacio">Sin alertas de inactividad.</p>
        )}
      </section>

      {reporte.resumen_ejecutivo ? (
        <section className="seccion">
          <h2 className="seccion__titulo">Resumen ejecutivo</h2>
          <p className="texto-pre">{reporte.resumen_ejecutivo}</p>
        </section>
      ) : null}
    </>
  );
}

function TablaDistribucion({
  titulo,
  datos,
}: {
  titulo: string;
  datos: Record<string, Record<string, number>>;
}) {
  const filas = Object.entries(datos ?? {});
  // Columnas = unión de todas las claves internas (presentación, no negocio).
  const columnas = Array.from(
    new Set(filas.flatMap(([, cols]) => Object.keys(cols))),
  );

  return (
    <section className="seccion">
      <h2 className="seccion__titulo">{titulo}</h2>
      {filas.length > 0 ? (
        <div className="tabla-scroll">
          <table className="tabla">
            <thead>
              <tr>
                <th scope="col">—</th>
                {columnas.map((c) => (
                  <th key={c} scope="col">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filas.map(([fila, cols]) => (
                <tr key={fila}>
                  <th scope="row">{fila}</th>
                  {columnas.map((c) => (
                    <td key={c}>{cols[c] ?? 0}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="texto-vacio">Sin datos para este período.</p>
      )}
    </section>
  );
}
