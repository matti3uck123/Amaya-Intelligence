"""The narrow interface between agents and whatever LLM backs them.

Every agent calls `completion.complete(system, user, tool_name, tool_schema)`
and expects the tool-call arguments back as a dict. Nothing else. That
means:

- Tests inject `StubCompletion` with a pre-baked response table. No
  network, no API key, no flakiness.
- Production injects `AnthropicCompletion` (Claude Sonnet 4.6).
- A future local-model path (Ollama, vLLM) is a third implementation —
  the agents don't change.

The contract is intentionally Anthropic-tool-use-shaped because Claude's
forced-tool-use is the cleanest structured-output path available today.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Protocol


class Completion(Protocol):
    """Any object that can take a prompt + tool schema and return a dict."""

    async def complete(
        self,
        system: str,
        user_message: str,
        tool_name: str,
        tool_schema: dict[str, Any],
    ) -> dict[str, Any]: ...


# ---------- AnthropicCompletion ----------


@dataclass
class AnthropicCompletion:
    """Claude Sonnet 4.6 with forced tool-use for structured output.

    Uses `tool_choice={type: tool, name: ...}` so the model is guaranteed
    to call our submission tool with our schema — no regex-on-free-text
    parsing, no JSON-mode quirks.
    """

    model: str = "claude-sonnet-4-6"
    api_key: str | None = None
    max_tokens: int = 1024

    def __post_init__(self) -> None:
        key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "AnthropicCompletion requires ANTHROPIC_API_KEY — "
                "set the env var or pass api_key explicitly."
            )
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=key)

    async def complete(
        self,
        system: str,
        user_message: str,
        tool_name: str,
        tool_schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            tools=[
                {
                    "name": tool_name,
                    "description": f"Submit the analytical result via {tool_name}.",
                    "input_schema": tool_schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": user_message}],
        )
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                return dict(block.input)
        raise RuntimeError(
            f"Expected tool_use block for {tool_name}; got {response.content!r}"
        )


# ---------- StubCompletion (tests) ----------


@dataclass
class StubCompletion:
    """Deterministic completion for tests.

    Pass a callable `responder(tool_name, user_message) -> dict`. The
    stub records every invocation so tests can assert on prompt content.
    """

    responder: Callable[[str, str], dict[str, Any]]
    calls: list[dict[str, Any]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.calls is None:
            self.calls = []

    async def complete(
        self,
        system: str,
        user_message: str,
        tool_name: str,
        tool_schema: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "system": system,
                "user_message": user_message,
                "tool_name": tool_name,
                "tool_schema": tool_schema,
            }
        )
        return self.responder(tool_name, user_message)


def stub_from_table(table: dict[str, dict[str, Any]]) -> StubCompletion:
    """Convenience: build a stub from {tool_name: response_dict}."""

    def _responder(tool_name: str, _user: str) -> dict[str, Any]:
        if tool_name not in table:
            raise KeyError(
                f"StubCompletion has no response registered for {tool_name!r}. "
                f"Known: {sorted(table)}"
            )
        return table[tool_name]

    return StubCompletion(responder=_responder)


def dump_response(response: dict[str, Any]) -> str:
    """Pretty-print a completion response for logging. Not on the hot path."""
    return json.dumps(response, indent=2, sort_keys=True)
