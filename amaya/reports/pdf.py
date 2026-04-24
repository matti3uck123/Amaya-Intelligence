"""Leave-behind PDF renderer for a sealed rating.

Pure reportlab — no native deps, installs cleanly on every platform. One
A4 page with the company, final grade, dimension breakdown, chain
positions, and any triggered circuit breakers. Matches the dashboard's
ink/copper/grade palette so a prospect sees the same artifact live and
on paper.

The generator consumes a `Rating` directly — same object the API returns
and the ledger seals — so the PDF is a deterministic view of whatever
the scoring engine produced.
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from amaya.schemas import Rating

# Mirrors dashboard/tailwind.config.ts palette so print matches screen.
INK_950 = HexColor("#0d0f12")
INK_800 = HexColor("#1f242b")
INK_700 = HexColor("#2d343d")
INK_500 = HexColor("#6b7683")
INK_400 = HexColor("#8a94a0")
INK_300 = HexColor("#a6afba")
INK_200 = HexColor("#c4cbd3")
INK_100 = HexColor("#e2e6eb")
COPPER_500 = HexColor("#c06b2f")
COPPER_400 = HexColor("#d4874a")
COPPER_300 = HexColor("#e2a274")
BG = HexColor("#f7f5f1")  # warm off-white for print

GRADE_COLORS: dict[str, colors.Color] = {
    "A+": HexColor("#2f8f60"),
    "A": HexColor("#4aa876"),
    "B+": HexColor("#6fa653"),
    "B": HexColor("#b5a742"),
    "C+": HexColor("#d08a3c"),
    "C": HexColor("#c86a3a"),
    "D": HexColor("#b04a3a"),
    "F": HexColor("#8a2a2a"),
}

LAYER_ORDER = ("external", "internal", "adaptive")
LAYER_DISPLAY = {
    "external": ("External Pressure", "40%"),
    "internal": ("Internal Resilience", "35%"),
    "adaptive": ("Adaptive Capacity", "25%"),
}
CHAIN_DISPLAY = {
    "upstream": "Upstream (suppliers)",
    "downstream": "Downstream (distribution)",
    "lateral": "Lateral (peers)",
    "end_consumer": "End consumer",
}

# Hand-mirrored from methodology/v1.0.yaml so the PDF renderer is a
# pure function of the Rating object — no filesystem lookup needed.
DIMENSION_META: dict[str, tuple[str, str]] = {
    "MCS":  ("external", "Market Category Survival"),
    "CPS":  ("external", "Client Profile Survivability"),
    "SCAE": ("external", "Supply Chain AI Exposure"),
    "CLS":  ("external", "Competitive Landscape Shift"),
    "VPR":  ("internal", "Value Proposition Replicability"),
    "WCI":  ("internal", "Workforce Composition Impact"),
    "RMV":  ("internal", "Revenue Model Vulnerability"),
    "TSR":  ("internal", "Tech Stack Readiness"),
    "LAL":  ("adaptive", "Leadership AI Literacy"),
    "SPS":  ("adaptive", "Strategic Pivoting Speed"),
    "ANCR": ("adaptive", "AI-Native Client Readiness"),
    "DIM":  ("adaptive", "Defensible IP & Moat"),
}


def render_rating_pdf(rating: Rating) -> bytes:
    """Render a single-page PDF for the given rating. Returns raw PDF bytes."""
    buf = BytesIO()

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Amaya ADI — {rating.input.company_name}",
        author="Amaya Intelligence",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        showBoundary=0,
    )
    doc.addPageTemplates(
        PageTemplate(id="report", frames=[frame], onPage=_draw_page_chrome)
    )

    styles = _styles()

    flow: list[Flowable] = []
    flow.extend(_header(rating, styles))
    flow.append(Spacer(1, 6 * mm))
    flow.extend(_grade_block(rating, styles))
    flow.append(Spacer(1, 6 * mm))
    flow.extend(_dimension_section(rating, styles))
    flow.append(Spacer(1, 5 * mm))
    flow.extend(_chain_section(rating, styles))

    if rating.result.circuit_breakers_triggered:
        flow.append(Spacer(1, 5 * mm))
        flow.extend(_circuit_breaker_section(rating, styles))

    doc.build(flow)
    return buf.getvalue()


# ---------- page chrome ----------


def _draw_page_chrome(canv, doc) -> None:  # noqa: ANN001 - reportlab signature
    canv.saveState()
    # Top bar
    canv.setFillColor(COPPER_500)
    canv.rect(0, A4[1] - 4 * mm, A4[0], 4 * mm, fill=1, stroke=0)
    # Footer rule
    canv.setStrokeColor(INK_300)
    canv.setLineWidth(0.25)
    canv.line(
        doc.leftMargin,
        doc.bottomMargin - 3 * mm,
        A4[0] - doc.rightMargin,
        doc.bottomMargin - 3 * mm,
    )
    canv.setFont("Helvetica", 7.5)
    canv.setFillColor(INK_500)
    canv.drawString(
        doc.leftMargin,
        doc.bottomMargin - 6 * mm,
        "Confidential · Amaya Intelligence · AI Durability Index",
    )
    canv.drawRightString(
        A4[0] - doc.rightMargin,
        doc.bottomMargin - 6 * mm,
        f"Methodology {doc.title.split('—')[-1].strip()}",
    )
    canv.restoreState()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "eyebrow",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=COPPER_500,
            spaceAfter=1,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=INK_950,
            spaceAfter=2,
        ),
        "sub": ParagraphStyle(
            "sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=INK_500,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=INK_500,
            spaceAfter=3,
        ),
        "layer": ParagraphStyle(
            "layer",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=INK_500,
            spaceBefore=3,
            spaceAfter=2,
        ),
        "score_big": ParagraphStyle(
            "score_big",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=28,
            textColor=INK_950,
        ),
        "score_small": ParagraphStyle(
            "score_small",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=INK_500,
        ),
        "action": ParagraphStyle(
            "action",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=10,
            leading=13,
            textColor=INK_700,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=INK_700,
        ),
        "rationale": ParagraphStyle(
            "rationale",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=INK_500,
        ),
        "cb_title": ParagraphStyle(
            "cb_title",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=HexColor("#8a2a2a"),
            spaceAfter=2,
        ),
        "cb_body": ParagraphStyle(
            "cb_body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=INK_700,
        ),
    }


# ---------- header ----------


def _header(rating: Rating, st: dict[str, ParagraphStyle]) -> list[Flowable]:
    issued = rating.issued_at.strftime("%d %b %Y")
    return [
        Paragraph("AI DURABILITY INDEX — RATING REPORT", st["eyebrow"]),
        Paragraph(_escape(rating.input.company_name), st["h1"]),
        Paragraph(
            f"{_escape(rating.input.sector) or '—'} &nbsp;·&nbsp; "
            f"<font face='Courier'>{_escape(rating.input.rating_id)}</font> &nbsp;·&nbsp; "
            f"Issued {issued}",
            st["sub"],
        ),
    ]


# ---------- grade block ----------


def _grade_block(rating: Rating, st: dict[str, ParagraphStyle]) -> list[Flowable]:
    result = rating.result
    grade_cell = _GradeTile(result.grade, 36 * mm, 24 * mm)

    scores_tbl = Table(
        [
            [
                Paragraph("FINAL SCORE", st["section"]),
                Paragraph("RAW", st["section"]),
                Paragraph("CHAIN MOD.", st["section"]),
                Paragraph("ADJUSTED", st["section"]),
            ],
            [
                Paragraph(f"{result.final_score:.1f}<font size=8 color='#6b7683'> / 100</font>", st["score_big"]),
                Paragraph(f"{result.raw_score:.1f}", st["score_big"]),
                Paragraph(
                    f"×{result.chain_modifier:.2f}",
                    ParagraphStyle(
                        "mod",
                        parent=st["score_big"],
                        textColor=COPPER_500 if result.chain_modifier >= 1.0 else HexColor("#b04a3a"),
                    ),
                ),
                Paragraph(f"{result.adjusted_score:.1f}", st["score_big"]),
            ],
        ],
        colWidths=[38 * mm, 28 * mm, 28 * mm, 28 * mm],
    )
    scores_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LINEBEFORE", (1, 0), (-1, -1), 0.25, INK_300),
                ("LEFTPADDING", (1, 0), (-1, -1), 5),
            ]
        )
    )

    label_text = f"<b>{_escape(result.grade_label)}</b> &nbsp;·&nbsp; {_escape(result.grade_action)}"

    top = Table(
        [[grade_cell, scores_tbl]],
        colWidths=[40 * mm, None],
    )
    top.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return [top, Spacer(1, 3 * mm), Paragraph(label_text, st["action"])]


# ---------- dimensions ----------


def _dimension_section(
    rating: Rating,
    st: dict[str, ParagraphStyle],
) -> list[Flowable]:
    avg_conf = (
        sum(d.confidence for d in rating.input.dimension_scores)
        / max(len(rating.input.dimension_scores), 1)
    )
    header = Table(
        [
            [
                Paragraph("DIMENSION BREAKDOWN — 12 AGENTS", st["section"]),
                Paragraph(
                    f"avg confidence {avg_conf * 100:.0f}%",
                    ParagraphStyle("rt", parent=st["section"], alignment=TA_RIGHT),
                ),
            ]
        ],
        colWidths=[None, 50 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    flow: list[Flowable] = [header, Spacer(1, 1 * mm)]

    by_layer: dict[str, list] = {k: [] for k in LAYER_ORDER}
    for d in rating.input.dimension_scores:
        layer, _ = DIMENSION_META.get(d.code, ("external", d.code))
        by_layer.setdefault(layer, []).append(d)

    for layer in LAYER_ORDER:
        dims = by_layer.get(layer) or []
        if not dims:
            continue
        display, weight = LAYER_DISPLAY[layer]
        flow.append(
            Paragraph(
                f"<b>{display.upper()}</b> &nbsp;·&nbsp; layer weight {weight}",
                st["layer"],
            )
        )

        rows = [["Code", "Dimension", "Score", "Conf.", "Bar"]]
        for d in sorted(dims, key=lambda x: -x.score):
            _, name = DIMENSION_META.get(d.code, ("", d.code))
            rows.append(
                [
                    Paragraph(f"<font face='Courier-Bold'>{d.code}</font>", st["body"]),
                    Paragraph(_escape(name), st["body"]),
                    Paragraph(f"<b>{d.score}</b>", st["body"]),
                    Paragraph(f"{d.confidence * 100:.0f}%", st["body"]),
                    _ScoreBar(d.score, 44 * mm, 3.5 * mm),
                ]
            )
        tbl = Table(
            rows,
            colWidths=[12 * mm, 70 * mm, 10 * mm, 12 * mm, 46 * mm],
            rowHeights=[5 * mm] + [5 * mm] * (len(rows) - 1),
        )
        tbl.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("TEXTCOLOR", (0, 0), (-1, 0), INK_500),
                    ("ALIGN", (2, 0), (3, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.25, INK_300),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        flow.append(tbl)

    return flow


# ---------- chain ----------


def _chain_section(rating: Rating, st: dict[str, ParagraphStyle]) -> list[Flowable]:
    mod = rating.result.chain_modifier
    direction = "tailwind" if mod >= 1.0 else "headwind"
    pill_color = COPPER_500 if mod >= 1.0 else HexColor("#b04a3a")

    head = Table(
        [
            [
                Paragraph("CHAIN POSITION — 4 AGENTS", st["section"]),
                Paragraph(
                    f"<font color='{pill_color.hexval()}'><b>×{mod:.2f}</b></font>"
                    f" &nbsp;<font size=7 color='#6b7683'>{direction}</font>",
                    ParagraphStyle("rt", parent=st["section"], alignment=TA_RIGHT, fontSize=10),
                ),
            ]
        ],
        colWidths=[None, 50 * mm],
    )
    head.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    rows: list[list] = []
    for p in rating.input.chain.positions:
        rows.append(
            [
                Paragraph(_escape(CHAIN_DISPLAY.get(p.position, p.position)), st["body"]),
                _ScoreBar(p.score, 80 * mm, 3.5 * mm),
                Paragraph(f"<b>{p.score}</b>", st["body"]),
            ]
        )
    tbl = Table(
        rows,
        colWidths=[50 * mm, 82 * mm, 18 * mm],
        rowHeights=[5 * mm] * len(rows),
    )
    tbl.setStyle(
        TableStyle(
            [
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return [head, Spacer(1, 1 * mm), tbl]


# ---------- circuit breakers ----------


def _circuit_breaker_section(
    rating: Rating, st: dict[str, ParagraphStyle]
) -> list[Flowable]:
    flow: list[Flowable] = [
        Paragraph("⚠  CIRCUIT BREAKERS TRIGGERED", st["cb_title"]),
    ]
    rows = []
    for cb in rating.result.circuit_breakers_triggered:
        rows.append(
            [
                Paragraph(f"<font face='Courier-Bold'>{cb.code}</font>", st["cb_body"]),
                Paragraph(_escape(cb.description), st["cb_body"]),
                Paragraph(
                    f"cap {cb.cap}",
                    ParagraphStyle(
                        "cap",
                        parent=st["cb_body"],
                        alignment=TA_RIGHT,
                        fontName="Helvetica-Bold",
                    ),
                ),
            ]
        )
    tbl = Table(rows, colWidths=[15 * mm, None, 25 * mm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#fbe8e6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEABOVE", (0, 0), (-1, 0), 1, HexColor("#b04a3a")),
                ("LINEBELOW", (0, -1), (-1, -1), 1, HexColor("#b04a3a")),
            ]
        )
    )
    flow.append(tbl)
    return flow


# ---------- custom flowables ----------


class _GradeTile(Flowable):
    """Large colored rectangle containing a single grade letter."""

    def __init__(self, grade: str, width: float, height: float) -> None:
        super().__init__()
        self.grade = grade
        self.width = width
        self.height = height

    def wrap(self, avail_w: float, avail_h: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        color = GRADE_COLORS.get(self.grade, GRADE_COLORS["C"])
        c.setFillColor(color)
        c.roundRect(0, 0, self.width, self.height, 4 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 40)
        # Vertically center the letter within the tile.
        text_y = (self.height - 40 * 0.72) / 2
        c.drawCentredString(self.width / 2, text_y, self.grade)


class _ScoreBar(Flowable):
    """Horizontal bar showing a 1–10 score, green→amber→red heatmap."""

    def __init__(self, score: int, width: float, height: float) -> None:
        super().__init__()
        self.score = max(1, min(10, int(score)))
        self.width = width
        self.height = height

    def wrap(self, avail_w: float, avail_h: float) -> tuple[float, float]:
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(INK_100)
        c.roundRect(0, 0, self.width, self.height, self.height / 2, fill=1, stroke=0)
        fill = _score_color(self.score)
        c.setFillColor(fill)
        filled_w = self.width * (self.score / 10.0)
        if filled_w > 0:
            c.roundRect(0, 0, filled_w, self.height, self.height / 2, fill=1, stroke=0)


# ---------- helpers ----------


def _score_color(s: int) -> colors.Color:
    if s >= 8:
        return GRADE_COLORS["A+"]
    if s >= 6:
        return GRADE_COLORS["B+"]
    if s >= 5:
        return GRADE_COLORS["B"]
    if s >= 4:
        return GRADE_COLORS["C+"]
    if s >= 3:
        return GRADE_COLORS["D"]
    return GRADE_COLORS["F"]


def _escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
