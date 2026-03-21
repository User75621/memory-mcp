"""Utilidades para detectar y describir el repositorio actual."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    """Convierte texto libre en un slug estable.

    Args:
        value: Cadena libre.

    Returns:
        Texto normalizado apto para slugs.
    """
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "memory-project"


@dataclass(slots=True)
class RepoContext:
    """Describe el repo o carpeta asociado a la sesion actual."""

    repo_root: str
    repo_name: str
    repo_slug: str
    repo_remote: str
    repo_branch: str
    repo_commit: str
    repo_status: list[str]
    repo_provider: str

    def to_dict(self) -> dict[str, Any]:
        """Convierte la instancia a diccionario serializable."""
        return asdict(self)


def _run_git(args: list[str], cwd: str) -> str:
    """Ejecuta un comando git y retorna stdout normalizado."""
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _candidate_paths(explicit_path: str | None = None) -> list[Path]:
    """Reune posibles rutas de trabajo para detectar el repo actual."""
    env_candidates = [
        explicit_path,
        os.getenv("PROJECT_MEMORY_REPO_PATH"),
        os.getenv("PROJECT_MEMORY_WORKSPACE"),
        os.getenv("GIT_WORK_TREE"),
        os.getenv("INIT_CWD"),
        os.getenv("PWD"),
        os.getenv("VSCODE_WORKSPACE_FOLDER"),
        os.getenv("REPO_PATH"),
        str(Path.cwd()),
    ]
    seen: set[str] = set()
    candidates: list[Path] = []
    for raw in env_candidates:
        if not raw:
            continue
        path = Path(raw).expanduser()
        normalized = str(path)
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(path)
    return candidates


def detect_repo_context(explicit_path: str | None = None) -> RepoContext:
    """Detecta nombre, ruta y estado del repositorio actual.

    Args:
        explicit_path: Ruta opcional para forzar la deteccion.

    Returns:
        Contexto del repo o carpeta activa.
    """
    for candidate in _candidate_paths(explicit_path):
        if not candidate.exists():
            continue
        repo_root = _run_git(["rev-parse", "--show-toplevel"], str(candidate))
        root_path = Path(repo_root or candidate).resolve()
        repo_name = root_path.name or "memory-project"
        branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], str(root_path))
        commit = _run_git(["rev-parse", "HEAD"], str(root_path))
        remote = _run_git(["remote", "get-url", "origin"], str(root_path))
        status_output = _run_git(["status", "--porcelain"], str(root_path))
        status_lines = [line for line in status_output.splitlines() if line.strip()]
        provider = "local"
        lowered_remote = remote.lower()
        if "github" in lowered_remote:
            provider = "github"
        elif "gitlab" in lowered_remote:
            provider = "gitlab"
        elif "bitbucket" in lowered_remote:
            provider = "bitbucket"
        return RepoContext(
            repo_root=str(root_path),
            repo_name=repo_name,
            repo_slug=slugify(repo_name),
            repo_remote=remote,
            repo_branch=branch or "unknown",
            repo_commit=commit or "unknown",
            repo_status=status_lines,
            repo_provider=provider,
        )

    fallback = Path.cwd().resolve()
    return RepoContext(
        repo_root=str(fallback),
        repo_name=fallback.name or "memory-project",
        repo_slug=slugify(fallback.name or "memory-project"),
        repo_remote="",
        repo_branch="unknown",
        repo_commit="unknown",
        repo_status=[],
        repo_provider="local",
    )


def derive_workspace_slug(owner_id: str, repo_remote: str) -> str:
    """Deriva un workspace estable desde owner o remoto git."""
    if repo_remote and "/" in repo_remote:
        remote_parts = re.split(r"[:/]", repo_remote.rstrip("/"))
        if len(remote_parts) >= 2:
            candidate = remote_parts[-2]
            if candidate and candidate not in {"github.com", "gitlab.com", "bitbucket.org"}:
                return slugify(candidate)
    return slugify(owner_id)
