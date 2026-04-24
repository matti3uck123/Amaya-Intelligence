# Amaya ADI — Deterministic Scoring Core

The heart of the AI Durability Index rating pipeline. No LLM, no external
services, no randomness. Same input + same methodology version → same output,
auditable three years later.

This is **Session 1 of the Path A build** (pure OSS, no paid APIs). It ships
the deterministic layer of the architecture brief's subsystem 05 (Scoring
Engine) and subsystem 07 (review → provenance), plus the versioned
methodology registry from section 05 of the brief.

## What's here

```
Amaya/
├── methodology/
│   └── v1.0.yaml              # dimension weights, CBs, grade bands, chain modifier
├── amaya/
│   ├── schemas.py             # Pydantic models (RatingInput, Rating, ScoringResult)
│   ├── methodology.py         # YAML registry loader
│   ├── scoring.py             # deterministic score() function
│   ├── provenance.py          # sealed bundles, WORM files, hash chain
│   └── cli.py                 # `amaya score|verify|methodology`
├── tests/                     # pytest — every CB, every grade boundary
└── examples/
    └── colabor_input.json     # sample rating input
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Run the full test suite
pytest -v

# Score the Colabor example
amaya score examples/colabor_input.json

# Score and seal into a provenance ledger
amaya score examples/colabor_input.json --seal ./ledger

# Verify the sealed bundle
amaya verify adi-2026Q2-colabor-001 --ledger ./ledger

# Dump the active methodology
amaya methodology
```

## Design invariants

1. **Determinism.** `scoring.score()` is a pure function of `(RatingInput, Methodology)`.
   It calls no LLM, reads no external state, uses no clock, uses no randomness.
   Tests assert byte-equality across repeated calls.

2. **Methodology is versioned and pinned.** A rating records the methodology
   version it was scored under. Changing weights creates v1.1 — old ratings
   never recalculate. This is how Moody's runs.

3. **Circuit breakers are hard caps, not soft penalties.** CB4 (MCS≤2 AND
   VPR≤2) caps the final score at 20 regardless of every other dimension.
   Lowest cap wins when multiple CBs fire.

4. **Provenance bundles are immutable.** Once sealed, the JSON is chmod 444
   and its SHA-256 is appended to a hash chain. `verify()` recomputes the
   hash; any tampering fails verification. This is the local-filesystem
   equivalent of S3 Object Lock + KMS signing called for in the brief.

## What's next (future sessions)

Session 1 delivers the deterministic core. Remaining work to reach MVP:

- **Session 2 — Document ingest.** `unstructured` + `pdfplumber` pipeline,
  12-section data-room classifier (local LLM via Ollama), pgvector storage.
- **Session 3 — LangGraph dimension agents.** 12 per-dimension agents
  running against Ollama (Llama 3.3 or Qwen 2.5). Evidence-linked rationale.
- **Session 4 — Voice interview (best-effort OSS).** Whisper for transcript,
  librosa/opensmile for prosody features. No real-time conversational AI
  without paid TTS.
- **Session 5 — Next.js frontend.** Upload flow, data-room checklist,
  rating view, analyst workbench.
- **Session 6 — Analyst workbench.** Dual sign-off, CMO escalation, review
  queue, audit log UI.
- **Session 7 — Report generators.** `python-pptx` IC deck, WeasyPrint PDF
  rating certificate, JSON API payload.

Everything in Session 1 is designed to stay untouched through those sessions
— the scoring engine is the contract every downstream stage writes to.

## The cost-to-run story

Running `amaya score` on a prepared input costs nothing. The only money
changes hands when dimension scores need to be produced by an LLM
(Session 3). At that point you choose between:

- Ollama + local model (free; noticeably weaker reasoning)
- Anthropic Claude or OpenAI via paid API (~$1–3 per rating)

The scoring engine doesn't care which produced the numbers.
