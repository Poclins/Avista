"""Extrae texto de los PDFs de mockups de Figma (tarea 14.1).

Intenta usar pypdf; si no está instalado, informa y sale sin error fatal.
Uso: python scripts/extract_mockups.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

MOCKUPS = Path(__file__).resolve().parent.parent / "mockups"
OUT = Path(__file__).resolve().parent / "mockups_extract.txt"


def main() -> int:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError:
        OUT.write_text("NO_PYPDF\n", encoding="utf-8")
        return 0

    buf = io.StringIO()
    pdfs = sorted(MOCKUPS.glob("*.pdf"))
    for pdf in pdfs:
        buf.write("=" * 70 + "\n")
        buf.write(f"ARCHIVO: {pdf.name}\n")
        buf.write("=" * 70 + "\n")
        try:
            reader = PdfReader(str(pdf))
        except Exception as exc:  # noqa: BLE001
            buf.write(f"  [ERROR al leer: {exc}]\n")
            continue
        buf.write(f"  paginas: {len(reader.pages)}\n")
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:  # noqa: BLE001
                text = f"[ERROR extract_text: {exc}]"
            text = text.strip()
            buf.write(f"  --- pagina {i} ---\n")
            if text:
                buf.write(text + "\n")
            else:
                buf.write("  [sin texto extraible - probablemente imagen rasterizada]\n")
    OUT.write_text(buf.getvalue(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
