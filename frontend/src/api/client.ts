// Cliente HTTP tipado para la API REST del backend (Módulo G).
//
// Responsabilidades (sin lógica de negocio, Requirement 9.6):
//  - componer la URL base desde VITE_API_BASE_URL,
//  - aplicar un timeout de 10 s por solicitud (Requirement 9.7),
//  - traducir fallos/timeout a un error tipado con mensaje en español,
//    de modo que las pantallas puedan mostrarlo SIN descartar los datos
//    ingresados por la educadora (Requirement 9.7).

/** Timeout por solicitud, en milisegundos (Requirement 9.7). */
export const REQUEST_TIMEOUT_MS = 10_000;

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "/api"
).replace(/\/$/, "");

/** Error tipado que las pantallas pueden mostrar sin perder los datos del formulario. */
export class ApiError extends Error {
  readonly status: number | null;
  readonly isTimeout: boolean;
  readonly detalle?: string;

  constructor(
    mensaje: string,
    opciones: { status?: number | null; isTimeout?: boolean; detalle?: string } = {},
  ) {
    super(mensaje);
    this.name = "ApiError";
    this.status = opciones.status ?? null;
    this.isTimeout = opciones.isTimeout ?? false;
    this.detalle = opciones.detalle;
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  /** Cuerpo JSON. Si se usa `formData`, se ignora. */
  body?: unknown;
  /** Cuerpo multipart (p. ej. subir medios). Tiene prioridad sobre `body`. */
  formData?: FormData;
  /** Parámetros de query string. */
  query?: Query;
  /** Timeout particular; por defecto usa REQUEST_TIMEOUT_MS. */
  timeoutMs?: number;
  /** Señal externa para permitir cancelación adicional por el llamador. */
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: Query): string {
  const base = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  if (!query) return base;
  const params = new URLSearchParams();
  for (const [clave, valor] of Object.entries(query)) {
    if (valor !== undefined && valor !== null) {
      params.append(clave, String(valor));
    }
  }
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
}

async function extraerMensajeError(resp: Response): Promise<string | undefined> {
  try {
    const data = await resp.clone().json();
    // El backend responde errores en español, típicamente en `detail`.
    if (typeof data === "string") return data;
    if (data && typeof data === "object") {
      const d = data as Record<string, unknown>;
      if (typeof d.detail === "string") return d.detail;
      if (typeof d.mensaje === "string") return d.mensaje;
      if (typeof d.message === "string") return d.message;
    }
  } catch {
    // cuerpo no-JSON: se ignora y se usa el mensaje genérico.
  }
  return undefined;
}

/**
 * Realiza una solicitud a la API REST con timeout de 10 s.
 * Lanza `ApiError` (en español) ante fallo de red, timeout o estado HTTP de error.
 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = "GET",
    body,
    formData,
    query,
    signal,
    timeoutMs = REQUEST_TIMEOUT_MS,
  } = options;

  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), timeoutMs);

  // Combina la señal de timeout con la señal externa opcional del llamador.
  const signals = [timeoutController.signal, signal].filter(Boolean) as AbortSignal[];
  const combinedSignal =
    signals.length === 1 ? signals[0] : anySignal(signals);

  const headers: Record<string, string> = {};
  let payload: BodyInit | undefined;

  if (formData) {
    payload = formData; // el navegador define el Content-Type con boundary.
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  try {
    const resp = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: payload,
      signal: combinedSignal,
    });

    if (!resp.ok) {
      const detalle = await extraerMensajeError(resp);
      throw new ApiError(
        detalle ?? "No se pudo completar la operación. Intenta nuevamente.",
        { status: resp.status, detalle },
      );
    }

    if (resp.status === 204) {
      return undefined as T;
    }

    const contentType = resp.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      return (await resp.json()) as T;
    }
    return (await resp.text()) as unknown as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;

    // AbortError por timeout propio o cancelación.
    if (error instanceof DOMException && error.name === "AbortError") {
      if (timeoutController.signal.aborted) {
        throw new ApiError(
          `La operación tardó demasiado (más de ${Math.round(timeoutMs / 1000)} segundos) y no pudo completarse. ` +
            "Tus datos no se han perdido; puedes intentar nuevamente.",
          { isTimeout: true },
        );
      }
      throw new ApiError("La operación fue cancelada.", { isTimeout: false });
    }

    // Fallo de red u otro error inesperado.
    throw new ApiError(
      "No se pudo conectar con el servidor. Revisa tu conexión e intenta nuevamente. " +
        "Tus datos no se han perdido.",
      { detalle: error instanceof Error ? error.message : undefined },
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

/** Equivalente mínimo de AbortSignal.any para entornos sin soporte nativo. */
function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  const onAbort = () => {
    controller.abort();
    for (const s of signals) s.removeEventListener("abort", onAbort);
  };
  for (const s of signals) {
    if (s.aborted) {
      onAbort();
      break;
    }
    s.addEventListener("abort", onAbort);
  }
  return controller.signal;
}
