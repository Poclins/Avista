// Capturar — registra una observación (texto, audio, foto o video) para un
// niño/a (Requirement 8.2). Envía multipart a POST /ninos/{id}/observaciones y,
// al recibir la clasificación propuesta, navega a la pantalla de confirmación.
// Sin lógica de negocio: la clasificación la propone el backend (Requirement 9.6).

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import type { FormatoCaptura, Observacion } from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";

const FORMATOS: { valor: FormatoCaptura; etiqueta: string }[] = [
  { valor: "texto", etiqueta: "Texto" },
  { valor: "audio", etiqueta: "Audio" },
  { valor: "foto", etiqueta: "Foto" },
  { valor: "video", etiqueta: "Video" },
];

const ACEPTA_ARCHIVO: Record<Exclude<FormatoCaptura, "texto">, string> = {
  audio: "audio/*",
  foto: "image/*",
  video: "video/*",
};

export function Capturar() {
  const navigate = useNavigate();
  const [idNino, setIdNino] = useState("");
  const [formato, setFormato] = useState<FormatoCaptura>("texto");
  const [texto, setTexto] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);

  const { cargando, error, ejecutar } = useAccionApi(
    (id: string, formData: FormData) => api.crearObservacion(id, formData),
  );

  async function enviar(e: FormEvent) {
    e.preventDefault();
    const id = idNino.trim();
    if (!id) return;

    // El cliente solo compone el multipart; el backend valida y clasifica.
    const formData = new FormData();
    formData.append("formato_captura", formato);
    if (formato === "texto") {
      formData.append("texto", texto);
    } else if (archivo) {
      formData.append("medio", archivo);
    }

    const observacion = (await ejecutar(id, formData)) as Observacion | null;
    if (observacion) {
      // Se pasa la observación propuesta por navegación para que la pantalla de
      // confirmación muestre la clasificación sin volver a pedirla al backend.
      navigate(
        `/educadora/observaciones/${encodeURIComponent(
          observacion.id_observacion,
        )}/clasificacion`,
        { state: { observacion } },
      );
    }
  }

  const faltaContenido =
    formato === "texto" ? texto.trim() === "" : archivo === null;

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Capturar observación</h1>
      <p className="pantalla__descripcion">
        Registra evidencia de un niño/a. El sistema propondrá una clasificación
        que podrás revisar y confirmar.
      </p>

      <form className="formulario" onSubmit={enviar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="id-nino">
            Identificador del niño/a
          </label>
          <input
            id="id-nino"
            value={idNino}
            onChange={(e) => setIdNino(e.target.value)}
            placeholder="Ej.: nino-0001"
            autoComplete="off"
          />
          <span className="campo__ayuda">
            Se usa el identificador seudónimo; nunca el nombre real ni el RUT.
          </span>
        </div>

        <div className="campo">
          <label className="campo__etiqueta" htmlFor="formato">
            Formato de captura
          </label>
          <select
            id="formato"
            value={formato}
            onChange={(e) => {
              setFormato(e.target.value as FormatoCaptura);
              setArchivo(null);
            }}
          >
            {FORMATOS.map((f) => (
              <option key={f.valor} value={f.valor}>
                {f.etiqueta}
              </option>
            ))}
          </select>
        </div>

        {formato === "texto" ? (
          <div className="campo">
            <label className="campo__etiqueta" htmlFor="texto">
              Observación
            </label>
            <textarea
              id="texto"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Describe lo observado…"
            />
          </div>
        ) : (
          <div className="campo">
            <label className="campo__etiqueta" htmlFor="archivo">
              Archivo ({formato})
            </label>
            <input
              id="archivo"
              type="file"
              accept={ACEPTA_ARCHIVO[formato]}
              onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
            />
            {archivo ? (
              <span className="campo__ayuda">Seleccionado: {archivo.name}</span>
            ) : null}
          </div>
        )}

        <div className="barra-acciones">
          <button
            type="submit"
            className="touch-target boton-primario"
            disabled={cargando || idNino.trim() === "" || faltaContenido}
          >
            Enviar y clasificar
          </button>
        </div>
      </form>

      {cargando ? (
        <IndicadorCarga mensaje="Enviando y clasificando la observación…" />
      ) : null}

      {error ? <MensajeError mensaje={error} /> : null}
    </section>
  );
}
