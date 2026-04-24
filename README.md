# Amaya ADI — AI Durability Index Rating Pipeline

The rating pipeline behind Amaya Intelligence. Deterministic scoring core,
document-ingest layer, and (soon) evidence-linked dimension agents for
AI-durability ratings of operating companies.

**Current status: Sessions 1–4 complete.**

```
 Data room ──▶ Ingest (Session 2) ──▶ Dimension agents (Session 3) ──▶ Scoring (Session 1) ──▶ Rating
    files         text + sections          LLM-produced scores           deterministic        sealed
                                                                          math + CBs          bundle
                         ▲
                         │                   Session 4 wraps the whole pipeline in a FastAPI
                         │                   service with SSE progress streaming — the dashboard
                         └──── `amaya serve` ◄── (Session 5) talks to this backend.
```

## What's here

```
Amaya Intelligence/
├── methodology/
│   └── v1.0.yaml              # dimension weights, CBs, grade bands, chain modifier
├── amaya/
│   ├── schemas.py             # Pydantic contracts (RatingInput, Rating, EvidenceRef)
│   ├── methodology.py         # YAML registry loader
│   ├── scoring.py             # deterministic score() function
│   ├── provenance.py          # sealed bundles, WORM files, hash chain
│   ├── ingest/                # Session 2: documents → classified evidence
│   │   ├── sections.py        # 12-section data-room taxonomy
│   │   ├── extract.py         # pdfplumber / python-docx / txt → chunks
│   │   ├── classifier.py      # KeywordClassifier + AnthropicClassifier
│   │   └── pipeline.py        # ingest(path) orchestrator
│   ├── agents/                # Session 3: evidence → dimension + chain scores
│   │   ├── completion.py      # Completion protocol (Anthropic + Stub)
│   │   ├── prompts.py         # 12 dimension + 4 chain prompt specs, schemas
│   │   ├── dimension.py       # score_dimension() — one dimension agent
│   │   ├── chain.py           # score_chain_position() — one chain agent
│   │   └── orchestrator.py    # rate() — runs all 16 agents concurrently
│   ├── api/                   # Session 4: FastAPI service with SSE progress
│   │   ├── app.py             # create_app() — health, methodology, verify
│   │   ├── ratings.py         # POST/GET /ratings + SSE event stream
│   │   ├── runner.py          # async background job runner
│   │   ├── jobs.py            # in-memory registry + event bus
│   │   ├── deps.py            # DI: completion, classifier, registry
│   │   └── schemas.py         # API request/response DTOs
│   └── cli.py                 # `amaya score|verify|methodology|ingest|rate|serve`
├── tests/                     # 126 tests — scoring + ingest + agents + API
└── examples/
    ├── colabor_input.json     # sample pre-scored rating input
    └── sample_dataroom/       # 11 synthetic Colabor data-room documents
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Run the full test suite (126 tests)
pytest -v

# --- Session 4: run the full HTTP backend ---

export ANTHROPIC_API_KEY=sk-ant-...
amaya serve --ledger ./ledger --port 8000
# OpenAPI: http://127.0.0.1:8000/docs
# POST /ratings            (multipart upload of data-room files)
# POST /ratings/from-path  (JSON body, rate a path on the server)
# GET  /ratings/{id}       (poll status + final rating)
# GET  /ratings/{id}/events (SSE — live progress across 16 agents)
# POST /verify             (recompute hash on a sealed bundle)

# --- Session 3: end-to-end rating from a data room ---

# Requires ANTHROPIC_API_KEY; runs 16 agents in parallel (~30-60s, ~$1-3)
export ANTHROPIC_API_KEY=sk-ant-...
amaya rate examples/sample_dataroom --company "Colabor" --sector "Food Distribution"
amaya rate examples/sample_dataroom --company "Colabor" --seal ./ledger

# --- Session 2: ingest a data room ---

# Classify every doc in the sample data room (keyword-based, zero cost)
amaya ingest examples/sample_dataroom

# Write the structured output to disk for the next stage
amaya ingest examples/sample_dataroom --out evidence.json

# Use Claude Haiku instead (set ANTHROPIC_API_KEY first)
amaya ingest examples/sample_dataroom --classifier claude

# --- Session 1: score a rating ---

amaya score examples/colabor_input.json
amaya score examples/colabor_input.json --seal ./ledger
amaya verify adi-2026Q2-colabor-001 --ledger ./ledger
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
   hash; any tampering fails verification.

5. **Ingest is swappable, scoring is not.** The ingest layer produces
   `EvidenceRef` objects and nothing else — the scoring engine doesn't care
   whether those came from pdfplumber or a manual analyst upload. Swap
   classifiers, swap extractors, swap LLMs: the sealing contract is stable.

## The 12-section data-room taxonomy (Session 2)

Every document chunk classified into exactly one of:

| Code  | Section              | Feeds dimensions |
|-------|----------------------|------------------|
| CORP  | Corporate Overview   | DIM, MCS         |
| FIN   | Financials           | RMV, CPS         |
| PROD  | Product & Technology | VPR, TSR, ANCR   |
| CUST  | Customers & Contracts| CPS, RMV, ANCR   |
| COMP  | Competitive Landscape| CLS, VPR         |
| TEAM  | Leadership & Team    | LAL, WCI         |
| OPS   | Operations & Supply  | SCAE, WCI        |
| LEGAL | Legal, IP, Regulatory| DIM, VPR         |
| MKT   | Market Analysis      | MCS, CPS         |
| AI    | AI Strategy & Roadmap| LAL, SPS, TSR, ANCR |
| GOV   | Governance & Board   | SPS              |
| OTHER | Uncategorized        | —                |

Dimension agents pull evidence by section: the MCS agent reads
MKT + COMP chunks; the RMV agent reads FIN + CUST; and so on.

## The agent layer (Session 3)

16 agents run concurrently via `asyncio.gather` — 12 dimension agents (one per
ADI dimension) and 4 chain-position agents (upstream, downstream, lateral,
end_consumer). Each agent receives only the evidence chunks from its declared
sections, a dimension-specific rubric, and must call its own structured tool
(`submit_<code>_score`) to emit score + rationale + confidence + evidence
indices. No LangGraph — there's no state machine, no branching, no iterative
refinement; just parallel structured calls.

The `Completion` protocol cleanly separates agent logic from the LLM client.
Production uses `AnthropicCompletion` (Claude Sonnet 4.6 with forced
tool_choice); tests use `StubCompletion` with a user-supplied responder. Every
agent test runs with zero network calls.

## The API layer (Session 4)

FastAPI on top of the rating pipeline. Every rating runs as an async
background task; progress streams over Server-Sent Events so a dashboard
(or `curl -N`) sees each of the 16 agents fire in real time.

Key design choices:

- **In-memory job registry.** The ledger on disk is the durable record
  of a rating — everything else is ephemeral session state. No database
  to admin for the demo.
- **SSE with history replay.** Every subscriber gets the full event
  history first, then the live tail. Reconnecting the dashboard mid-run
  doesn't miss anything; connecting after completion still gets every
  progress event so the UI can render a full timeline.
- **DI-overridable Completion.** The same `Completion` protocol used by
  the agents flows through FastAPI `Depends`, so every API test runs
  with `StubCompletion` — no API key, no network, deterministic.
- **Upload or from-path.** `POST /ratings` takes multipart files;
  `POST /ratings/from-path` takes a server-local path — the same
  shortcut the CLI uses, convenient for demos.

## Roadmap

- **Session 5 — Next.js dashboard.** Upload flow, rating detail page,
  evidence explorer, provenance verify button.
- **Session 6 — Demo polish.** Pre-loaded flagship ratings, PDF leave-behind
  generator (WeasyPrint), landing page, one-click "reset demo."

## Cost to run

| Operation                         | Cost                         |
|-----------------------------------|------------------------------|
| `amaya score` on prepared input   | Free                         |
| `amaya ingest` (keyword mode)     | Free                         |
| `amaya ingest` (Claude Haiku)     | ~$0.01 per ~50-doc data room |
| Full rating via Session 3 agents  | ~$1–3 per rating             |

The scoring engine doesn't know or care which source produced the dimension
numbers — swap a free path for a paid path anytime without touching it.
