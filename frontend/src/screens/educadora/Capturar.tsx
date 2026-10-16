// Capturar - registra una observación para un niño/a seleccionado desde los
// niños del jardín de la educadora activa. El backend clasifica la evidencia.

import { useEffect, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../../api";
import type {
  Educadora,
  FormatoCaptura,
  Nino,
  Observacion,
} from "../../api/types";
import { useAccionApi } from "../../hooks/useAccionApi";
import { IndicadorCarga } from "../../components/IndicadorCarga";
import { MensajeError } from "../../components/MensajeError";
import { nombreCompletoNino } from "../etiquetas";

const FORMATOS: { valor: "texto" | "audio"; etiqueta: string }[] = [
  { valor: "texto", etiqueta: "Texto" },
  { valor: "audio", etiqueta: "Audio" },
];

const ACEPTA_AUDIO = ".wav,.ogg,.opus,.mp3,audio/wav,audio/ogg,audio/opus,audio/mpeg";

export function Capturar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [mensajeExito] = useState(() =>
    (location.state as { mensajeExito?: string } | null)?.mensajeExito ?? null,
  );
  const [idEducadora, setIdEducadora] = useState("");
  const [idNino, setIdNino] = useState("");
  const [formato, setFormato] = useState<FormatoCaptura>("texto");
  const [texto, setTexto] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);

  const educadorasApi = useAccionApi(api.listarEducadoras);
  const ninosApi = useAccionApi(api.listarNinosDeEducadora);
  const captura = useAccionApi(
    (id: string, formData: FormData) => api.crearObservacion(id, formData),
  );

  const educadoras = (educadorasApi.datos ?? []) as Educadora[];
  const ninos = (ninosApi.datos ?? []) as Nino[];

  useEffect(() => {
    if (mensajeExito) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, mensajeExito, navigate]);

  useEffect(() => {
    void educadorasApi.ejecutar();
    // La función importada es estable y solo se carga al montar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (educadoras.length === 0 || idEducadora) return;
    const preferida =
      educadoras.find((educadora) => educadora.id_educadora === "EDU-0001") ??
      educadoras[0];
    setIdEducadora(preferida.id_educadora);
  }, [educadoras, idEducadora]);

  useEffect(() => {
    setIdNino("");
    if (idEducadora) void ninosApi.ejecutar(idEducadora);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idEducadora]);

  useEffect(() => {
    if (ninos.length > 0 && !idNino) setIdNino(ninos[0].id_nino);
  }, [ninos, idNino]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!idNino || !idEducadora) return;

    const formData = new FormData();
    formData.append("id_educadora", idEducadora);
    formData.append("formato", formato);
    if (formato === "texto") {
      formData.append("texto", texto.trim());
    } else if (archivo) {
      formData.append("archivo", archivo);
    }

    const observacion = (await captura.ejecutar(idNino, formData)) as
      | Observacion
      | null;
    if (observacion) {
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
  const cargandoOpciones = educadorasApi.cargando || ninosApi.cargando;

  return (
    <section className="pantalla">
      <h1 className="pantalla__titulo">Capturar observación</h1>
      <p className="pantalla__descripcion">
        Selecciona una educadora y uno de los niños/as de su jardín. El sistema
        propondrá una clasificación que podrás revisar.
      </p>

      {mensajeExito ? (
        <p className="texto-exito" role="status">{mensajeExito}</p>
      ) : null}

      <form className="formulario" onSubmit={enviar}>
        <div className="campo">
          <label className="campo__etiqueta" htmlFor="id-educadora">
            Educadora
          </label>
          <select
            id="id-educadora"
            value={idEducadora}
            onChange={(e) => setIdEducadora(e.target.value)}
            disabled={educadorasApi.cargando}
          >
            <option value="">Selecciona una educadora</option>
            {educadoras.map((educadora) => (
              <option key={educadora.id_educadora} value={educadora.id_educadora}>
                {educadora.id_educadora} · {educadora.id_jardin} · {educadora.rol}
              </option>
            ))}
          </select>
        </div>

        <div className="campo">
          <label className="campo__etiqueta" htmlFor="id-nino">
            Niño/a del jardín
          </label>
          <select
            id="id-nino"
            value={idNino}
            onChange={(e) => setIdNino(e.target.value)}
            disabled={!idEducadora || ninosApi.cargando}
          >
            <option value="">
              {ninosApi.cargando ? "Cargando niños/as…" : "Selecciona un niño/a"}
            </option>
            {ninos.map((nino) => (
              <option key={nino.id_nino} value={nino.id_nino}>
                {nombreCompletoNino(nino)} · sala {nino.sala_grupo}
              </option>
            ))}
          </select>
          {idEducadora && !ninosApi.cargando ? (
            <span className="campo__ayuda">
              {ninos.length} niño(s)/a(s) relacionados por jardín.
            </span>
          ) : null}
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
            {FORMATOS.map((opcion) => (
              <option key={opcion.valor} value={opcion.valor}>
                {opcion.etiqueta}
              </option>
            ))}
          </select>
        </div>

        {formato === "texto" ? (
          <div className="campo">
            <label className="campo__etiqueta" htmlFor="texto">Observación</label>
            <textarea
              id="texto"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Describe una conducta observable…"
            />
          </div>
        ) : (
          <div className="campo">
            <label className="campo__etiqueta" htmlFor="archivo">
              Archivo de audio WAV, OGG, Opus o MP3
            </label>
            <input
              id="archivo"
              type="file"
              accept={ACEPTA_AUDIO}
              onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
            />
                        <span className="campo__ayuda">
              WAV, OGG, Opus o MP3 de hasta 60 segundos. Se convierte automáticamente a mono 16 kHz.
            </span>
            {archivo ? (
              <span className="campo__ayuda">Seleccionado: {archivo.name}</span>
            ) : null}
          </div>
        )}

        <div className="barra-acciones">
          <button
            type="submit"
            className="touch-target boton-primario"
            disabled={
              captura.cargando || cargandoOpciones || !idNino || !idEducadora || faltaContenido
            }
          >
            Enviar y clasificar
          </button>
        </div>
      </form>

      {cargandoOpciones ? <IndicadorCarga mensaje="Cargando opciones…" /> : null}
      {captura.cargando ? (
        <IndicadorCarga mensaje="Enviando y clasificando la observación…" />
      ) : null}
      {educadorasApi.error ? <MensajeError mensaje={educadorasApi.error} /> : null}
      {ninosApi.error ? <MensajeError mensaje={ninosApi.error} /> : null}
      {captura.error ? <MensajeError mensaje={captura.error} /> : null}
    </section>
  );
}
