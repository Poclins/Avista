"""Nombres ficticios deterministas para los niños/as sintéticos E-1.

No representan personas reales. El nombre completo es único para cada id_nino
oficial y puede regenerarse de forma estable en cualquier base local o cloud.
"""

from __future__ import annotations

import hashlib
import re

_NOMBRES = (
    "Amalia", "Benjamín", "Catalina", "Diego", "Emilia", "Facundo",
    "Gabriela", "Hugo", "Isidora", "Joaquín", "Josefa", "Lucas",
    "Maite", "Nicolás", "Olivia", "Pedro", "Renata", "Simón",
    "Trinidad", "Vicente", "Amanda", "Bruno", "Clara", "Domingo",
    "Elena", "Felipe", "Florencia", "Gaspar", "Ignacia", "Matías",
)

_APELLIDOS = (
    "Aguilera", "Araya", "Bustamante", "Cáceres", "Contreras", "Delgado",
    "Espinoza", "Fernández", "Fuentes", "Gallardo", "González", "Herrera",
    "Jara", "Leiva", "Mardones", "Medina", "Molina", "Muñoz",
    "Navarro", "Núñez", "Orellana", "Paredes", "Pizarro", "Ramírez",
    "Riquelme", "Rojas", "Salazar", "Sepúlveda", "Soto", "Valenzuela",
)


def _indice(id_nino: str) -> int:
    coincidencia = re.search(r"(\d+)$", id_nino)
    if coincidencia:
        return max(int(coincidencia.group(1)) - 1, 0)
    return int(hashlib.sha256(id_nino.encode("utf-8")).hexdigest(), 16)


def nombres_para_nino(id_nino: str) -> tuple[str, str, str]:
    """Devuelve nombre y dos apellidos distintos; el nombre completo es único."""
    indice = _indice(id_nino)
    nombre = _NOMBRES[indice % len(_NOMBRES)]
    apellido_paterno = _APELLIDOS[(indice // len(_NOMBRES)) % len(_APELLIDOS)]
    indice_materno = (indice * 7 + 11) % len(_APELLIDOS)
    apellido_materno = _APELLIDOS[indice_materno]
    if apellido_materno == apellido_paterno:
        apellido_materno = _APELLIDOS[(indice_materno + 1) % len(_APELLIDOS)]
    return nombre, apellido_paterno, apellido_materno


def nombre_completo(
    id_nino: str,
    nombre: str | None = None,
    apellido_paterno: str | None = None,
    apellido_materno: str | None = None,
) -> str:
    """Nombre completo almacenado o, si falta, su valor sintético estable."""
    if nombre and apellido_paterno and apellido_materno:
        return f"{nombre} {apellido_paterno} {apellido_materno}"
    return " ".join(nombres_para_nino(id_nino))


__all__ = ["nombres_para_nino", "nombre_completo"]
