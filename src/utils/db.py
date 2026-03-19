"""Ayudas para crear y configurar el cliente de Supabase."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover - fallback para entornos sin dependencia
    Client = Any  # type: ignore[misc,assignment]

    def create_client(url: str, key: str) -> Any:
        raise RuntimeError(
            "supabase package is required to create the client at runtime"
        )


load_dotenv()


def get_supabase_client() -> Client:
    """Crea un cliente autenticado de Supabase desde variables de entorno.

    Returns:
        Cliente listo para consultas PostgREST.

    Raises:
        EnvironmentError: Si faltan variables obligatorias.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()

    if not supabase_url or not supabase_key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_KEY must be configured"
        )

    return create_client(supabase_url, supabase_key)


def set_owner_context(client: Any, owner_id: str) -> Any:
    """Adjunta contexto del propietario para apoyar RLS y trazabilidad.

    Args:
        client: Cliente de Supabase ya inicializado.
        owner_id: Identificador unico del usuario o workspace.

    Returns:
        El mismo cliente, enriquecido con metadata cuando es posible.

    Raises:
        ValueError: Si owner_id llega vacio.
    """
    normalized_owner = str(owner_id).strip()
    if not normalized_owner:
        raise ValueError("owner_id is required")

    if hasattr(client, "options") and getattr(client.options, "headers", None) is not None:
        client.options.headers["X-Owner-Context"] = normalized_owner

    if hasattr(client, "postgrest") and hasattr(client.postgrest, "session"):
        setattr(client.postgrest, "session", {"owner_id": normalized_owner})

    setattr(client, "owner_id", normalized_owner)
    return client
