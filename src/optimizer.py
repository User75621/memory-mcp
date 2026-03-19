"""Optimizacion de contexto para interfaces con distintos limites de memoria."""

from __future__ import annotations

import json
from typing import Any


class ContextOptimizer:
    """Comprime y prioriza contexto persistente para agentes multi-interfaz."""

    INTERFACE_LIMITS = {
        "native": 24000,
        "opencode": 48000,
        "claude-code": 56000,
        "qwen-code": 32000,
        "codex": 64000,
    }

    def estimate_tokens(self, payload: Any) -> int:
        """Estima tokens usando un ratio conservador basado en caracteres.

        Args:
            payload: Texto o estructura serializable.

        Returns:
            Conteo aproximado de tokens.
        """
        if isinstance(payload, str):
            serialized = payload
        else:
            serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        return max(1, len(serialized) // 4)

    def trim_context(self, context: dict[str, Any], max_tokens: int) -> dict[str, Any]:
        """Recorta listas secundarias hasta respetar un limite maximo.

        Args:
            context: Contexto agregado del proyecto.
            max_tokens: Limite maximo permitido.

        Returns:
            Contexto reducido sin romper su estructura principal.
        """
        trimmed = dict(context)
        working = {
            "decisions": list(context.get("decisions", [])),
            "tasks": list(context.get("tasks", [])),
            "warnings": list(context.get("warnings", [])),
            "sessions": list(context.get("sessions", [])),
        }

        trimmed.update(working)
        while self.estimate_tokens(trimmed) > max_tokens:
            removed = False
            for key in ("sessions", "warnings", "tasks", "decisions"):
                if working[key]:
                    working[key].pop(0)
                    trimmed[key] = list(working[key])
                    removed = True
                    break
            if not removed:
                break
        return trimmed

    def optimize_for_interface(
        self,
        context: dict[str, Any],
        interface_name: str,
    ) -> dict[str, Any]:
        """Ajusta el contexto segun el tipo de interfaz consumidora.

        Args:
            context: Contexto unificado listo para consumo.
            interface_name: Interfaz objetivo, por ejemplo opencode o codex.

        Returns:
            Contexto anotado y posiblemente recortado.
        """
        interface_key = interface_name.strip().lower() or "native"
        limit = self.INTERFACE_LIMITS.get(interface_key, self.INTERFACE_LIMITS["native"])
        optimized = self.trim_context(context, limit)
        optimized["interface"] = interface_key
        optimized["token_estimate"] = self.estimate_tokens(optimized)
        optimized["strategy"] = {
            "limit": limit,
            "focus": (
                "code"
                if interface_key in {"opencode", "claude-code", "qwen-code", "codex"}
                else "reasoning"
            ),
        }
        return optimized
