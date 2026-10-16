// Bitacoras — ver, generar, editar y aprobar bitácoras quincenales de un
// niño/a (Requirement 8.2).
//
// Consume:
//   GET   /ninos/{id}/bitacoras   → listar
//   POST  /ninos/{id}/bitacoras   → generar (body: periodo)
//   PATCH /bitacoras/{id}         → editar (contenido) / aprobar (estado)
//
// Sin lógica de negocio (Requirement 9.6): el contenido lo genera el backend
// (RAG + LLM); el cliente solo muestra, edita el texto y cambia el estado.

import { useState, type FormEvent } from "react";
import { api } from "../../api";
import type { Bitacora } from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";
import { formatearFecha } from "../etiquetas";

export function Bitacoras() {
  const [idNino, setIdNino] = useState("");
  const [idConsultado, setIdConsultado] = useState<string | null>(null);
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFin, setPeriodoFin] = useState("");

  const listado = useAccionApi((id: string) => api.listarBitacoras(id));
  const generar = useAccionApi(
    (id: string) =>
      api.generarBitacora(id, {
        periodo_inicio: periodoInicio,
        periodo_fin: periodoFin,
      }),
  );

  const bitacoras = (listado.datos ?? []) as Bitacora[];

  function consultar(e: FormEvent) {
    e.preventDefault();
    const id = idNino.trim();
    if (!id) return;
    setIdConsultado(id);
    void listado.ejecutar(id);
  }

  async function generarBitacora() {
    if (!idConsultado) return;
    const nueva = await generar.ejecutar(idConsultado);
    if (nueva) void listado.ejecutar(idConsultado);
  }

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Bitácoras</h1>
      <p className="pantalla__descripcion">
        Consulta las bitácoras de un niño/a, genera una nueva para un período y
        edítala o apruébala.
      </p>

      <form className="formulario" onSubmit={consultar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="id-nino-bit">
            Identificador del niño/a
          </label>
          <input
            id="id-nino-bit"
            value={idNino}
            onChange={(e) => setIdNino(e.target.value)}
            placeholder="Ej.: nino-0001"
            autoComplete="off"
          />
        </div>
        <div className="barra-acciones">
          <button
            type="submit"
            className="touch-target boton-primario"
            disabled={listado.cargando || idNino.trim() === ""}
          >
            Ver bitácoras
          </button>
        </div>
      </form>

      {idConsultado !== null ? (
        <section className="seccion">
          <h2 className="seccion__titulo">Generar bitácora</h2>
          <div className="formulario">
            <div className="campo">
              <label className="campo__etiqueta" htmlFor="periodo-inicio">
                Período — inicio
              </label>
              <input
                id="periodo-inicio"
                type="date"
                value={periodoInicio}
                onChange={(e) => setPeriodoInicio(e.target.value)}
              />
            </div>
            <div className="campo">
              <label className="campo__etiqueta" htmlFor="periodo-fin">
                Período — fin
              </label>
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
                  periodoInicio === "" ||
                  periodoFin === ""
                }
                onClick={() => void generarBitacora()}
              >
                Generar bitácora
              </button>
            </div>
          </div>
          {generar.cargando ? (
            <IndicadorCarga mensaje="Generando la bitácora…" />
          ) : null}
          {generar.error ? <MensajeError mensaje={generar.error} /> : null}
        </section>
      ) : null}

      {listado.cargando ? (
        <IndicadorCarga mensaje="Cargando bitácoras…" />
      ) : null}
      {listado.error ? (
        <MensajeError
          mensaje={listado.error}
          onReintentar={
            idConsultado ? () => void listado.ejecutar(idConsultado) : undefined
          }
        />
      ) : null}

      {!listado.cargando && !listado.error && idConsultado !== null ? (
        bitacoras.length > 0 ? (
          <ul className="lista">
            {bitacoras.map((b) => (
              <TarjetaBitacora
                key={b.id_bitacora}
                bitacora={b}
                onCambio={() =>
                  idConsultado ? void listado.ejecutar(idConsultado) : undefined
                }
              />
            ))}
          </ul>
        ) : (
          <p className="texto-vacio">
            No hay bitácoras para este niño/a. Genera una nueva arriba.
          </p>
        )
      ) : null}
    </section>
  );
}

function TarjetaBitacora({
  bitacora,
  onCambio,
}: {
  bitacora: Bitacora;
  onCambio: () => void;
}) {
  const [editando, setEditando] = useState(false);
  const [contenido, setContenido] = useState(bitacora.contenido);

  const editar = useAccionApi(() =>
    api.editarBitacora(bitacora.id_bitacora, { contenido }),
  );
  const aprobar = useAccionApi(() =>
    api.editarBitacora(bitacora.id_bitacora, { estado: "aprobada" }),
  );

  const esBorrador = bitacora.estado === "borrador";

  async function guardar() {
    const ok = await editar.ejecutar();
    if (ok) {
      setEditando(false);
      onCambio();
    }
  }

  async function aprobarBitacora() {
    const ok = await aprobar.ejecutar();
    if (ok) onCambio();
  }

  return (
    <li className="tarjeta">
      <span className="tarjeta__meta">
        <span>
          {formatearFecha(bitacora.periodo_inicio)} –{" "}
          {formatearFecha(bitacora.periodo_fin)}
        </span>
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
        <p className="texto-pre">{bitacora.contenido}</p>
      )}

      {bitacora.citas.length > 0 ? (
        <span className="campo__ayuda">
          Citas: {bitacora.citas.join(", ")}
        </span>
      ) : null}

      <div className="barra-acciones">
        {esBorrador && !editando ? (
          <button
            type="button"
            className="touch-target boton-secundario"
            onClick={() => {
              setContenido(bitacora.contenido);
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

      {editar.cargando ? (
        <IndicadorCarga compacto mensaje="Guardando…" />
      ) : null}
      {aprobar.cargando ? (
        <IndicadorCarga compacto mensaje="Aprobando…" />
      ) : null}
      {editar.error ? <MensajeError mensaje={editar.error} /> : null}
      {aprobar.error ? <MensajeError mensaje={aprobar.error} /> : null}
    </li>
  );
}
