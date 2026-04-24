"""Per-dimension and per-chain-position analyst prompts.

This is where the methodology lives in natural language. The scoring
engine in Session 1 turns these 1-10 numbers into grades; the ingest
layer in Session 2 gets evidence to the right agent. But the actual
*judgment* — what a 7 vs an 8 on Market Category Stability means for a
food distributor — is encoded here. Changing a rubric is a methodology
change; bump the prompt version alongside any substantive edit.

Each prompt is self-contained and deliberately verbose. The cost of
an extra 200 tokens of rubric is < $0.001; the cost of an ambiguous
rubric that produces inconsistent ratings across companies is
un-bounded.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from amaya.ingest.sections import SectionCode
from amaya.schemas import ChainPosition, DimensionCode

PROMPT_VERSION = "1.0.0"


# ============================================================
# Shared framework
# ============================================================


SYSTEM_PROMPT = """You are a senior analyst at Amaya Intelligence, an independent \
ratings agency that issues AI Durability Index (ADI) ratings for operating \
companies. Your work is consumed by institutional investors, boards, and \
corporate finance teams making capital allocation decisions under \
AI-driven industry transformation.

You are not an AI optimist or pessimist. You apply the methodology with \
detached rigor. Every rationale you produce must be:

1. Grounded in the evidence provided. Cite specific excerpts by source_id.
2. Tight. Two to four sentences. No throat-clearing, no hedging language.
3. Decisive. Pick a number on the rubric and defend it. A rating that \
straddles two bands is not a rating.

When you are uncertain because the evidence is thin, express that via the \
`confidence` field, not via a fence-sitting rationale. Confidence 0.9+ \
means the evidence clearly supports your number. Confidence 0.5 means you \
made a judgment call that could reasonably go one band either direction. \
Confidence below 0.4 means the evidence is too thin to rate — still pick \
your best-guess number, but flag it.

The same input + same methodology version must produce the same rating. \
Be consistent."""


# ============================================================
# Dimension specs
# ============================================================


@dataclass(frozen=True)
class DimensionPromptSpec:
    code: DimensionCode
    name: str
    layer: str
    what_it_measures: str
    rubric: tuple[tuple[int, str], ...]
    evidence_sections: tuple[SectionCode, ...]


DIMENSION_SPECS: dict[DimensionCode, DimensionPromptSpec] = {
    "MCS": DimensionPromptSpec(
        code="MCS",
        name="Market Category Stability",
        layer="External Pressure",
        what_it_measures=(
            "How stable the company's market category is under AI-driven "
            "transformation. Is the problem the company solves being redefined "
            "or eliminated by AI, or does the category remain structurally "
            "intact even as AI changes who wins inside it?"
        ),
        rubric=(
            (10, "AI-proof category. Fundamental demand (food, shelter, care, physical logistics) that AI cannot substitute. Category size stable or growing."),
            (8, "AI reshapes delivery but category endures. Category TAM intact; winners within may rotate but the job-to-be-done persists."),
            (6, "AI partially displaces the category — some use cases migrate to AI-native alternatives, others hold. Category shrinks 10–30%."),
            (4, "AI substantially replaces the category for most use cases. Category shrinks 30–60% over a 5-year horizon."),
            (2, "AI collapses the category. Most demand migrates to AI-native alternatives. Legacy players losing 60%+ of TAM."),
            (1, "Terminal. Category does not survive AI transition in any recognizable form."),
        ),
        evidence_sections=("MKT", "COMP", "CORP"),
    ),
    "CPS": DimensionPromptSpec(
        code="CPS",
        name="Client Profile Stability",
        layer="External Pressure",
        what_it_measures=(
            "How durable the company's customer base is under AI transformation. "
            "Are its customers themselves AI-exposed? If the customer segment "
            "contracts, the company loses revenue even if its category persists."
        ),
        rubric=(
            (10, "Customer segment strongly benefits from AI — customers grow, spend more, multiply."),
            (8, "Customer segment stable; neither beneficiary nor victim of AI."),
            (6, "Customer segment mildly pressured — modest consolidation or slowed growth."),
            (4, "Customer segment materially shrinking — 20–40% revenue base erosion plausible over 3-5y."),
            (2, "Customer segment in active collapse. Account mortality rising year-on-year."),
            (1, "Customer segment will not exist in recognizable form within 5 years."),
        ),
        evidence_sections=("CUST", "FIN", "MKT"),
    ),
    "SCAE": DimensionPromptSpec(
        code="SCAE",
        name="Supply Chain AI Exposure",
        layer="External Pressure",
        what_it_measures=(
            "How much of the company's supply chain — upstream inputs, vendor "
            "relationships, procurement — is being restructured by AI. Upstream "
            "AI adoption can squeeze margins, disintermediate the company, or "
            "change the basis of competition for inputs."
        ),
        rubric=(
            (10, "Supply chain AI-agnostic. Inputs commoditized, vendor mix stable, no meaningful upstream AI displacement risk."),
            (8, "Modest upstream AI adoption. Some efficiency gains flow through but no structural disintermediation."),
            (6, "Upstream vendors adopting AI-mediated channels. Procurement relationships becoming software-gated."),
            (4, "Major upstream AI disintermediation underway. Direct-to-operator AI platforms bypassing the company's traditional middleman role."),
            (2, "Supply chain restructuring is actively eroding the company's margin capture and vendor access."),
            (1, "Supply chain displacement is complete or imminent. Traditional middleman role no longer viable."),
        ),
        evidence_sections=("OPS", "COMP", "MKT"),
    ),
    "CLS": DimensionPromptSpec(
        code="CLS",
        name="Competitive Landscape Shift",
        layer="External Pressure",
        what_it_measures=(
            "How aggressively competitors — especially AI-native entrants and "
            "well-capitalized incumbents — are reshaping the competitive basis. "
            "Is the company being out-invested in AI? Is replication pressure "
            "from AI-native challengers material?"
        ),
        rubric=(
            (10, "Competitive moat strengthening. Incumbents and AI-native entrants both struggling to match the company's position."),
            (8, "Competitive landscape stable. Company holds its own against both classes of competitor."),
            (6, "Mild competitive pressure. Well-capitalized rivals making AI investments that will close feature gaps over 2-3y."),
            (4, "Material replication pressure. AI-native entrants gaining share; incumbents out-spending on AI."),
            (2, "Severe competitive displacement in progress. Company losing deals to AI-native or AI-armed incumbents."),
            (1, "Competitive position terminal — displacement cannot be reversed within available capital runway."),
        ),
        evidence_sections=("COMP", "MKT"),
    ),
    "VPR": DimensionPromptSpec(
        code="VPR",
        name="Value Proposition Replicability",
        layer="Internal Resilience",
        what_it_measures=(
            "How hard it is for an AI-armed competitor to replicate what the "
            "company provides. Physical assets, regulatory moats, network "
            "effects, proprietary data — these are AI-resistant. Software "
            "features, workflows, and content are AI-replicable."
        ),
        rubric=(
            (10, "Value proposition genuinely AI-unreplicable — regulated, physical, or network-moat-protected in ways that capital + AI cannot substitute."),
            (8, "Value proposition hard to replicate. Combinations of physical assets, data, and relationships create real defensibility."),
            (6, "Value proposition partially replicable. Some physical/relational elements; some features AI can duplicate."),
            (4, "Value proposition mostly software/workflow — replicable by a well-resourced AI-native team in 12-24 months."),
            (2, "Value proposition is pure software/content that AI can replicate in months at marginal cost."),
            (1, "Value proposition already replicated by AI-native tooling; company provides no durable edge."),
        ),
        evidence_sections=("PROD", "COMP", "LEGAL"),
    ),
    "WCI": DimensionPromptSpec(
        code="WCI",
        name="Workforce Composition Index",
        layer="Internal Resilience",
        what_it_measures=(
            "How much of the workforce is exposed to AI-driven automation. A "
            "high share of revenue-linked knowledge-worker headcount (sales "
            "reps, support, back-office) is a structural margin risk. "
            "Physical-labor-heavy workforces are more AI-resistant."
        ),
        rubric=(
            (10, "Workforce is predominantly physical-labor or highly specialized expertise — minimal AI automation exposure."),
            (8, "Balanced workforce; knowledge-worker roles exist but are not the dominant cost center."),
            (6, "Material AI exposure. 20–40% of labor cost in roles plausibly automated over 3-5y."),
            (4, "Heavy AI exposure. Majority of labor cost in roles whose work AI can already meaningfully automate."),
            (2, "Workforce is largely in roles AI is already replacing at scale. Major restructuring required to survive."),
            (1, "Workforce is structurally redundant under near-term AI — viability requires replacement of most headcount."),
        ),
        evidence_sections=("TEAM", "OPS", "FIN"),
    ),
    "RMV": DimensionPromptSpec(
        code="RMV",
        name="Revenue Model Vulnerability",
        layer="Internal Resilience",
        what_it_measures=(
            "How exposed the company's revenue model is to AI-driven pricing "
            "pressure, disintermediation, or switching. Unit economics that "
            "depend on high-margin intermediation, per-seat licensing, or "
            "information asymmetry are particularly vulnerable."
        ),
        rubric=(
            (10, "Revenue model AI-insensitive. Pricing power structural — regulated, usage-metered on physical goods, or locked by contract."),
            (8, "Revenue model robust. Modest pricing pressure plausible but no structural compression risk."),
            (6, "Revenue model exposed to AI-driven margin compression. Per-seat or intermediation-based pricing at risk."),
            (4, "Revenue model facing active erosion. Customers actively renegotiating based on AI-driven alternatives."),
            (2, "Revenue model in distress. Material price/volume deterioration already reflected in reported numbers."),
            (1, "Revenue model terminal — unit economics no longer support going-concern operation."),
        ),
        evidence_sections=("FIN", "CUST", "COMP"),
    ),
    "TSR": DimensionPromptSpec(
        code="TSR",
        name="Tech Stack Readiness",
        layer="Internal Resilience",
        what_it_measures=(
            "How AI-ready the company's existing technology foundation is. "
            "Modern data platforms, clean APIs, structured data assets, and "
            "model-deployment muscle are prerequisites for an AI pivot. Legacy "
            "monoliths with data scattered across file shares are structurally "
            "slow to adopt AI."
        ),
        rubric=(
            (10, "AI-native stack. Foundation models integrated into product, clean data pipelines, MLOps at enterprise grade."),
            (8, "Modern stack with active AI/ML deployment. Cloud-native, solid data infra, pilot-to-production pipelines in place."),
            (6, "Modernized stack with some AI capability. Traditional ML in production but no generative AI, limited MLOps."),
            (4, "Hybrid stack. Some modern systems, significant legacy drag. AI deployments require custom integration work."),
            (2, "Legacy-heavy stack. On-prem, batch-oriented, minimal API surface. AI adoption requires multi-year modernization."),
            (1, "Pre-digital stack. AI deployment is not a feature project — it is a full replatform."),
        ),
        evidence_sections=("PROD", "AI"),
    ),
    "LAL": DimensionPromptSpec(
        code="LAL",
        name="Leadership AI Literacy",
        layer="Adaptive Capacity",
        what_it_measures=(
            "Whether the executive team has the mental model, vocabulary, and "
            "operating instincts to lead an AI transition. CEOs who can't "
            "distinguish between RAG and fine-tuning cannot allocate capital "
            "to the right bets, and cannot credibly recruit AI talent."
        ),
        rubric=(
            (10, "Leadership is AI-native. Executives have built or shipped AI-powered products; AI strategy is the business strategy."),
            (8, "Leadership AI-literate. Clear technical vocabulary, specific roadmap commitments, relevant hires made (CAIO, VP AI)."),
            (6, "Leadership aware. Published AI strategy with right concepts but limited shipped product to show for it."),
            (4, "Leadership nominally engaged. Vague language ('leveraging AI'), no senior AI hires, strategy lives in slides not P&L."),
            (2, "Leadership disengaged. AI is treated as an IT project; no executive sponsorship, no capital commitment."),
            (1, "Leadership structurally incapable of running an AI transition. Change of leadership likely prerequisite to survival."),
        ),
        evidence_sections=("TEAM", "AI", "CORP"),
    ),
    "SPS": DimensionPromptSpec(
        code="SPS",
        name="Strategic Planning Speed",
        layer="Adaptive Capacity",
        what_it_measures=(
            "How fast the company can actually move. A correct AI strategy that "
            "takes 4 board cycles to approve is worse than a decent strategy "
            "shipped in 90 days. Governance rhythm, capital allocation flexibility, "
            "and internal decision latency all matter."
        ),
        rubric=(
            (10, "Founder-speed. Major capital reallocations within weeks, not quarters. No governance drag."),
            (8, "Fast. Quarterly strategy cycles with real resource reallocation; board supportive."),
            (6, "Moderate. Annual planning cycles, mid-year adjustments possible but contested."),
            (4, "Slow. Multi-year capex commitments, governance drag on strategic pivots, committee culture."),
            (2, "Very slow. Decision latency measured in 12-18 month cycles; board risk-averse."),
            (1, "Structurally immobile. Governance, capital structure, or culture prevent strategic pivots within available time."),
        ),
        evidence_sections=("GOV", "TEAM", "AI", "CORP"),
    ),
    "ANCR": DimensionPromptSpec(
        code="ANCR",
        name="AI-Native Client Readiness",
        layer="Adaptive Capacity",
        what_it_measures=(
            "Whether the company can serve AI-native clients — the fastest-growing "
            "customer segment of the 2026-2030 decade. AI-native clients expect "
            "agent-facing APIs, structured data exchange, and programmatic "
            "onboarding. Companies that only sell human-to-human lose this "
            "cohort entirely."
        ),
        rubric=(
            (10, "AI-native client first-class. Agent-facing API surface, programmatic onboarding, machine-readable contracts."),
            (8, "AI-native client ready. Strong public API, developer docs, structured integrations live with 10+ partners."),
            (6, "AI-native client achievable. Some API surface exists but not designed for agent consumption; manual integration required."),
            (4, "Human-mediated sales only. No programmatic onboarding. AI-native prospects encounter friction."),
            (2, "No AI-native surface at all. Every customer relationship requires human sales and human service."),
            (1, "Sales and delivery motions structurally incompatible with AI-native buyers."),
        ),
        evidence_sections=("PROD", "CUST", "AI"),
    ),
    "DIM": DimensionPromptSpec(
        code="DIM",
        name="Durable Moat",
        layer="Adaptive Capacity",
        what_it_measures=(
            "What the company's AI-durable moat actually is. Brand, regulatory "
            "license, network effect, physical footprint, proprietary data at "
            "scale — these survive AI. Workflow, feature set, or human-rep "
            "relationships do not."
        ),
        rubric=(
            (10, "Multiple AI-durable moats stacked — physical footprint + regulatory license + data moat + network effect."),
            (8, "One strong AI-durable moat. Physical/regulatory/network protection on which business can compound."),
            (6, "Moat exists but is partial. Real assets and relationships, offset by replicable workflow/brand components."),
            (4, "Thin moat. Primarily customer habits and rep relationships — erodes under AI-mediated alternatives."),
            (2, "Effectively no moat. Whatever the company does, a well-funded AI-native competitor could stand up in 12 months."),
            (1, "Negative moat — the company's assets are liabilities under AI transition (e.g. large headcount in automated roles)."),
        ),
        evidence_sections=("CORP", "LEGAL", "PROD", "OPS"),
    ),
}


# ============================================================
# Chain-position specs
# ============================================================


@dataclass(frozen=True)
class ChainPromptSpec:
    position: ChainPosition
    name: str
    what_it_measures: str
    rubric: tuple[tuple[int, str], ...]


CHAIN_SPECS: dict[ChainPosition, ChainPromptSpec] = {
    "upstream": ChainPromptSpec(
        position="upstream",
        name="Upstream Position",
        what_it_measures=(
            "AI exposure of the suppliers, producers, and input providers the "
            "company depends on. Upstream AI adoption can compress margins, "
            "restructure vendor relationships, or disintermediate the company."
        ),
        rubric=(
            (10, "Upstream benefits strongly from AI — suppliers more productive, more reliable, lower input costs flow through."),
            (8, "Upstream stable; neither a tailwind nor a threat."),
            (6, "Modest upstream AI restructuring. Some vendor relationships changing shape."),
            (4, "Material upstream AI displacement. Key suppliers building direct-to-customer AI channels."),
            (2, "Upstream actively disintermediating the company — suppliers going around."),
            (1, "Upstream relationship terminal — traditional vendor/buyer structure will not exist."),
        ),
    ),
    "downstream": ChainPromptSpec(
        position="downstream",
        name="Downstream Position",
        what_it_measures=(
            "AI exposure of the customers and distribution channels the company "
            "sells through. Downstream AI adoption can reshape buying behavior, "
            "introduce new intermediaries, or eliminate the need for the "
            "company's current sales motion entirely."
        ),
        rubric=(
            (10, "Downstream AI adoption is a tailwind — customers buy more, more often, with lower friction."),
            (8, "Downstream stable. Customer behavior shifting modestly but within existing channels."),
            (6, "Downstream AI pressure emerging. Some customers migrating to AI-mediated channels."),
            (4, "Material downstream AI displacement. Customer segments actively adopting AI-native alternatives."),
            (2, "Downstream collapse in progress. Customers leaving the category or using AI to bypass the company."),
            (1, "Downstream relationship terminal — the sales motion no longer reaches buyers."),
        ),
    ),
    "lateral": ChainPromptSpec(
        position="lateral",
        name="Lateral Position",
        what_it_measures=(
            "AI activity among peers, partners, and adjacent categories — the "
            "horizontal layer. Lateral AI adoption signals how fast competitors "
            "and complementors are moving. A company surrounded by AI-forward "
            "peers faces higher replication pressure than one surrounded by "
            "laggards."
        ),
        rubric=(
            (10, "Lateral ecosystem AI-inert — low competitive pressure, low replication risk."),
            (8, "Lateral ecosystem moving at moderate pace. Peers adopting AI but nothing disruptive."),
            (6, "Lateral ecosystem actively AI-investing. Material competitive pressure developing."),
            (4, "Lateral ecosystem AI-forward. Several peers shipping AI features faster than the company."),
            (2, "Lateral ecosystem in AI arms race. Company visibly lagging peer group on AI adoption."),
            (1, "Lateral ecosystem has out-evolved the company — peers operate at a fundamentally different tempo."),
        ),
    ),
    "end_consumer": ChainPromptSpec(
        position="end_consumer",
        name="End Consumer Position",
        what_it_measures=(
            "Whether the ultimate end-user demand — not intermediate buyers — "
            "persists through the AI transition. A company can have stable "
            "wholesale customers whose own end-consumers are leaving them. "
            "End-consumer demand is the bedrock signal."
        ),
        rubric=(
            (10, "End-consumer demand is structural and growing. AI does not substitute for what end-users ultimately consume."),
            (8, "End-consumer demand stable. The thing people ultimately want persists."),
            (6, "End-consumer demand stable but shifting delivery. Same need, different intermediary."),
            (4, "End-consumer demand partially replaced by AI-native substitutes."),
            (2, "End-consumer demand materially eroding — AI substitutes are winning real share."),
            (1, "End-consumer demand collapsing — the underlying need is dissolving or being served entirely differently."),
        ),
    ),
}


# ============================================================
# Prompt builders
# ============================================================


def build_dimension_prompt(
    spec: DimensionPromptSpec,
    company_name: str,
    sector: str,
    evidence_text: str,
) -> str:
    rubric_lines = "\n".join(f"- **{score}**: {text}" for score, text in spec.rubric)
    return _DIMENSION_TEMPLATE.format(
        name=spec.name,
        layer=spec.layer,
        what_it_measures=spec.what_it_measures,
        rubric=rubric_lines,
        company_name=company_name,
        sector=sector or "—",
        evidence=evidence_text,
        code=spec.code,
    )


def build_chain_prompt(
    spec: ChainPromptSpec,
    company_name: str,
    sector: str,
    evidence_text: str,
) -> str:
    rubric_lines = "\n".join(f"- **{score}**: {text}" for score, text in spec.rubric)
    return _CHAIN_TEMPLATE.format(
        name=spec.name,
        what_it_measures=spec.what_it_measures,
        rubric=rubric_lines,
        company_name=company_name,
        sector=sector or "—",
        evidence=evidence_text,
        position=spec.position,
    )


def format_evidence(chunks: Sequence) -> str:
    """Format a list of ClassifiedChunk objects as a numbered evidence
    block for the prompt."""
    if not chunks:
        return "(No evidence chunks matched this dimension's sections.)"
    lines: list[str] = []
    for i, c in enumerate(chunks, start=1):
        source_id_short = c.raw.source_id[:12]
        lines.append(
            f"[{i}] source_id={source_id_short} file={c.raw.source_file} "
            f"section={c.section} locator={c.raw.locator}\n"
            f"{c.raw.text.strip()}\n"
        )
    return "\n".join(lines)


def dimension_tool_schema(code: DimensionCode) -> dict:
    return {
        "type": "object",
        "required": ["score", "rationale", "confidence", "evidence_indices"],
        "properties": {
            "score": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": f"Your {code} rating on the 1-10 rubric.",
            },
            "rationale": {
                "type": "string",
                "description": (
                    "Two to four sentences. Cite specific evidence indices like "
                    "[1], [3]. No hedging. Defend your number."
                ),
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Your confidence in the score given the evidence.",
            },
            "evidence_indices": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Indices (from the evidence block) of the 1-3 excerpts most determinative of your score.",
            },
        },
    }


def chain_tool_schema(position: ChainPosition) -> dict:
    return {
        "type": "object",
        "required": ["score", "rationale"],
        "properties": {
            "score": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": f"Your {position} position rating on the 1-10 rubric.",
            },
            "rationale": {
                "type": "string",
                "description": "One or two sentences. Cite specific evidence indices like [1], [3].",
            },
        },
    }


_DIMENSION_TEMPLATE = """# Dimension: {name} ({code})

**Layer:** {layer}

**What this measures:** {what_it_measures}

## Scoring rubric (1-10)

{rubric}

## Company under review

- Name: {company_name}
- Sector: {sector}

## Evidence (from company data room)

{evidence}

## Instructions

Read the evidence. Apply the rubric. Call the `submit_{code}_score` tool with:

- `score` (1-10 integer) — your rating
- `rationale` (2-4 sentences) — analytical defense citing evidence by index
- `confidence` (0.0-1.0) — your certainty given the evidence
- `evidence_indices` (list of integers) — the 1-3 most determinative excerpts

Pick a number. Defend it. Cite the evidence."""


_CHAIN_TEMPLATE = """# Chain position: {name}

**What this measures:** {what_it_measures}

## Scoring rubric (1-10)

{rubric}

## Company under review

- Name: {company_name}
- Sector: {sector}

## Evidence (from company data room)

{evidence}

## Instructions

Read the evidence. Apply the rubric. Call the `submit_{position}_score` tool with:

- `score` (1-10 integer) — your rating
- `rationale` (1-2 sentences) — analytical defense citing evidence by index"""
