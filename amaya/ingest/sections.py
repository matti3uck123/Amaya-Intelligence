"""The 12-section data-room taxonomy.

Each uploaded chunk is classified into exactly one of these sections.
Sections are the *evidence index* — Session 3 dimension agents pull
chunks by section when scoring (e.g. the MCS agent reads MKT + COMP
chunks; the RMV agent reads FIN + CUST).

The taxonomy is an engineering choice, not a methodology choice: it
does not appear in v1.0.yaml and changing it does not bump the
methodology version. It bumps the *pipeline* version instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SectionCode = Literal[
    "CORP", "FIN", "PROD", "CUST",
    "COMP", "TEAM", "OPS", "LEGAL",
    "MKT", "AI", "GOV", "OTHER",
]


@dataclass(frozen=True)
class SectionSpec:
    code: SectionCode
    label: str
    description: str
    keywords: tuple[str, ...]
    feeds_dimensions: tuple[str, ...]


SECTIONS: dict[SectionCode, SectionSpec] = {
    "CORP": SectionSpec(
        code="CORP",
        label="Corporate Overview",
        description="Company description, pitch deck, mission, sector positioning, history, vision.",
        keywords=(
            "mission", "vision", "founded", "headquartered", "about us",
            "company overview", "who we are", "pitch deck", "executive summary",
            "sector", "industry", "business description",
        ),
        feeds_dimensions=("DIM", "MCS"),
    ),
    "FIN": SectionSpec(
        code="FIN",
        label="Financials",
        description="Revenue, P&L, balance sheet, cap table, burn, ARR/MRR, margins, unit economics.",
        keywords=(
            "revenue", "arr", "mrr", "ebitda", "gross margin", "net margin",
            "p&l", "income statement", "balance sheet", "cap table",
            "burn rate", "runway", "cash flow", "unit economics",
            "bookings", "customer acquisition cost", "ltv", "cac",
        ),
        feeds_dimensions=("RMV", "CPS"),
    ),
    "PROD": SectionSpec(
        code="PROD",
        label="Product & Technology",
        description="Product documentation, tech stack, engineering architecture, feature set, roadmap.",
        keywords=(
            "product", "feature", "architecture", "api", "sdk",
            "tech stack", "engineering", "platform", "integration",
            "microservices", "database", "infrastructure", "frontend", "backend",
            "machine learning", "algorithm", "model training",
        ),
        feeds_dimensions=("VPR", "TSR", "ANCR"),
    ),
    "CUST": SectionSpec(
        code="CUST",
        label="Customers & Contracts",
        description="Customer list, logo concentration, contracts, retention, churn, NPS, case studies.",
        keywords=(
            "customer", "client", "contract", "retention", "churn",
            "nps", "logo", "case study", "testimonial", "renewal",
            "msa", "master service agreement", "sow", "statement of work",
            "enterprise customer", "smb", "key account",
        ),
        feeds_dimensions=("CPS", "RMV", "ANCR"),
    ),
    "COMP": SectionSpec(
        code="COMP",
        label="Competitive Landscape",
        description="Competitor analysis, market share, positioning matrices, differentiation.",
        keywords=(
            "competitor", "competition", "market share", "positioning",
            "differentiation", "versus", "alternative", "incumbent",
            "challenger", "landscape", "moat", "competitive advantage",
            "gartner", "forrester", "magic quadrant",
        ),
        feeds_dimensions=("CLS", "VPR"),
    ),
    "TEAM": SectionSpec(
        code="TEAM",
        label="Leadership & Team",
        description="Executive bios, org chart, headcount, key hires, board of directors.",
        keywords=(
            "ceo", "cto", "cfo", "coo", "chief", "founder", "cofounder",
            "co-founder", "executive team", "leadership", "org chart",
            "headcount", "employees", "bio", "biography", "experience",
            "previously", "background",
        ),
        feeds_dimensions=("LAL", "WCI"),
    ),
    "OPS": SectionSpec(
        code="OPS",
        label="Operations & Supply Chain",
        description="Supply chain, fulfillment, logistics, delivery, manufacturing, vendor relationships.",
        keywords=(
            "supply chain", "supplier", "vendor", "fulfillment",
            "logistics", "warehouse", "distribution", "manufacturing",
            "procurement", "inventory", "operations", "delivery",
            "fleet", "route", "last mile",
        ),
        feeds_dimensions=("SCAE", "WCI"),
    ),
    "LEGAL": SectionSpec(
        code="LEGAL",
        label="Legal, IP & Regulatory",
        description="Patents, trademarks, litigation, regulatory filings, compliance, data privacy.",
        keywords=(
            "patent", "trademark", "copyright", "intellectual property",
            "ip portfolio", "litigation", "lawsuit", "regulatory",
            "compliance", "gdpr", "hipaa", "sox", "privacy policy",
            "terms of service", "license", "licensing",
        ),
        feeds_dimensions=("DIM", "VPR"),
    ),
    "MKT": SectionSpec(
        code="MKT",
        label="Market Analysis",
        description="TAM/SAM/SOM, sector research, industry reports, category trends, demographics.",
        keywords=(
            "tam", "sam", "som", "total addressable market",
            "market size", "market opportunity", "cagr",
            "industry report", "sector analysis", "category growth",
            "demographic", "trend", "market research",
        ),
        feeds_dimensions=("MCS", "CPS"),
    ),
    "AI": SectionSpec(
        code="AI",
        label="AI Strategy & Roadmap",
        description="AI/ML strategy, model deployment, data infrastructure, AI product roadmap, policy.",
        keywords=(
            "artificial intelligence", "ai strategy", "ai roadmap",
            "llm", "large language model", "generative ai", "genai",
            "foundation model", "rag", "retrieval augmented",
            "ai governance", "ai policy", "model deployment",
            "ai-native", "ai-first", "mlops", "ai transformation",
        ),
        feeds_dimensions=("LAL", "SPS", "TSR", "ANCR"),
    ),
    "GOV": SectionSpec(
        code="GOV",
        label="Governance & Board",
        description="Board composition, governance policies, committee charters, shareholder materials.",
        keywords=(
            "board of directors", "board meeting", "committee",
            "audit committee", "compensation committee", "governance",
            "shareholder", "proxy", "bylaws", "charter",
            "independent director", "chairman",
        ),
        feeds_dimensions=("SPS",),
    ),
    "OTHER": SectionSpec(
        code="OTHER",
        label="Uncategorized",
        description="Fallback for chunks that don't match any other section.",
        keywords=(),
        feeds_dimensions=(),
    ),
}


def sections_for_dimension(code: str) -> list[SectionCode]:
    """Return the section codes whose evidence informs a given ADI dimension."""
    return [s.code for s in SECTIONS.values() if code in s.feeds_dimensions]
