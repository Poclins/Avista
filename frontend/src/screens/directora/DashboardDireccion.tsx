// DashboardDireccion - reporte de direccion (Requirement 8.3). Consume
// GET /jardines/{id}/reportes (query fecha_inicio/fecha_fin). Sin logica de
// negocio: todas las metricas vienen del backend en reporte.metricas.

import { useState, type FormEvent } from "react";
import { api } from "../../api";
import type { ReporteDireccion } from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";

type Dict = Record<string, unknown>;
function obj(v: unknown): Dict { return (v && typeof v === "object") ? (v as Dict) : {}; }
function num(v: unknown): number { return typeof v === "number" ? v : 0; }

export function DashboardDireccion() {
  const [idJardin, setIdJardin] = useState("");
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFin, setPeriodoFin] = useState("");

  const { cargando, error, datos, ejecutar } = useAccionApi((id: string) =>
    api.obtenerReporteDireccion(id, {
      fecha_inicio: periodoInicio,
      fecha_fin: periodoFin,
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
      <h1 className="pantalla__titulo">Dashboard de direccion</h1>
      <p className="pantalla__descripcion">
        Metricas agregadas, KPI de tiempo ahorrado y resumen ejecutivo por
        jardin y periodo.
      </p>

      <form className="formulario" onSubmit={consultar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="id-jardin">
            Identificador del jardin
          </label>
          <input
            id="id-jardin"
            value={idJardin}
            onChange={(e) => setIdJardin(e.target.value)}
            placeholder="Ej.: JAR-0013"
            autoComplete="off"
          />
        </div>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="rep-inicio">Periodo - inicio</label>
          <input id="rep-inicio" type="date" value={periodoInicio}
            onChange={(e) => setPeriodoInicio(e.target.value)} />
        </div>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="rep-fin">Periodo - fin</label>
          <input id="rep-fin" type="date" value={periodoFin}
            onChange={(e) => setPeriodoFin(e.target.value)} />
        </div>
        <div className="barra-acciones">
          <button type="submit" className="touch-target boton-primario"
            disabled={cargando || idJardin.trim() === "" || periodoInicio === "" || periodoFin === ""}>
            Generar reporte
          </button>
        </div>
      </form>

      {cargando ? <IndicadorCarga mensaje="Generando el reporte..." /> : null}
      {error ? <MensajeError mensaje={error} /> : null}
      {reporte ? <VistaReporte reporte={reporte} /> : null}
    </section>
  );
}

function VistaReporte({ reporte }: { reporte: ReporteDireccion }) {
  const m = obj(reporte.metricas);
  const kpi = obj(m.kpi_tiempo_ahorrado);
  const obs = obj(m.observaciones);
  const bit = obj(m.bitacoras);
  const alertas = obj(m.alertas);
  const retroceso = Array.isArray(alertas.retroceso) ? (alertas.retroceso as string[]) : [];
  const inactividad = Array.isArray(alertas.inactividad) ? (alertas.inactividad as string[]) : [];

  // Totales de movimiento sumando el desglose por sala.
  const conteos = obj(m.conteos_nivel_por_sala);
  let subieron = 0, mantuvieron = 0, bajaron = 0;
  for (const cats of Object.values(conteos)) {
    const c = obj(cats);
    subieron += num(c.subieron);
    mantuvieron += num(c.mantuvieron);
    bajaron += num(c.bajaron);
  }

  return (
    <>
      <section className="seccion">
        <h2 className="seccion__titulo">Movimiento de niveles</h2>
        <div className="kpi-grid">
          <div className="kpi"><div className="kpi__valor">{subieron}</div><div className="kpi__etiqueta">Subieron</div></div>
          <div className="kpi"><div className="kpi__valor">{mantuvieron}</div><div className="kpi__etiqueta">Mantuvieron</div></div>
          <div className="kpi"><div className="kpi__valor">{bajaron}</div><div className="kpi__etiqueta">Bajaron</div></div>
        </div>
      </section>

      <section className="seccion">
        <h2 className="seccion__titulo">Indicadores</h2>
        <div className="kpi-grid">
          <div className="kpi"><div className="kpi__valor">{num(kpi.horas_ahorradas)}</div><div className="kpi__etiqueta">Horas ahorradas</div></div>
          <div className="kpi"><div className="kpi__valor">{num(obs.total)}</div><div className="kpi__etiqueta">Observaciones</div></div>
          <div className="kpi"><div className="kpi__valor">{num(bit.total)}</div><div className="kpi__etiqueta">Bitacoras</div></div>
        </div>
      </section>

      <TablaDistribucion titulo="Distribucion por sala" datos={obj(m.distribucion_niveles_por_sala)} />
      <TablaDistribucion titulo="Distribucion por dominio" datos={obj(m.distribucion_niveles_por_dominio)} />

      <section className="seccion">
        <h2 className="seccion__titulo">Alertas</h2>
        <h3 className="seccion__titulo">Retroceso</h3>
        {retroceso.length > 0 ? (
          <ul className="lista">{retroceso.map((a, i) => (<li key={`r-${i}`} className="tarjeta">{a}</li>))}</ul>
        ) : (<p className="texto-vacio">Sin alertas de retroceso.</p>)}
        <h3 className="seccion__titulo">Inactividad</h3>
        {inactividad.length > 0 ? (
          <ul className="lista">{inactividad.map((a, i) => (<li key={`i-${i}`} className="tarjeta">{a}</li>))}</ul>
        ) : (<p className="texto-vacio">Sin alertas de inactividad.</p>)}
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

function TablaDistribucion({ titulo, datos }: { titulo: string; datos: Record<string, unknown> }) {
  const filas = Object.entries(datos ?? {}).map(([k, v]) => [k, obj(v)] as [string, Dict]);
  const columnas = Array.from(new Set(filas.flatMap(([, cols]) => Object.keys(cols))));
  return (
    <section className="seccion">
      <h2 className="seccion__titulo">{titulo}</h2>
      {filas.length > 0 ? (
        <div className="tabla-scroll">
          <table className="tabla">
            <thead><tr><th scope="col">-</th>{columnas.map((c) => (<th key={c} scope="col">{c}</th>))}</tr></thead>
            <tbody>
              {filas.map(([fila, cols]) => (
                <tr key={fila}><th scope="row">{fila}</th>{columnas.map((c) => (<td key={c}>{num(cols[c])}</td>))}</tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (<p className="texto-vacio">Sin datos para este periodo.</p>)}
    </section>
  );
}
