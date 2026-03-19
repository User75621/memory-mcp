"""Validadores reutilizables para entradas del servidor."""

from __future__ import annotations

import re
from uuid import UUID

VALID_SEVERITIES = {"low", "medium", "high", "critical"}
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def validate_project_id(project_id: str) -> str:
    """Valida que el identificador del proyecto sea un UUID.

    Args:
        project_id: Identificador recibido desde una interfaz cliente.

    Returns:
        El mismo UUID en formato string si es valido.

    Raises:
        ValueError: Si el valor no representa un UUID valido.
    """
    if not isinstance(project_id, str) or not UUID_PATTERN.match(project_id):
        raise ValueError("project_id must be a valid UUID string")

    UUID(project_id)
    return project_id


def validate_severity(severity: str) -> str:
    """Valida niveles de severidad admitidos por el sistema.

    Args:
        severity: Nivel de severidad enviado por la herramienta.

    Returns:
        El nivel normalizado en minusculas.

    Raises:
        ValueError: Si el nivel no se encuentra en la lista soportada.
    """
    normalized = str(severity).strip().lower()
    if normalized not in VALID_SEVERITIES:
        raise ValueError(
            "severity must be one of: low, medium, high, critical"
        )
    return normalized
