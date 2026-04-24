"""FastAPI dependency providers.

Every provider is a simple callable so tests can swap them via
`app.dependency_overrides[...]`. Factories live here (not inline in
routes) so the wiring is discoverable and overridable.
"""
from __future__ import annotations

from fastapi import HTTPException

from amaya.agents.completion import AnthropicCompletion, Completion
from amaya.api.jobs import JobRegistry
from amaya.ingest.classifier import Classifier, KeywordClassifier


def get_completion() -> Completion:
    """Production default: real Anthropic client.

    Tests override this with StubCompletion. Returns a clean 503 rather
    than a 500 trace when the API key is missing, so the dashboard can
    show a setup hint instead of a scary error.
    """
    try:
        return AnthropicCompletion()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


def get_classifier() -> Classifier:
    """Default to the zero-cost keyword classifier.

    The ingest layer supports AnthropicClassifier too, but for the demo
    the keyword one is plenty accurate and instant.
    """
    return KeywordClassifier()


_registry: JobRegistry | None = None


def get_registry() -> JobRegistry:
    """Process-wide singleton. Created lazily on first request."""
    global _registry
    if _registry is None:
        _registry = JobRegistry()
    return _registry


def reset_registry() -> None:
    """Test hook — fresh registry between test cases."""
    global _registry
    _registry = None
