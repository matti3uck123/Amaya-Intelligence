"""Tests for the Completion abstraction."""
from __future__ import annotations

import asyncio

import pytest

from amaya.agents.completion import (
    AnthropicCompletion,
    StubCompletion,
    stub_from_table,
)


def test_stub_completion_records_calls() -> None:
    async def _go():
        stub = StubCompletion(responder=lambda _t, _u: {"score": 7})
        result = await stub.complete(
            system="sys",
            user_message="msg",
            tool_name="submit_test",
            tool_schema={"type": "object"},
        )
        assert result == {"score": 7}
        assert len(stub.calls) == 1
        assert stub.calls[0]["tool_name"] == "submit_test"
        assert stub.calls[0]["user_message"] == "msg"

    asyncio.run(_go())


def test_stub_from_table_routes_by_tool_name() -> None:
    async def _go():
        table = {
            "submit_MCS_score": {"score": 6, "rationale": "r", "confidence": 0.8, "evidence_indices": []},
            "submit_FIN_score": {"score": 3, "rationale": "r", "confidence": 0.7, "evidence_indices": []},
        }
        stub = stub_from_table(table)
        a = await stub.complete("sys", "m", "submit_MCS_score", {})
        b = await stub.complete("sys", "m", "submit_FIN_score", {})
        assert a["score"] == 6
        assert b["score"] == 3

    asyncio.run(_go())


def test_stub_from_table_raises_on_unknown_tool() -> None:
    async def _go():
        stub = stub_from_table({"submit_MCS_score": {"score": 5}})
        with pytest.raises(KeyError):
            await stub.complete("sys", "m", "submit_missing_score", {})

    asyncio.run(_go())


def test_anthropic_completion_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicCompletion()


def test_anthropic_completion_accepts_explicit_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    completion = AnthropicCompletion(api_key="sk-ant-fake")
    assert completion.model == "claude-sonnet-4-6"
