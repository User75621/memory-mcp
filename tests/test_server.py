"""Tests for MCP server tools and routing."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from src import server as server_module
from src.interface_detector import detect_interface, get_model_for_interface
from src.utils.db import set_owner_context
from src.utils.validators import validate_project_id, validate_severity


PROJECT_ID = "123e4567-e89b-12d3-a456-426614174000"


class FakeQuery:
    """Tiny PostgREST-like query builder for tests."""

    def __init__(self, table_name: str, store: dict[str, list[dict[str, Any]]]) -> None:
        self.table_name = table_name
        self.store = store
        self.mode = "select"
        self.filters: dict[str, Any] = {}
        self.payload: dict[str, Any] | None = None

    def select(self, _columns: str) -> "FakeQuery":
        return self

    def eq(self, key: str, value: Any) -> "FakeQuery":
        self.filters[key] = value
        return self

    def upsert(self, payload: dict[str, Any]) -> "FakeQuery":
        self.mode = "upsert"
        self.payload = payload
        return self

    def execute(self) -> SimpleNamespace:
        if self.mode == "upsert" and self.payload is not None:
            target = self.store.setdefault(self.table_name, [])
            payload = dict(self.payload)
            existing_index = next(
                (
                    index
                    for index, item in enumerate(target)
                    if payload.get("id") and item.get("id") == payload.get("id")
                ),
                None,
            )
            if existing_index is None:
                if self.table_name == "session_state" and "id" not in payload:
                    payload["id"] = "state-1"
                elif "id" not in payload:
                    payload["id"] = f"{self.table_name}-{len(target) + 1}"
                target.append(payload)
            else:
                target[existing_index].update(payload)
                payload = target[existing_index]
            return SimpleNamespace(data=[payload])

        rows = self.store.get(self.table_name, [])
        result = []
        for row in rows:
            if all(row.get(key) == value for key, value in self.filters.items()):
                result.append(dict(row))
        return SimpleNamespace(data=result)


class FakeClient:
    """Supabase client replacement with table access."""

    def __init__(self) -> None:
        self.options = SimpleNamespace(headers={})
        self.store = {
            "projects": [
                {
                    "id": PROJECT_ID,
                    "owner_id": "demo-owner",
                    "name": "Demo Project",
                    "slug": "demo-project",
                }
            ],
            "decisions": [],
            "tasks": [],
            "preferences": [],
            "sessions": [],
            "warnings": [],
            "session_state": [],
            "interface_analytics": [
                {
                    "project_id": PROJECT_ID,
                    "interface": "native",
                    "total_sessions": 1,
                    "active_sessions": 1,
                }
            ],
        }

    def table(self, table_name: str) -> FakeQuery:
        return FakeQuery(table_name, self.store)


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    """Provide a fake client and patch server dependencies."""
    client = FakeClient()
    monkeypatch.setattr(server_module, "get_supabase_client", lambda: client)
    monkeypatch.setattr(server_module, "set_owner_context", lambda c, _owner: c)
    monkeypatch.setattr(server_module, "detect_interface", lambda: "native")
    return client


@pytest.mark.asyncio
async def test_list_tools_exposes_nine_tools() -> None:
    """Asegura que las nueve herramientas minimas esten registradas."""
    tools = await server_module.server.list_registered_tools()
    assert len(tools) == 9


def test_load_unified_context(fake_client: FakeClient) -> None:
    """Carga el contexto consolidado con metadatos utiles."""
    result = server_module.load_unified_context(PROJECT_ID, interface="native")
    assert result["project"]["id"] == PROJECT_ID
    assert result["metadata"]["recommended_model"] == "gemini-pro"


def test_save_cross_interface_decision(fake_client: FakeClient) -> None:
    """Guarda decisiones compartidas."""
    result = server_module.save_cross_interface_decision(
        PROJECT_ID,
        summary="Use shared memory",
        details="Persist context for every interface.",
        interface="qwen-code",
    )
    assert result["status"] == "ok"
    assert result["decision"]["interface"] == "qwen-code"


def test_update_task_status(fake_client: FakeClient) -> None:
    """Actualiza estado de tareas."""
    result = server_module.update_task_status("task-1", PROJECT_ID, "completed")
    assert result["task"]["status"] == "completed"


def test_create_and_end_session(fake_client: FakeClient) -> None:
    """Permite abrir y cerrar sesiones."""
    created = server_module.create_session(PROJECT_ID, interface="codex")
    assert created["session"]["status"] == "active"
    ended = server_module.end_session(created["session"]["id"])
    assert ended["session"]["status"] == "ended"


def test_add_warning_and_get_active_warnings(fake_client: FakeClient) -> None:
    """Registra advertencias y luego las consulta."""
    server_module.add_warning(PROJECT_ID, "Token usage is high", "high")
    result = server_module.get_active_warnings(PROJECT_ID)
    assert result["count"] == 1
    assert result["warnings"][0]["severity"] == "high"


def test_sync_session_state(fake_client: FakeClient) -> None:
    """Sincroniza estado serializable de una sesion."""
    result = server_module.sync_session_state(
        "session-1", PROJECT_ID, {"cursor": 2, "active_file": "src/server.py"}
    )
    assert result["session_state"]["state"]["active_file"] == "src/server.py"


def test_get_interface_analytics(fake_client: FakeClient) -> None:
    """Lee la vista agregada de interfaces."""
    result = server_module.get_interface_analytics(PROJECT_ID)
    assert result["interfaces"] == 1


@pytest.mark.asyncio
async def test_call_tool_router(fake_client: FakeClient) -> None:
    """Ejecuta una tool via router asincrono."""
    result = await server_module.server.call_registered_tool(
        "get_interface_analytics", {"project_id": PROJECT_ID}
    )
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_call_tool_unknown_raises() -> None:
    """Protege contra tools inexistentes."""
    with pytest.raises(ValueError):
        await server_module.server.call_registered_tool("unknown_tool", {})


def test_interface_detection_and_model_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Detecta interfaces conocidas y resuelve su modelo."""
    monkeypatch.setenv("PROJECT_MEMORY_INTERFACE", "opencode")
    assert detect_interface() == "opencode"
    monkeypatch.delenv("PROJECT_MEMORY_INTERFACE")
    monkeypatch.setenv("CLAUDECODE", "1")
    assert detect_interface() == "claude-code"
    assert get_model_for_interface("codex") == "gpt-4.1"
    assert get_model_for_interface("claude-code") == "claude-3-7-sonnet"


def test_set_owner_context_and_validators() -> None:
    """Aplica metadata de owner y valida entradas clave."""
    client = FakeClient()
    updated = set_owner_context(client, "owner-123")
    assert updated.options.headers["X-Owner-Context"] == "owner-123"
    assert validate_project_id(PROJECT_ID) == PROJECT_ID
    assert validate_severity("CRITICAL") == "critical"
