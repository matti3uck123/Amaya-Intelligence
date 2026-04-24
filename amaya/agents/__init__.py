"""LLM dimension + chain agents that turn ingest evidence into a RatingInput.

Public surface:

  rate(rating_id, company_name, sector, ingest_result, completion) -> RatingInput

Everything else — per-dimension prompts, per-agent logic, the Completion
protocol — is implementation detail callers do not need to import.
"""
from amaya.agents.completion import (
    AnthropicCompletion,
    Completion,
    StubCompletion,
)
from amaya.agents.dimension import score_dimension
from amaya.agents.chain import score_chain_position
from amaya.agents.orchestrator import rate

__all__ = [
    "AnthropicCompletion",
    "Completion",
    "StubCompletion",
    "score_dimension",
    "score_chain_position",
    "rate",
]
