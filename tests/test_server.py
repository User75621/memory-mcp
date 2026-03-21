"""Tests for MCP server tools and automatic project memory flows."""

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

    def insert(self, payload: dict[str, Any]) -> "FakeQuery":
        self.mode = "insert"
        self.payload = payload
        return self

    def execute(self) -> SimpleNamespace:
        if self.mode in {"upsert", "insert"} and self.payload is not None:
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
            if existing_index is None and payload.get("id") is None:
                natural_keys = [
                    ("project_id", "slug"),
                    ("project_id", "file_path"),
                    ("project_id", "title"),
                    ("project_id", "preference_key"),
                    ("owner_id", "slug"),
                    ("session_id",),
                    ("project_id", "source_type", "source_id"),
                ]
                for keys in natural_keys:
                    if all(key in payload for key in keys):
                        existing_index = next(
                            (
                                index
                                for index, item in enumerate(target)
                                if all(item.get(key) == payload.get(key) for key in keys)
                            ),
                            None,
                        )
                        if existing_index is not None:
                            break
            if existing_index is None:
                payload.setdefault("id", f"{self.table_name}-{len(target) + 1}")
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


class FakeRPC:
    """Simple RPC response wrapper."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self.payload)


class FakeClient:
    """Supabase client replacement with table access and RPC."""

    def __init__(self) -> None:
        self.options = SimpleNamespace(headers={})
        self.store = {
            "workspaces": [
                {
                    "id": "workspace-1",
                    "owner_id": "demo-owner",
                    "slug": "demo-owner",
                    "name": "Demo Owner",
                }
            ],
            "projects": [
                {
                    "id": PROJECT_ID,
                    "owner_id": "demo-owner",
                    "workspace_id": "workspace-1",
                    "name": "Demo Project",
                    "slug": "demo-project",
                    "repo_path": "C:/repo/demo-project",
                    "repo_remote": "https://github.com/demo/demo-project.git",
                    "repo_branch": "main",
                    "repo_last_commit": "abc123",
                    "repo_status": {"changed_files": []},
                    "metadata": {},
                }
            ],
            "decisions": [],
            "tasks": [],
            "preferences": [],
            "sessions": [],
            "warnings": [],
            "session_state": [],
            "checkpoints": [],
            "file_memory": [],
            "file_relations": [],
            "prompt_patterns": [],
            "memory_documents": [],
            "timeline_events": [],
            "retention_policies": [],
            "interface_logs": [],
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

    def rpc(self, function_name: str, params: dict[str, Any]) -> FakeRPC:
        if function_name == "match_memory_documents":
            rows = self.store.get("memory_documents", [])
            filtered = [
                row
                for row in rows
                if row.get("project_id") == params.get("filter_project_id")
                and row.get("owner_id") == params.get("filter_owner_id")
            ]
            enriched = [dict(row, similarity=0.99) for row in filtered[: params.get("match_count", 5)]]
            return FakeRPC(enriched)
        return FakeRPC([])


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    """Provide a fake client and patch server dependencies."""
    client = FakeClient()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(server_module, "get_supabase_client", lambda: client)
    monkeypatch.setattr(server_module, "set_owner_context", lambda c, _owner: c)
    monkeypatch.setattr(server_module, "detect_interface", lambda: "native")
    monkeypatch.setattr(
        server_module,
        "detect_repo_context",
        lambda _path=None: SimpleNamespace(
            to_dict=lambda: {
                "repo_root": "C:/repo/demo-project",
                "repo_name": "Demo Project",
                "repo_slug": "demo-project",
                "repo_remote": "https://github.com/demo/demo-project.git",
                "repo_branch": "main",
                "repo_commit": "abc123",
                "repo_status": [],
                "repo_provider": "github",
            }
        ),
    )
    return client


@pytest.mark.asyncio
async def test_list_tools_exposes_extended_toolset() -> None:
    """Asegura que el servidor expone las nuevas tools de memoria."""
    tools = await getattr(server_module.server, "list_registered_tools")()
    names = {tool["name"] for tool in tools}
    assert len(tools) >= 20
    assert {"resolve_project", "resume_project", "search_semantic_memory"}.issubset(names)


def test_resolve_project_auto_uses_repo_context(fake_client: FakeClient) -> None:
    """Resuelve proyectos por slug de repo sin exigir project_id."""
    result = server_module.resolve_project(owner_id="demo-owner")
    assert result["project_id"] == PROJECT_ID
    assert result["repo_root"] == "C:/repo/demo-project"


def test_create_project_auto_creates_when_missing(fake_client: FakeClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Crea proyectos automaticamente cuando el repo no existe en memoria."""
    monkeypatch.setattr(
        server_module,
        "detect_repo_context",
        lambda _path=None: SimpleNamespace(
            to_dict=lambda: {
                "repo_root": "C:/repo/new-app",
                "repo_name": "New App",
                "repo_slug": "new-app",
                "repo_remote": "https://github.com/demo/new-app.git",
                "repo_branch": "main",
                "repo_commit": "def456",
                "repo_status": [],
                "repo_provider": "github",
            }
        ),
    )
    result = server_module.create_project(owner_id="demo-owner")
    assert result["project_slug"] == "new-app"


def test_load_unified_context_without_project_id(fake_client: FakeClient) -> None:
    """Carga contexto usando resolucion automatica del proyecto."""
    result = server_module.load_unified_context(owner_id="demo-owner", interface="native")
    assert result["project"]["id"] == PROJECT_ID
    assert result["metadata"]["recommended_model"] == "gemini-pro"


def test_save_decision_creates_timeline_and_search_doc(fake_client: FakeClient) -> None:
    """Guardar decisiones debe indexar documentos y timeline."""
    result = server_module.save_cross_interface_decision(
        summary="Use shared memory",
        details="Persist context for every interface.",
        owner_id="demo-owner",
        project_id=PROJECT_ID,
    )
    assert result["status"] == "ok"
    assert fake_client.store["memory_documents"][0]["source_type"] == "decision"
    assert any(
        event["event_type"] == "decision.saved" for event in fake_client.store["timeline_events"]
    )


def test_update_task_status_detects_duplicates(fake_client: FakeClient) -> None:
    """Actualizar tareas puede crear warnings por duplicado."""
    server_module.update_task_status(project_id=PROJECT_ID, owner_id="demo-owner", title="Ship API")
    result = server_module.update_task_status(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        title="Ship API",
        status="in_progress",
    )
    assert result["status"] == "ok"
    assert result["warning_count"] >= 1


def test_session_lifecycle_creates_checkpoint(fake_client: FakeClient) -> None:
    """Cerrar sesion debe resumir progreso en un checkpoint."""
    created = server_module.create_session(project_id=PROJECT_ID, owner_id="demo-owner")
    server_module.sync_session_state(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        session_id=created["session_id"],
        state={"summary": "Finished auth middleware", "next_step": "Write tests"},
    )
    ended = server_module.end_session(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        session_id=created["session_id"],
    )
    assert ended["session_status"] == "ended"
    assert ended["checkpoint_id"] is not None


def test_save_file_memory_and_relations(fake_client: FakeClient) -> None:
    """Guarda memoria por archivo y relaciones de dependencia."""
    result = server_module.save_file_memory(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        file_path="src/auth.py",
        summary="Authentication entry point.",
        dependencies=["src/db.py"],
    )
    assert result["status"] == "ok"
    assert fake_client.store["file_relations"][0]["target_file"] == "src/db.py"


def test_save_prompt_pattern(fake_client: FakeClient) -> None:
    """Persiste prompts utiles para futuros flujos."""
    result = server_module.save_prompt_pattern(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        title="Architecture review",
        prompt="Review the architecture before coding.",
    )
    assert result["prompt_pattern"]["title"] == "Architecture review"


def test_capture_project_memory_saves_multiple_artifacts(fake_client: FakeClient) -> None:
    """Guarda decisiones, tareas, archivos y checkpoint en una sola llamada."""
    result = server_module.capture_project_memory(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        summary="Iteration summary",
        what_was_done="Finished auth and routing",
        what_is_left=["Write tests", "Review docs"],
        next_step="Write tests",
        decisions=[
            {
                "summary": "Use token rotation",
                "details": "Refresh tokens are mandatory.",
            }
        ],
        tasks=[
            {
                "title": "Write tests",
                "status": "in_progress",
            }
        ],
        file_memory=[
            {
                "file_path": "src/auth.py",
                "summary": "Authentication service",
                "dependencies": ["src/db.py"],
            }
        ],
        prompt_patterns=[
            {
                "title": "Release checklist",
                "prompt": "Review release blockers",
            }
        ],
        session_state={"current_goal": "Finalize auth"},
    )
    assert result["status"] == "ok"
    assert result["saved"]["tasks"] >= 1
    assert result["saved"]["file_memory"] >= 1
    assert result["saved"]["prompt_patterns"] >= 1
    assert result["checkpoint"] is not None


def test_search_semantic_memory_uses_documents(fake_client: FakeClient) -> None:
    """Busca memoria desde documentos indexados."""
    server_module.save_cross_interface_decision(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        summary="Use Supabase",
        details="Persistent storage backend.",
    )
    result = server_module.search_semantic_memory(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        query="persistent storage",
    )
    assert result["match_count"] >= 1


def test_resume_project_returns_summary(fake_client: FakeClient) -> None:
    """Resume_project debe devolver estado listo para continuar."""
    server_module.update_task_status(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        title="Write docs",
        status="pending",
    )
    server_module.save_checkpoint(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        title="Checkpoint",
        functional_state="Finished API skeleton",
        next_steps=["Write docs"],
    )
    result = server_module.resume_project(project_id=PROJECT_ID, owner_id="demo-owner")
    assert result["resume"]["next_step"] == "Write docs"


def test_export_and_import_bundle(fake_client: FakeClient) -> None:
    """Exporta e importa memoria en formato JSON."""
    server_module.save_prompt_pattern(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        title="Prompt one",
        prompt="Do the thing",
    )
    exported = server_module.export_memory_bundle(project_id=PROJECT_ID, owner_id="demo-owner")
    assert exported["format"] == "json"
    imported = server_module.import_memory_bundle(exported["content"], owner_id="demo-owner")
    assert imported["status"] == "ok"


def test_apply_retention_policy(fake_client: FakeClient) -> None:
    """Guarda politicas de retencion y genera checkpoint resumen."""
    result = server_module.apply_retention_policy(project_id=PROJECT_ID, owner_id="demo-owner")
    assert result["policy"]["keep_recent_sessions"] == 5
    assert result["checkpoint"] is not None


def test_get_project_timeline(fake_client: FakeClient) -> None:
    """Lista la linea de tiempo acumulada."""
    server_module.save_prompt_pattern(
        project_id=PROJECT_ID,
        owner_id="demo-owner",
        title="Prompt two",
        prompt="Keep going",
    )
    result = server_module.get_project_timeline(project_id=PROJECT_ID, owner_id="demo-owner")
    assert result["count"] >= 1


@pytest.mark.asyncio
async def test_call_tool_router(fake_client: FakeClient) -> None:
    """Ejecuta una tool via router asincrono."""
    result = await getattr(server_module.server, "call_registered_tool")(
        "resume_project", {"project_id": PROJECT_ID, "owner_id": "demo-owner"}
    )
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_call_tool_unknown_raises() -> None:
    """Protege contra tools inexistentes."""
    with pytest.raises(ValueError):
        await getattr(server_module.server, "call_registered_tool")("unknown_tool", {})


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
