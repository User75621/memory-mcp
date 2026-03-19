"""Servidor MCP para memoria persistente multi-interfaz con Supabase."""

from __future__ import annotations

import asyncio
import inspect
import os
from typing import Any, Awaitable, Callable

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


class MemoryMCP:
    """Shim ligero compatible con decoradores MCP para este proyecto."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._list_handler: Handler | None = None
        self._call_handler: Handler | None = None

    def list_tools(self) -> Callable[[Handler], Handler]:
        """Registra la funcion que expone herramientas disponibles."""

        def decorator(func: Handler) -> Handler:
            self._list_handler = func
            return func

        return decorator

    def call_tool(self) -> Callable[[Handler], Handler]:
        """Registra la funcion que enruta la ejecucion de tools."""

        def decorator(func: Handler) -> Handler:
            self._call_handler = func
            return func

        return decorator

    async def list_registered_tools(self) -> Any:
        """Ejecuta el handler decorado de listado."""
        if self._list_handler is None:
            raise RuntimeError("No list_tools handler registered")
        result = self._list_handler()
        if inspect.isawaitable(result):
            return await result
        return result

    async def call_registered_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> Any:
        """Ejecuta el handler decorado de llamada de herramientas."""
        if self._call_handler is None:
            raise RuntimeError("No call_tool handler registered")
        result = self._call_handler(tool_name, arguments or {})
        if inspect.isawaitable(result):
            return await result
        return result

    def run(self) -> None:
        """Inicia un loop basico para compatibilidad con entry points."""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.list_registered_tools())
        finally:
            loop.close()


server = MemoryMCP("Project Memory MCP")
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


@server.list_tools()
async def list_tools() -> list[dict[str, Any]]:
    """Expone las herramientas soportadas por el servidor.

    Returns:
        Lista descriptiva de tools MCP disponibles.
    """
    return TOOL_SCHEMAS


@server.call_tool()
async def call_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Enruta llamadas de herramientas a la implementacion correspondiente.

    Args:
        tool_name: Nombre de la herramienta solicitada.
        arguments: Argumentos serializados de la llamada.

    Returns:
        Resultado serializable para MCP.

    Raises:
        ValueError: Si el nombre de herramienta no existe.
    """
    handlers: dict[str, Handler] = {
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
    if tool_name not in handlers:
        raise ValueError(f"Unknown tool: {tool_name}")

    result = handlers[tool_name](**arguments)
    if isinstance(result, Awaitable):
        return await result
    return result


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
        project_rows = _table_select(
            client, "projects", {"id": validated_project_id}
        )
        context = {
            "project": project_rows[0] if project_rows else {},
            "decisions": _table_select(
                client, "decisions", {"project_id": validated_project_id}
            ),
            "tasks": _table_select(client, "tasks", {"project_id": validated_project_id}),
            "preferences": _table_select(
                client, "preferences", {"project_id": validated_project_id}
            ),
            "warnings": _table_select(
                client, "warnings", {"project_id": validated_project_id, "is_active": True}
            ),
            "sessions": _table_select(
                client, "sessions", {"project_id": validated_project_id}
            ),
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


def update_task_status(
    task_id: str,
    project_id: str,
    status: str,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Actualiza el estado de una tarea almacenada.

    Args:
        task_id: Identificador de la tarea.
        project_id: UUID del proyecto asociado.
        status: Nuevo estado semantico.
        owner_id: Propietario para RLS.

    Returns:
        Resultado de la operacion de escritura.
    """
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


def create_session(
    project_id: str,
    interface: str | None = None,
    model_name: str | None = None,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Crea una sesion activa para una interfaz especifica.

    Args:
        project_id: UUID del proyecto.
        interface: Interfaz iniciadora.
        model_name: Modelo asociado a la sesion.
        owner_id: Propietario del contexto.

    Returns:
        Sesion persistida o error.
    """
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


def end_session(session_id: str, owner_id: str | None = None) -> dict[str, Any]:
    """Marca una sesion como finalizada.

    Args:
        session_id: Identificador de la sesion.
        owner_id: Propietario del contexto.

    Returns:
        Resultado de la actualizacion.
    """
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


def add_warning(
    project_id: str,
    message: str,
    severity: str,
    owner_id: str | None = None,
    interface: str | None = None,
) -> dict[str, Any]:
    """Registra una advertencia activa en la memoria persistente.

    Args:
        project_id: UUID del proyecto.
        message: Mensaje de advertencia.
        severity: low, medium, high o critical.
        owner_id: Propietario para RLS.
        interface: Interfaz que genera la advertencia.

    Returns:
        Advertencia persistida o error.
    """
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


def get_active_warnings(
    project_id: str,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Obtiene todas las advertencias activas de un proyecto.

    Args:
        project_id: UUID del proyecto.
        owner_id: Propietario para RLS.

    Returns:
        Lista de advertencias activas y conteo.
    """
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


def sync_session_state(
    session_id: str,
    project_id: str,
    state: dict[str, Any],
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Sincroniza el estado de una sesion entre interfaces.

    Args:
        session_id: Identificador de la sesion.
        project_id: UUID del proyecto.
        state: Estado serializable compartido.
        owner_id: Propietario para RLS.

    Returns:
        Estado persistido o error estructurado.
    """
    client = _client(owner_id)
    payload = {
        "session_id": session_id,
        "project_id": validate_project_id(project_id),
        "state": state,
        "owner_id": owner_id or os.getenv("OWNER_ID", "default-owner"),
    }
    try:
        stored = _table_upsert(client, "session_state", payload)
        return {"status": "ok", "session_state": stored[0] if isinstance(stored, list) else stored}
    except Exception as exc:
        return {"error": str(exc), "tool": "sync_session_state"}


def get_interface_analytics(
    project_id: str | None = None,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Lee analitica agregada por interfaz desde la vista SQL.

    Args:
        project_id: UUID opcional para filtrar resultados.
        owner_id: Propietario para RLS.

    Returns:
        Resumen de interfaces y uso de sesiones.
    """
    client = _client(owner_id)
    try:
        filters: dict[str, Any] = {}
        if project_id:
            filters["project_id"] = validate_project_id(project_id)
        analytics = _table_select(client, "interface_analytics", filters)
        return {"status": "ok", "analytics": analytics, "interfaces": len(analytics)}
    except Exception as exc:
        return {"error": str(exc), "tool": "get_interface_analytics"}


def main() -> None:
    """Punto de entrada del servidor para ejecucion local o MCP."""
    server.run()


if __name__ == "__main__":
    main()
