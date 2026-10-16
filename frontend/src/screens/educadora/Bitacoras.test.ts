import { describe, expect, it } from "vitest";
import { numerarReferenciasObservaciones } from "./Bitacoras";

describe("numerarReferenciasObservaciones", () => {
  it("reemplaza UUID repetido por el mismo índice", () => {
    const id = "27df4d97552747cf9a1c7ddd052913d7";
    const texto = `Primera referencia (observación ${id}). Repite ${id}.`;
    expect(numerarReferenciasObservaciones(texto)).toBe(
      "Primera referencia (Observación 1). Repite Observación 1.",
    );
  });

  it("numera identificadores diferentes por orden de aparición", () => {
    const texto = "OBS-0001 respalda algo y OBS-0002 aporta otra evidencia.";
    expect(numerarReferenciasObservaciones(texto)).toBe(
      "Observación 1 respalda algo y Observación 2 aporta otra evidencia.",
    );
  });
});
