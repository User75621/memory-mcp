"""Servidor MCP para memoria persistente multi-interfaz con Supabase."""

from __future__ import annotations

import os
from typing import Any, Callable

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:  # pragma: no cover - fallback for local test envs
    class FastMCP:  # type: ignore[no-redef]
        """Fallback minimo cuando la libreria mcp no esta instalada."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self._tools: dict[str, Callable[..., Any]] = {}

        def tool(
            self,
            name: str | None = None,
            description: str | None = None,
            **_kwargs: Any,
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                self._tools[name or func.__name__] = func
                setattr(func, "_tool_description", description)
                return func

            return decorator

        def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
            del transport, mount_path
            return None

from .interface_detector import detect_interface, get_model_for_interface
from .model_router import ModelRouter
from .optimizer import ContextOptimizer
from .utils import (
    format_context,
    format_decision,
    get_supabase_client,
    set_owner_context,
    validate_project_id,
    validate_severity,
)

Handler = Callable[..., Any]

server = FastMCP(
    name="Project Memory MCP",
    instructions=(
        "Persistent project memory MCP server backed by Supabase. "
        "Use tools to load shared context, persist decisions, sync sessions, "
        "track warnings, and query analytics across AI clients."
    ),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
)
optimizer = ContextOptimizer()
router = ModelRouter()

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "load_unified_context",
        "description": "Carga contexto persistente multi-interfaz de un proyecto.",
    },
    {
        "name": "save_cross_interface_decision",
        "description": "Guarda decisiones compartidas entre interfaces.",
    },
    {
        "name": "update_task_status",
        "description": "Actualiza el estado de una tarea persistida.",
    },
    {"name": "create_session", "description": "Crea una nueva sesion de memoria."},
    {"name": "end_session", "description": "Marca una sesion como finalizada."},
    {"name": "add_warning", "description": "Registra advertencias persistentes."},
    {
        "name": "get_active_warnings",
        "description": "Obtiene advertencias activas de un proyecto.",
    },
    {
        "name": "sync_session_state",
        "description": "Sincroniza el estado actual de una sesion activa.",
    },
    {
        "name": "get_interface_analytics",
        "description": "Resume uso y rendimiento por interfaz.",
    },
]


def _client(owner_id: str | None = None) -> Any:
    """Crea cliente y aplica contexto de propietario si existe.

    Args:
        owner_id: Identificador de usuario o workspace.

    Returns:
        Cliente de Supabase listo para consultas.
    """
    client = get_supabase_client()
    resolved_owner = owner_id or os.getenv("OWNER_ID", "default-owner")
    return set_owner_context(client, resolved_owner)


def _extract_data(response: Any) -> Any:
    """Normaliza la forma de leer respuestas del cliente Supabase."""
    return getattr(response, "data", response)


def _table_select(client: Any, table: str, filters: dict[str, Any] | None = None) -> Any:
    """Consulta una tabla con filtros simples de igualdad."""
    query = client.table(table).select("*")
    for key, value in (filters or {}).items():
        query = query.eq(key, value)
    return _extract_data(query.execute())


def _table_upsert(client: Any, table: str, payload: dict[str, Any]) -> Any:
    """Inserta o actualiza un registro en Supabase."""
    return _extract_data(client.table(table).upsert(payload).execute())


@server.tool(
    name="load_unified_context",
    description="Carga contexto persistente multi-interfaz de un proyecto.",
)
def load_unified_context(
    project_id: str,
    interface: str | None = None,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Carga el contexto consolidado y lo optimiza para una interfaz.

    Args:
        project_id: UUID del proyecto persistido.
        interface: Interfaz solicitante; si falta se detecta automaticamente.
        owner_id: Propietario para RLS y trazabilidad.

    Returns:
        Contexto unificado, optimizado y enriquecido con metadata.
    """
    validated_project_id = validate_project_id(project_id)
    target_interface = interface or detect_interface()
    client = _client(owner_id)

    try:
        project_rows = _table_select(client, "projects", {"id": validated_project_id})
        context = {
            "project": project_rows[0] if project_rows else {},
            "decisions": _table_select(client, "decisions", {"project_id": validated_project_id}),
            "tasks": _table_select(client, "tasks", {"project_id": validated_project_id}),
            "preferences": _table_select(client, "preferences", {"project_id": validated_project_id}),
            "warnings": _table_select(
                client,
                "warnings",
                {"project_id": validated_project_id, "is_active": True},
            ),
            "sessions": _table_select(client, "sessions", {"project_id": validated_project_id}),
            "metadata": {
                "interface": target_interface,
                "recommended_model": get_model_for_interface(target_interface),
            },
        }
        formatted = format_context(context)
        optimized = optimizer.optimize_for_interface(formatted, target_interface)
        estimated_tokens = optimizer.estimate_tokens(optimized)
        return router.optimize_context_for_model(
            optimized["metadata"]["recommended_model"],
            optimized,
            estimated_tokens,
        )
    except Exception as exc:
        return {"error": str(exc), "tool": "load_unified_context"}


@server.tool(
    name="save_cross_interface_decision",
    description="Guarda decisiones compartidas entre interfaces.",
)
def save_cross_interface_decision(
    project_id: str,
    summary: str,
    details: str,
    interface: str | None = None,
    decision_type: str = "general",
    owner_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persiste una decision reusable por varias interfaces.

    Args:
        project_id: UUID del proyecto.
        summary: Resumen corto de la decision.
        details: Descripcion extendida o rationale.
        interface: Interfaz origen.
        decision_type: Categoria de la decision.
        owner_id: Propietario para RLS.
        metadata: Datos auxiliares.

    Returns:
        Registro persistido o un error estructurado.
    """
    client = _client(owner_id)
    payload = format_decision(
        {
            "project_id": validate_project_id(project_id),
            "interface": interface or detect_interface(),
            "summary": summary,
            "details": details,
            "decision_type": decision_type,
            "metadata": metadata or {},
            "owner_id": owner_id or os.getenv("OWNER_ID", "default-owner"),
        }
    )
    payload["owner_id"] = owner_id or os.getenv("OWNER_ID", "default-owner")

    try:
        stored = _table_upsert(client, "decisions", payload)
        return {"status": "ok", "decision": stored[0] if isinstance(stored, list) else stored}
    except Exception as exc:
        return {"error": str(exc), "tool": "save_cross_interface_decision"}


@server.tool(
    name="update_task_status",
    description="Actualiza el estado de una tarea persistida.",
)
def update_task_status(
    task_id: str,
    project_id: str,
    status: str,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Actualiza el estado de una tarea almacenada."""
    client = _client(owner_id)
    payload = {
        "id": task_id,
        "project_id": validate_project_id(project_id),
        "status": status.strip().lower(),
        "owner_id": owner_id or os.getenv("OWNER_ID", "default-owner"),
    }
    try:
        stored = _table_upsert(client, "tasks", payload)
        return {"status": "ok", "task": stored[0] if isinstance(stored, list) else stored}
    except Exception as exc:
        return {"error": str(exc), "tool": "update_task_status"}


@server.tool(name="create_session", description="Crea una nueva sesion de memoria.")
def create_session(
    project_id: str,
    interface: str | None = None,
    model_name: str | None = None,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Crea una sesion activa para una interfaz especifica."""
    client = _client(owner_id)
    interface_name = interface or detect_interface()
    model = model_name or router.recommend_model("coding")
    payload = {
        "project_id": validate_project_id(project_id),
        "interface": interface_name,
        "model_name": model,
        "status": "active",
        "owner_id": owner_id or os.getenv("OWNER_ID", "default-owner"),
    }
    try:
        stored = _table_upsert(client, "sessions", payload)
        return {"status": "ok", "session": stored[0] if isinstance(stored, list) else stored}
    except Exception as exc:
        return {"error": str(exc), "tool": "create_session"}


@server.tool(name="end_session", description="Marca una sesion como finalizada.")
def end_session(session_id: str, owner_id: str | None = None) -> dict[str, Any]:
    """Marca una sesion como finalizada."""
    client = _client(owner_id)
    payload = {
        "id": session_id,
        "status": "ended",
        "owner_id": owner_id or os.getenv("OWNER_ID", "default-owner"),
    }
    try:
        stored = _table_upsert(client, "sessions", payload)
        return {"status": "ok", "session": stored[0] if isinstance(stored, list) else stored}
    except Exception as exc:
        return {"error": str(exc), "tool": "end_session"}


@server.tool(name="add_warning", description="Registra advertencias persistentes.")
def add_warning(
    project_id: str,
    message: str,
    severity: str,
    owner_id: str | None = None,
    interface: str | None = None,
) -> dict[str, Any]:
    """Registra una advertencia activa en la memoria persistente."""
    client = _client(owner_id)
    payload = {
        "project_id": validate_project_id(project_id),
        "message": message.strip(),
        "severity": validate_severity(severity),
        "interface": interface or detect_interface(),
        "is_active": True,
        "owner_id": owner_id or os.getenv("OWNER_ID", "default-owner"),
    }
    try:
        stored = _table_upsert(client, "warnings", payload)
        return {"status": "ok", "warning": stored[0] if isinstance(stored, list) else stored}
    except Exception as exc:
        return {"error": str(exc), "tool": "add_warning"}


@server.tool(
    name="get_active_warnings",
    description="Obtiene advertencias activas de un proyecto.",
)
def get_active_warnings(
    project_id: str,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Obtiene todas las advertencias activas de un proyecto."""
    client = _client(owner_id)
    try:
        warnings = _table_select(
            client,
            "warnings",
            {"project_id": validate_project_id(project_id), "is_active": True},
        )
        return {"status": "ok", "warnings": warnings, "count": len(warnings)}
    except Exception as exc:
        return {"error": str(exc), "tool": "get_active_warnings"}


@server.tool(
    name="sync_session_state",
    description="Sincroniza el estado actual de una sesion activa.",
)
def sync_session_state(
    session_id: str,
    project_id: str,
    state: dict[str, Any],
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Sincroniza el estado de una sesion entre interfaces."""
    client = _client(owner_id)
    payload = {
        "session_id": session_id,
        "project_id": validate_project_id(project_id),
        "state": state,
        "owner_id": owner_id or os.getenv("OWNER_ID", "default-owner"),
    }
    try:
        stored = _table_upsert(client, "session_state", payload)
        return {
            "status": "ok",
            "session_state": stored[0] if isinstance(stored, list) else stored,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "sync_session_state"}


@server.tool(
    name="get_interface_analytics",
    description="Resume uso y rendimiento por interfaz.",
)
def get_interface_analytics(
    project_id: str | None = None,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Lee analitica agregada por interfaz desde la vista SQL."""
    client = _client(owner_id)
    try:
        filters: dict[str, Any] = {}
        if project_id:
            filters["project_id"] = validate_project_id(project_id)
        analytics = _table_select(client, "interface_analytics", filters)
        return {"status": "ok", "analytics": analytics, "interfaces": len(analytics)}
    except Exception as exc:
        return {"error": str(exc), "tool": "get_interface_analytics"}


TOOL_HANDLERS: dict[str, Handler] = {
    "load_unified_context": load_unified_context,
    "save_cross_interface_decision": save_cross_interface_decision,
    "update_task_status": update_task_status,
    "create_session": create_session,
    "end_session": end_session,
    "add_warning": add_warning,
    "get_active_warnings": get_active_warnings,
    "sync_session_state": sync_session_state,
    "get_interface_analytics": get_interface_analytics,
}


async def list_registered_tools() -> list[dict[str, Any]]:
    """Expone las herramientas soportadas por el servidor para tests locales."""
    return TOOL_SCHEMAS


async def call_registered_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta una herramienta por nombre para tests locales."""
    if tool_name not in TOOL_HANDLERS:
        raise ValueError(f"Unknown tool: {tool_name}")
    return TOOL_HANDLERS[tool_name](**(arguments or {}))


setattr(server, "list_registered_tools", list_registered_tools)
setattr(server, "call_registered_tool", call_registered_tool)


def main() -> None:
    """Punto de entrada del servidor para ejecucion local o MCP stdio."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
