"""Formateadores de salida para contexto y decisiones."""

from __future__ import annotations

from typing import Any


def format_context(context: dict[str, Any]) -> dict[str, Any]:
    """Prepara una respuesta uniforme de contexto para clientes MCP.

    Args:
        context: Diccionario con datos agregados del proyecto.

    Returns:
        Un diccionario con claves estables y listas ordenadas.
    """
    formatted = {
        "project": context.get("project") or {},
        "workspace": context.get("workspace") or {},
        "decisions": context.get("decisions") or [],
        "tasks": context.get("tasks") or [],
        "preferences": context.get("preferences") or [],
        "warnings": context.get("warnings") or [],
        "sessions": context.get("sessions") or [],
        "checkpoints": context.get("checkpoints") or [],
        "file_memory": context.get("file_memory") or [],
        "prompt_patterns": context.get("prompt_patterns") or [],
        "timeline": context.get("timeline") or [],
        "semantic_matches": context.get("semantic_matches") or [],
        "metadata": context.get("metadata") or {},
    }
    formatted["counts"] = {
        "decisions": len(formatted["decisions"]),
        "tasks": len(formatted["tasks"]),
        "warnings": len(formatted["warnings"]),
        "sessions": len(formatted["sessions"]),
        "checkpoints": len(formatted["checkpoints"]),
        "file_memory": len(formatted["file_memory"]),
        "prompt_patterns": len(formatted["prompt_patterns"]),
        "timeline": len(formatted["timeline"]),
    }
    return formatted


def format_decision(decision: dict[str, Any]) -> dict[str, Any]:
    """Normaliza una decision para respuestas consistentes.

    Args:
        decision: Registro de decision generado por cualquier interfaz.

    Returns:
        El payload listo para persistencia o presentacion.
    """
    return {
        "id": decision.get("id"),
        "project_id": decision.get("project_id"),
        "interface": decision.get("interface", "unknown"),
        "summary": str(decision.get("summary", "")).strip(),
        "details": str(decision.get("details", "")).strip(),
        "decision_type": decision.get("decision_type", "general"),
        "created_at": decision.get("created_at"),
        "metadata": decision.get("metadata") or {},
    }
