# Amaya ADI — AI Durability Index Rating Pipeline

The rating pipeline behind Amaya Intelligence. Deterministic scoring core,
document-ingest layer, and (soon) evidence-linked dimension agents for
AI-durability ratings of operating companies.

**Current status: Sessions 1–2 complete.**

```
 Data room ──▶ Ingest (Session 2) ──▶ Dimension agents (Session 3) ──▶ Scoring (Session 1) ──▶ Rating
    files         text + sections          LLM-produced scores           deterministic        sealed
                                                                          math + CBs          bundle
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
│   └── cli.py                 # `amaya score|verify|methodology|ingest`
├── tests/                     # 67 tests — scoring core + ingest pipeline
└── examples/
    ├── colabor_input.json     # sample pre-scored rating input
    └── sample_dataroom/       # 11 synthetic Colabor data-room documents
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Run the full test suite (67 tests)
pytest -v

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

Session 3 dimension agents pull evidence by section: the MCS agent reads
MKT + COMP chunks; the RMV agent reads FIN + CUST; and so on.

## Roadmap

- **Session 3 — Dimension agents.** LangGraph orchestrator + 12 per-dimension
  Claude Sonnet 4.6 agents + 4 chain-position agents. Output: full
  `RatingInput` the Session 1 engine consumes. End-to-end: `amaya rate ./dataroom`.
- **Session 4 — FastAPI backend.** REST + SSE for live progress.
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
