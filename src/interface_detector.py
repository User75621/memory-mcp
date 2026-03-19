"""Deteccion de interfaz origen para clientes MCP y herramientas asociadas."""

from __future__ import annotations

import os
from pathlib import Path


def detect_interface() -> str:
    """Detecta la interfaz activa usando entorno y ruta de instalacion.

    Returns:
        Una de las interfaces soportadas: native, opencode, claude-code,
        qwen-code o codex.
    """
    explicit_interface = (
        os.getenv("PROJECT_MEMORY_INTERFACE", "")
        or os.getenv("ANTIGRAVITY_INTERFACE", "")
    ).strip().lower()
    if explicit_interface in {"native", "opencode", "claude-code", "qwen-code", "codex"}:
        return explicit_interface

    executable_hint = " ".join(
        filter(
            None,
            [
                os.getenv("PROJECT_MEMORY_CLIENT", ""),
                os.getenv("TERM_PROGRAM", ""),
                os.getenv("VSCODE_GIT_IPC_HANDLE", ""),
                os.getenv("OPENCODE_SESSION", ""),
                os.getenv("CLAUDECODE", ""),
                os.getenv("CLAUDE_CODE_SESSION", ""),
                os.getenv("QWEN_CODE_SESSION", ""),
                os.getenv("CODEX_SESSION_ID", ""),
                str(Path.cwd()),
            ],
        )
    ).lower()

    if os.getenv("OPENCODE_SESSION") or "opencode" in executable_hint:
        return "opencode"
    if os.getenv("CLAUDECODE") or os.getenv("CLAUDE_CODE_SESSION") or "claude" in executable_hint:
        return "claude-code"
    if "qwen" in executable_hint:
        return "qwen-code"
    if "codex" in executable_hint or os.getenv("OPENAI_API_KEY"):
        return "codex"
    return "native"


def get_model_for_interface(interface_name: str) -> str:
    """Retorna el modelo por defecto recomendado para una interfaz.

    Args:
        interface_name: Interfaz detectada o provista por el cliente.

    Returns:
        Nombre del modelo configurado para esa superficie.
    """
    interface_key = interface_name.strip().lower()
    if interface_key == "opencode":
        return os.getenv("OPENCODE_DEFAULT_MODEL", "gpt-4.1")
    if interface_key == "claude-code":
        return os.getenv("CLAUDE_DEFAULT_MODEL", "claude-3-7-sonnet")
    if interface_key == "qwen-code":
        return os.getenv("QWEN_DEFAULT_MODEL", "qwen2.5-coder")
    if interface_key == "codex":
        return os.getenv("CODEX_DEFAULT_MODEL", "gpt-4.1")
    return os.getenv("DEFAULT_MODEL", "gemini-pro")
