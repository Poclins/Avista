// Bitacoras - consultar, generar, editar y aprobar bitacoras quincenales.
// La pantalla selecciona automaticamente una ventana de 14 dias que contiene
// evidencia real del nino/a, evitando solicitudes sin observaciones.

import { useEffect, useState, type FormEvent } from "react";
import { api } from "../../api";
import type { Bitacora, Educadora, Nino, Observacion } from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";
import { nombreCompletoNino } from "../etiquetas";

export function numerarReferenciasObservaciones(texto: string): string {
  const indices = new Map<string, number>();
  return texto.replace(
    /(?:observaci[oó]n\s+)?(OBS-\d+|[a-f0-9]{32})/gi,
    (_coincidencia, identificador: string) => {
      const clave = identificador.toLowerCase();
      if (!indices.has(clave)) indices.set(clave, indices.size + 1);
      return `Observación ${indices.get(clave)}`;
    },
  );
}
function textoVisibleBitacora(texto: string, nino?: Nino): string {
  const numerado = numerarReferenciasObservaciones(texto);
  return nino
    ? numerado.split(nino.id_nino).join(nombreCompletoNino(nino))
    : numerado;
}
function restarDias(fechaIso: string, dias: number): string {
  const fecha = new Date(`${fechaIso}T00:00:00Z`);
  fecha.setUTCDate(fecha.getUTCDate() - dias);
  return fecha.toISOString().slice(0, 10);
}

function ultimaObservacion(observaciones: Observacion[]): Observacion | null {
  if (observaciones.length === 0) return null;
  return [...observaciones].sort((a, b) =>
    a.fecha_observacion.localeCompare(b.fecha_observacion),
  )[observaciones.length - 1];
}

export function Bitacoras() {
  const [idNino, setIdNino] = useState("");
  const [idConsultado, setIdConsultado] = useState<string | null>(null);
  const [idEducadora, setIdEducadora] = useState("");
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFin, setPeriodoFin] = useState("");
  const [evidenciaPeriodo, setEvidenciaPeriodo] = useState(0);

  const educadorasApi = useAccionApi(api.listarEducadoras);
  const ninosApi = useAccionApi(api.listarNinosDeEducadora);

  const listado = useAccionApi((id: string) => api.listarBitacoras(id));
  const evidencia = useAccionApi((id: string) => api.listarObservaciones(id));
  const generar = useAccionApi((id: string) =>
    api.generarBitacora(id, {
      id_educadora: idEducadora,
      fecha_inicio: periodoInicio,
      fecha_fin: periodoFin,
    }),
  );

  const bitacoras = (listado.datos ?? []) as Bitacora[];
  const educadoras = (educadorasApi.datos ?? []) as Educadora[];
  const ninos = (ninosApi.datos ?? []) as Nino[];
  const ninoConsultado = ninos.find((nino) => nino.id_nino === idConsultado);

  useEffect(() => {
    void educadorasApi.ejecutar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (educadoras.length > 0 && !idEducadora) {
      const preferida = educadoras.find((e) => e.id_educadora === "EDU-0001") ?? educadoras[0];
      setIdEducadora(preferida.id_educadora);
    }
  }, [educadoras, idEducadora]);

  useEffect(() => {
    setIdNino("");
    setIdConsultado(null);
    if (idEducadora) void ninosApi.ejecutar(idEducadora);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idEducadora]);

  useEffect(() => {
    if (ninos.length > 0 && !idNino) setIdNino(ninos[0].id_nino);
  }, [ninos, idNino]);

  async function consultar(e: FormEvent) {
    e.preventDefault();
    const id = idNino.trim();
    if (!id) return;

    setIdConsultado(id);
    void listado.ejecutar(id);
    const observaciones = await evidencia.ejecutar(id);
    const ultima = ultimaObservacion(observaciones ?? []);

    if (ultima) {
      const fin = ultima.fecha_observacion;
      const inicio = restarDias(fin, 13);
      setPeriodoInicio(inicio);
      setPeriodoFin(fin);
      setEvidenciaPeriodo(
        (observaciones ?? []).filter(
          (obs) => obs.fecha_observacion >= inicio && obs.fecha_observacion <= fin,
        ).length,
      );
    } else {
      setPeriodoInicio("");
      setPeriodoFin("");
      setIdEducadora("");
      setEvidenciaPeriodo(0);
    }
  }

  async function generarBitacora() {
    if (!idConsultado || !idEducadora || !periodoInicio || !periodoFin) return;
    const nueva = await generar.ejecutar(idConsultado);
    if (nueva) void listado.ejecutar(idConsultado);
  }

  const cargandoConsulta = listado.cargando || evidencia.cargando;

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Bitácoras</h1>
      <p className="pantalla__descripcion">
        Consulta un niño/a. El sistema elegirá automáticamente un período con
        evidencia para generar la bitácora localmente.
      </p>

      <form className="formulario" onSubmit={consultar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="educadora-bit">Educadora</label>
          <select
            id="educadora-bit"
            value={idEducadora}
            onChange={(e) => setIdEducadora(e.target.value)}
          >
            <option value="">Selecciona una educadora</option>
            {educadoras.map((educadora) => (
              <option key={educadora.id_educadora} value={educadora.id_educadora}>
                {educadora.id_educadora} · {educadora.id_jardin}
              </option>
            ))}
          </select>
        </div>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="id-nino-bit">Niño/a</label>
          <select
            id="id-nino-bit"
            value={idNino}
            onChange={(e) => setIdNino(e.target.value)}
            disabled={!idEducadora || ninosApi.cargando}
          >
            <option value="">Selecciona un niño/a</option>
            {ninos.map((nino) => (
              <option key={nino.id_nino} value={nino.id_nino}>
                {nombreCompletoNino(nino)} · sala {nino.sala_grupo}
              </option>
            ))}
          </select>
        </div>
        <div className="barra-acciones">
          <button
            type="submit"
            className="touch-target boton-primario"
            disabled={cargandoConsulta || !idNino || !idEducadora}
          >
            Ver bitácoras
          </button>
        </div>
      </form>

      {cargandoConsulta ? <IndicadorCarga mensaje="Cargando evidencia…" /> : null}
      {evidencia.error ? <MensajeError mensaje={evidencia.error} /> : null}

      {idConsultado !== null && !cargandoConsulta ? (
        <section className="seccion">
          <h2 className="seccion__titulo">
            Bitácoras de {ninoConsultado ? nombreCompletoNino(ninoConsultado) : "niño/a"}
          </h2>
          {evidenciaPeriodo > 0 ? (
            <p className="texto-exito" role="status">
              Período sugerido con {evidenciaPeriodo} observación(es). Educadora: {idEducadora}.
            </p>
          ) : (
            <p className="texto-vacio">
              Este niño/a no tiene observaciones disponibles para generar una bitácora.
            </p>
          )}
          <div className="formulario">
            <div className="campo">
              <label className="campo__etiqueta" htmlFor="periodo-inicio">Inicio</label>
              <input
                id="periodo-inicio"
                type="date"
                value={periodoInicio}
                onChange={(e) => setPeriodoInicio(e.target.value)}
              />
            </div>
            <div className="campo">
              <label className="campo__etiqueta" htmlFor="periodo-fin">Fin</label>
              <input
                id="periodo-fin"
                type="date"
                value={periodoFin}
                onChange={(e) => setPeriodoFin(e.target.value)}
              />
            </div>
            <div className="barra-acciones">
              <button
                type="button"
                className="touch-target boton-secundario"
                disabled={
                  generar.cargando ||
                  !idEducadora ||
                  periodoInicio === "" ||
                  periodoFin === ""
                }
                onClick={() => void generarBitacora()}
              >
                Generar bitácora
              </button>
            </div>
          </div>
          {generar.cargando ? <IndicadorCarga mensaje="Generando la bitácora…" /> : null}
          {generar.error ? <MensajeError mensaje={generar.error} /> : null}
        </section>
      ) : null}

      {listado.error ? (
        <MensajeError
          mensaje={listado.error}
          onReintentar={idConsultado ? () => void listado.ejecutar(idConsultado) : undefined}
        />
      ) : null}

      {!listado.cargando && !listado.error && idConsultado !== null ? (
        bitacoras.length > 0 ? (
          <ul className="lista">
            {bitacoras.map((bitacora) => (
              <TarjetaBitacora
                key={bitacora.id_bitacora}
                bitacora={bitacora}
                nino={ninoConsultado}
                onCambio={() => void listado.ejecutar(idConsultado)}
              />
            ))}
          </ul>
        ) : (
          <p className="texto-vacio">No hay bitácoras guardadas para este niño/a.</p>
        )
      ) : null}
    </section>
  );
}

function TarjetaBitacora({
  bitacora,
  nino,
  onCambio,
}: {
  bitacora: Bitacora;
  nino?: Nino;
  onCambio: () => void;
}) {
  const [editando, setEditando] = useState(false);
  const [contenido, setContenido] = useState(textoVisibleBitacora(bitacora.texto_generado, nino));
  const editar = useAccionApi(() =>
    api.editarBitacora(bitacora.id_bitacora, { accion: "editar", texto: contenido }),
  );
  const aprobar = useAccionApi(() =>
    api.editarBitacora(bitacora.id_bitacora, { accion: "aprobar" }),
  );
  const esBorrador = bitacora.estado === "borrador";

  async function guardar() {
    const actualizada = await editar.ejecutar();
    if (actualizada) {
      setEditando(false);
      onCambio();
    }
  }

  async function aprobarBitacora() {
    const actualizada = await aprobar.ejecutar();
    if (actualizada) onCambio();
  }

  return (
    <li className="tarjeta">
      <span className="tarjeta__meta">
        <span>{bitacora.periodo}</span>
        <span className="chip">{bitacora.estado}</span>
      </span>

      {editando ? (
        <div className="campo">
          <textarea
            value={contenido}
            onChange={(e) => setContenido(e.target.value)}
            aria-label="Contenido de la bitácora"
          />
        </div>
      ) : (
        <p className="texto-pre">
          {textoVisibleBitacora(bitacora.texto_generado, nino)}
        </p>
      )}

      <div className="barra-acciones">
        {esBorrador && !editando ? (
          <button
            type="button"
            className="touch-target boton-secundario"
            onClick={() => {
              setContenido(textoVisibleBitacora(bitacora.texto_generado, nino));
              setEditando(true);
            }}
          >
            Editar
          </button>
        ) : null}
        {esBorrador && editando ? (
          <>
            <button
              type="button"
              className="touch-target boton-primario"
              disabled={editar.cargando}
              onClick={() => void guardar()}
            >
              Guardar cambios
            </button>
            <button
              type="button"
              className="touch-target boton-secundario"
              onClick={() => setEditando(false)}
            >
              Cancelar
            </button>
          </>
        ) : null}
        {esBorrador && !editando ? (
          <button
            type="button"
            className="touch-target boton-primario"
            disabled={aprobar.cargando}
            onClick={() => void aprobarBitacora()}
          >
            Aprobar
          </button>
        ) : null}
      </div>

      {editar.cargando ? <IndicadorCarga compacto mensaje="Guardando…" /> : null}
      {aprobar.cargando ? <IndicadorCarga compacto mensaje="Aprobando…" /> : null}
      {editar.error ? <MensajeError mensaje={editar.error} /> : null}
      {aprobar.error ? <MensajeError mensaje={aprobar.error} /> : null}
    </li>
  );
}
