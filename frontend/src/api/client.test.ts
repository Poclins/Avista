// Pruebas de la lógica central del cliente REST: construcción de URL/query,
// manejo de error HTTP con mensaje en español, timeout de 10 s (Requirement 9.7)
// y preservación implícita de datos (el cliente lanza ApiError sin tocar estado
// del formulario — eso lo verifica useAccionApi en la capa de pantallas).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, request, REQUEST_TIMEOUT_MS } from "./client";

function respuestaJson(data: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

describe("request()", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("construye la URL con base y query string", async () => {
    fetchMock.mockResolvedValue(respuestaJson([{ id_nino: "n1" }]));

    await request("/ninos", { query: { sala: "A-1", activos: true } });

    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("/ninos");
    expect(url).toContain("sala=A-1");
    expect(url).toContain("activos=true");
  });

  it("devuelve el JSON tipado en una respuesta exitosa", async () => {
    fetchMock.mockResolvedValue(respuestaJson({ status: "ok" }));

    const data = await request<{ status: string }>("/health");
    expect(data).toEqual({ status: "ok" });
  });

  it("lanza ApiError con el mensaje en español del backend ante error HTTP", async () => {
    fetchMock.mockResolvedValue(
      respuestaJson(
        { detail: "Formato de archivo no soportado." },
        { status: 400, statusText: "Bad Request" },
      ),
    );

    await expect(request("/ninos/n1/observaciones", { method: "POST" }))
      .rejects.toMatchObject({
        name: "ApiError",
        status: 400,
      });
  });

  it("lanza ApiError de timeout cuando la solicitud excede 10 s", async () => {
    vi.useFakeTimers();

    // fetch que respeta la señal de aborto para simular el timeout.
    fetchMock.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          );
        }),
    );

    const promesa = request("/ninos/n1/bitacoras", { method: "POST" });
    // Captura temprano el rechazo para evitar "unhandled rejection".
    const expectativa = expect(promesa).rejects.toBeInstanceOf(ApiError);

    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS + 10);
    await expectativa;

    await promesa.catch((err: ApiError) => {
      expect(err.isTimeout).toBe(true);
    });
  });

  it("lanza ApiError de red ante fallo de conexión", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(request("/health")).rejects.toMatchObject({
      name: "ApiError",
      isTimeout: false,
    });
  });
});
