"""Tests for context optimization utilities."""

from __future__ import annotations

from src.optimizer import ContextOptimizer


def test_estimate_tokens_for_string() -> None:
    """Valida estimacion simple sobre strings."""
    optimizer = ContextOptimizer()
    assert optimizer.estimate_tokens("abcd" * 10) == 10


def test_estimate_tokens_for_dict() -> None:
    """Asegura soporte para estructuras serializables."""
    optimizer = ContextOptimizer()
    tokens = optimizer.estimate_tokens({"message": "hello", "count": 2})
    assert tokens >= 1


def test_trim_context_reduces_lists() -> None:
    """Recorta elementos secundarios cuando supera el limite."""
    optimizer = ContextOptimizer()
    context = {
        "project": {"id": "demo"},
        "decisions": [{"summary": "a" * 300} for _ in range(4)],
        "tasks": [{"title": "b" * 300} for _ in range(4)],
        "warnings": [{"message": "c" * 300} for _ in range(4)],
        "sessions": [{"interface": "native", "notes": "d" * 300} for _ in range(4)],
    }
    trimmed = optimizer.trim_context(context, 180)
    assert optimizer.estimate_tokens(trimmed) <= optimizer.estimate_tokens(context)
    assert len(trimmed["sessions"]) <= len(context["sessions"])


def test_trim_context_handles_empty_lists() -> None:
    """No falla cuando no hay material para recortar."""
    optimizer = ContextOptimizer()
    context = {"project": {"id": "demo"}, "decisions": [], "tasks": []}
    assert optimizer.trim_context(context, 10)["project"]["id"] == "demo"


def test_optimize_for_interface_sets_metadata() -> None:
    """Agrega estrategia y limite por interfaz."""
    optimizer = ContextOptimizer()
    optimized = optimizer.optimize_for_interface({"project": {}}, "qwen-code")
    assert optimized["interface"] == "qwen-code"
    assert optimized["strategy"]["limit"] == 32000
    assert optimized["token_estimate"] >= 1
