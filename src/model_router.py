"""Enrutamiento de modelos segun tarea, limite y contexto disponible."""

from __future__ import annotations

from typing import Any


class ModelRouter:
    """Selecciona modelos y ajusta contexto de acuerdo con la carga de trabajo."""

    MODEL_STRENGTHS: dict[str, dict[str, Any]] = {
        "gemini-pro": {
            "tasks": {"analysis", "planning", "documentation"},
            "context_limit": 32768,
            "style": "balanced",
        },
        "qwen2.5-coder": {
            "tasks": {"coding", "refactor", "debugging"},
            "context_limit": 65536,
            "style": "code-first",
        },
        "claude-3-7-sonnet": {
            "tasks": {"architecture", "planning", "review"},
            "context_limit": 200000,
            "style": "long-context",
        },
        "gpt-4.1": {
            "tasks": {"reasoning", "review", "multi-step"},
            "context_limit": 131072,
            "style": "deep-reasoning",
        },
    }

    def recommend_model(self, task_type: str) -> str:
        """Recomienda un modelo segun la naturaleza de la tarea.

        Args:
            task_type: Categoria funcional de la tarea.

        Returns:
            Nombre del modelo recomendado.
        """
        normalized_task = task_type.strip().lower()
        for model_name, settings in self.MODEL_STRENGTHS.items():
            if normalized_task in settings["tasks"]:
                return model_name
        return "gemini-pro"

    def get_context_limit(self, model_name: str) -> int:
        """Obtiene el limite de tokens de contexto de un modelo.

        Args:
            model_name: Nombre del modelo a consultar.

        Returns:
            Numero maximo de tokens estimados.
        """
        return int(
            self.MODEL_STRENGTHS.get(model_name, self.MODEL_STRENGTHS["gemini-pro"])[
                "context_limit"
            ]
        )

    def optimize_context_for_model(
        self,
        model_name: str,
        context: dict[str, Any],
        estimated_tokens: int,
    ) -> dict[str, Any]:
        """Marca estrategia de compresion y prioridad por modelo.

        Args:
            model_name: Modelo objetivo.
            context: Contexto previamente agregado.
            estimated_tokens: Tokens calculados para el payload actual.

        Returns:
            Contexto anotado con estrategia de entrega.
        """
        limit = self.get_context_limit(model_name)
        ratio = 0 if limit == 0 else min(1.0, estimated_tokens / limit)
        optimized = dict(context)
        optimized["model"] = model_name
        optimized["delivery_profile"] = {
            "style": self.MODEL_STRENGTHS.get(model_name, {}).get("style", "balanced"),
            "estimated_tokens": estimated_tokens,
            "limit": limit,
            "compression_level": "high" if ratio > 0.8 else "low",
        }
        return optimized
