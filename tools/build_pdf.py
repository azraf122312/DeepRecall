"""Generate the DeepRecall learning guide as a PDF.

    py tools/build_pdf.py

Produces  DeepRecall_Learning_Guide.pdf  in the project root. Uses reportlab
(Platypus) only -- no external fonts, no network. The guide explains the
project and, specifically, how DeepRecall turns *learning materials*
(textbooks, lecture notes, slide decks, docs) into a queryable, cited tutor.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "DeepRecall_Learning_Guide.pdf"

# ---------------------------------------------------------------- palette
INK = colors.HexColor("#1b2733")
ACCENT = colors.HexColor("#2563eb")
ACCENT2 = colors.HexColor("#0ea5e9")
MUTED = colors.HexColor("#5b6b7b")
SOFT = colors.HexColor("#eef3fb")
CODE_BG = colors.HexColor("#0f172a")
CODE_FG = colors.HexColor("#e2e8f0")
RULE = colors.HexColor("#cbd5e1")
WARN_BG = colors.HexColor("#fff7ed")
WARN_BD = colors.HexColor("#fb923c")

# ---------------------------------------------------------------- styles
ss = getSampleStyleSheet()


def style(name, **kw):
    base = kw.pop("parent", ss["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


H1 = style("H1", fontName="Helvetica-Bold", fontSize=22, leading=26,
           textColor=INK, spaceAfter=6, spaceBefore=10)
H2 = style("H2", fontName="Helvetica-Bold", fontSize=14, leading=18,
           textColor=ACCENT, spaceBefore=16, spaceAfter=6)
H3 = style("H3", fontName="Helvetica-Bold", fontSize=11.5, leading=15,
           textColor=INK, spaceBefore=10, spaceAfter=3)
BODY = style("Body", fontSize=10, leading=15, textColor=INK, spaceAfter=7,
             alignment=TA_LEFT)
LEAD = style("Lead", fontSize=11.5, leading=17, textColor=MUTED, spaceAfter=10)
BULLET = style("Bullet", parent=BODY, leftIndent=14, bulletIndent=2, spaceAfter=3)
SMALL = style("Small", fontSize=8.5, leading=11, textColor=MUTED)
CODE = style("Code", fontName="Courier", fontSize=8.5, leading=12,
             textColor=CODE_FG, backColor=CODE_BG, leftIndent=6, rightIndent=6,
             spaceBefore=4, spaceAfter=8, borderPadding=(8, 8, 8, 8))
QUOTE = style("Quote", fontSize=11, leading=16, textColor=INK, leftIndent=12,
              rightIndent=8, spaceBefore=4, spaceAfter=10, fontName="Helvetica-Oblique")
TH = style("TH", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.white)
TD = style("TD", fontSize=9, leading=12.5, textColor=INK)
TDB = style("TDB", fontName="Helvetica-Bold", fontSize=9, leading=12.5, textColor=INK)
COVER_T = style("CoverT", fontName="Helvetica-Bold", fontSize=34, leading=38,
                textColor=colors.white, alignment=TA_CENTER)
COVER_S = style("CoverS", fontSize=13, leading=18, textColor=colors.HexColor("#dbeafe"),
                alignment=TA_CENTER)


def cell(text, st=TD):
    return Paragraph(text, st)


def info_table(rows, col_widths, header=True):
    data = [[cell(c, TH if (header and r == 0) else TD) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1),
         [colors.white, SOFT]),
    ]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), ACCENT)]
    t.setStyle(TableStyle(cmds))
    return t


def callout(title, body, bg=SOFT, bd=ACCENT):
    inner = [Paragraph(f"<b>{title}</b>", style("ct", fontName="Helvetica-Bold",
                                                fontSize=10, textColor=bd, spaceAfter=3)),
             Paragraph(body, BODY)]
    t = Table([[inner]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LINEBEFORE", (0, 0), (0, -1), 3, bd),
    ]))
    return t


# ---------------------------------------------------------------- page frames
def on_cover(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(INK)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h * 0.58, w, h * 0.42, fill=1, stroke=0)
    canvas.setFillColor(ACCENT2)
    canvas.rect(0, h * 0.575, w, 6, fill=1, stroke=0)
    canvas.restoreState()


def on_content(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, h - 1.5 * cm, w - 2 * cm, h - 1.5 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, h - 1.35 * cm, "DeepRecall - Learning Guide")
    canvas.drawRightString(w - 2 * cm, h - 1.35 * cm, "Structure-aware Hybrid RAG")
    canvas.line(2 * cm, 1.4 * cm, w - 2 * cm, 1.4 * cm)
    canvas.drawString(2 * cm, 1.0 * cm, "v0.1.0")
    canvas.drawRightString(w - 2 * cm, 1.0 * cm, f"Page {doc.page - 1}")
    canvas.restoreState()


def build():
    doc = BaseDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title="DeepRecall - Learning Guide", author="DeepRecall",
    )
    full = Frame(2 * cm, 2 * cm, A4[0] - 4 * cm, A4[1] - 4 * cm, id="full")
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[full], onPage=on_cover),
        PageTemplate(id="Content", frames=[full], onPage=on_content),
    ])

    s = []  # story

    # ----- COVER
    s += [Spacer(1, 3.2 * cm),
          Paragraph("DeepRecall", COVER_T),
          Spacer(1, 4 * mm),
          Paragraph("How a structure-aware RAG turns your learning<br/>"
                    "materials into a queryable, cited tutor", COVER_S),
          Spacer(1, 7.5 * cm),
          Paragraph("A learning &amp; architecture guide", style("cl", parent=COVER_S, fontSize=11)),
          Paragraph("Document Cognition Layer  -  v0.1.0", style("cl2", parent=COVER_S, fontSize=9))]
    s += [NextPageTemplate("Content"), PageBreak()]

    # ----- 1. THE IDEA
    s += [Paragraph("1.  The core idea", H1),
          Paragraph("Most RAG fails because it treats documents as flat text. "
                    "Documents have structure, hierarchy, and implicit "
                    "relationships - and so should the system that reads them.", QUOTE)]
    s += [Paragraph("DeepRecall is a <b>Document Cognition Layer</b>. Instead of "
                    "slicing your material into equal-sized blind chunks, it first "
                    "<i>understands</i> the document - its sections, tables, code, "
                    "warnings and how they relate - then retrieves and answers with "
                    "that structure intact, always citing its sources.", BODY)]
    s += [Paragraph("Why this matters for learning materials", H2),
          Paragraph("Textbooks, lecture notes, slide decks and lab manuals are "
                    "<b>highly structured</b>: chapters, definitions, worked "
                    "examples, step-by-step procedures, comparison tables, and "
                    "cautionary notes. A naive RAG shreds that structure and gives "
                    "you confident-sounding but ungrounded answers. DeepRecall keeps "
                    "the structure, so studying becomes faster and more trustworthy.", BODY)]
    s += [info_table([
        ["Study problem", "How DeepRecall helps"],
        ["\"Where was that defined?\"", "Definition blocks are detected as a chunk type and cited to the exact section."],
        ["\"Give me the steps.\"", "Procedures are recognised and boosted for how-to questions, returned in order."],
        ["\"Which option is better?\"", "Comparison tables are preserved whole and boosted for decision questions."],
        ["\"What are the gotchas?\"", "Warning/caution blocks are surfaced explicitly as caveats."],
        ["\"Is this actually in my notes?\"", "If nothing relevant is found, it refuses instead of hallucinating."],
    ], [5.4 * cm, 11.0 * cm])]
    s += [Spacer(1, 4 * mm),
          callout("The promise",
                  "Point DeepRecall at a folder of your course materials and ask "
                  "questions in plain language. Every answer comes back grounded in, "
                  "and cited to, the exact section of the exact file it came from - "
                  "so you can trust it and go read the source.")]
    s += [PageBreak()]

    # ----- 2. PIPELINE OVERVIEW
    s += [Paragraph("2.  How it works, end to end", H1),
          Paragraph("Three stages turn raw study material into a grounded answer.", LEAD)]
    s += [_flow_table()]
    s += [Paragraph("2.1  Ingestion - reading like a student, not a shredder", H2),
          Paragraph("DeepRecall parses each file into a tree (Title -> Section -> "
                    "Subsection -> Paragraph / List / Table / Code), enriches it with "
                    "named entities and an <i>intent</i> per section, then chunks by "
                    "<b>meaning</b> rather than token count.", BODY),
          Paragraph("Semantic chunk types it recognises:", H3)]
    s += [info_table([
        ["Chunk type", "What it captures in your notes"],
        ["Definition", "A term and its explanation."],
        ["Procedure", "Numbered / how-to steps."],
        ["Comparison", "A table weighing options."],
        ["Code example", "Code paired with its surrounding explanation."],
        ["FAQ", "A question and its answer."],
        ["Warning", "A caution, gotcha or \"never do this\"."],
    ], [4.3 * cm, 12.1 * cm])]
    s += [Spacer(1, 3 * mm),
          callout("Why chunk by meaning?",
                  "A fixed 500-token window can split a definition from its term, or "
                  "a step 3 from step 4. Semantic chunks keep each idea whole, so "
                  "retrieval returns a complete, usable answer instead of a fragment.")]
    s += [PageBreak()]

    s += [Paragraph("2.2  Retrieval - four lenses, fused", H2),
          Paragraph("The same question is asked of four complementary indices, then "
                    "their rankings are merged. No single method wins every time, so "
                    "DeepRecall combines their strengths.", BODY)]
    s += [info_table([
        ["Index", "Strength", "Good for"],
        ["Dense (vectors)", "Meaning / paraphrase", "\"explain in other words\""],
        ["Sparse (BM25)", "Exact keywords", "specific terms, acronyms"],
        ["Graph (entities)", "Relationships", "\"what depends on X\""],
        ["Structural", "Hierarchy", "parent section, siblings"],
    ], [4.0 * cm, 5.2 * cm, 7.2 * cm])]
    s += [Paragraph("The four ranked lists are merged with <b>Reciprocal Rank "
                    "Fusion</b> (RRF), which combines rankings fairly even when their "
                    "score scales differ wildly:", BODY)]
    s += [Paragraph('score(d) = &#931;<sub>i</sub> 1 / (k + rank<sub>i</sub>(d)),'
                    "  with k = 60", style("formula", parent=BODY,
                    fontName="Helvetica-Oblique", alignment=TA_CENTER,
                    backColor=SOFT, borderPadding=8, spaceAfter=9))]
    s += [Paragraph("Then two finishing touches:", H3),
          Paragraph("<b>Intent-aware structural boost</b> - a how-to question lifts "
                    "<i>procedure</i> chunks (+0.10); a troubleshooting question lifts "
                    "<i>warning</i> chunks (+0.20); a decision question lifts "
                    "<i>comparison</i> tables (+0.15).", BULLET, bulletText="-"),
          Paragraph("<b>Cross-encoder rerank</b> - the top candidates are re-scored by "
                    "jointly reading the question and each chunk, for sharper ordering.",
                    BULLET, bulletText="-")]
    s += [PageBreak()]

    s += [Paragraph("2.3  Generation - grounded, cited, honest", H2),
          Paragraph("DeepRecall assembles the winning chunks (plus a parent-section "
                    "summary and related siblings, de-duplicated) and produces an "
                    "answer where every claim points back to a numbered source.", BODY)]
    s += [info_table([
        ["Feature", "What it gives a learner"],
        ["Source grounding", "Every claim carries a [n] citation to a real section."],
        ["Confidence score", "An honest signal of how well the corpus covered you."],
        ["\"I don't know\"", "Refuses when nothing relevant is found - no bluffing."],
        ["Caveat surfacing", "Warnings are pulled out so you don't miss them."],
    ], [4.6 * cm, 11.8 * cm])]
    s += [Spacer(1, 2 * mm),
          callout("Standard RAG vs DeepRecall",
                  "Standard RAG: \"Here's what I found...\"  &nbsp;&nbsp;|&nbsp;&nbsp;  "
                  "DeepRecall: \"Based on 3 sources, the recommended approach is X, "
                  "with caveat Y from [warning block]\" - and it shows you exactly "
                  "where X and Y came from.")]
    s += [PageBreak()]

    # ----- 3. WORKED EXAMPLE
    s += [Paragraph("3.  A worked example", H1),
          Paragraph("Imagine your study folder holds two notes: a Kubernetes "
                    "operations guide and an API-gateway reference. You ask:", BODY),
          Paragraph("\"How do I configure auto-scaling for the API gateway during "
                    "high traffic?\"", QUOTE)]
    s += [Paragraph("DeepRecall's trace", H3),
          Paragraph("intent = <b>how-to</b>&nbsp;&nbsp; entities = <b>[API Gateway]</b>",
                    style("tr", parent=CODE, backColor=SOFT, textColor=INK))]
    s += [info_table([
        ["Rank", "Chunk type", "Section", "Why it won"],
        ["1", "procedure", "API Gateway 3.2", "BM25 + dense + graph + how-to boost"],
        ["2", "procedure", "Kubernetes 4.2", "step list + how-to boost"],
        ["3", "code", "Kubernetes 4.2", "HPA YAML paired with its explanation"],
    ], [1.3 * cm, 2.7 * cm, 4.0 * cm, 8.4 * cm])]
    s += [Paragraph("The generated answer stitches these into ordered guidance, "
                    "then appends the caveat it found in section 4.4 - "
                    "\"never set minReplicas to 0 for a public gateway\" - and lists "
                    "all four sources. Confidence: 97%.", BODY)]
    s += [Spacer(1, 2 * mm),
          callout("Honesty check",
                  "Ask it \"How do I bake a sourdough loaf?\" against the same folder "
                  "and it refuses: no relevant sources. That refusal is a feature - "
                  "it is the difference between a study aid you can trust and one "
                  "that confidently misleads you the night before an exam.",
                  bg=WARN_BG, bd=WARN_BD)]
    s += [PageBreak()]

    # ----- 4. USING IT
    s += [Paragraph("4.  Using it on your own materials", H1)]
    s += [Paragraph("Three lines of Python turn a folder of notes into a tutor:", BODY),
          Paragraph(
              "from deeprecall import DeepRecall<br/><br/>"
              "rag = DeepRecall()<br/>"
              "rag.ingest_dir(\"my_course_notes\")     # .md / .txt / .html<br/>"
              "print(rag.query(\"summarise chapter 4's key formulas\").render())",
              CODE)]
    s += [Paragraph("Run the bundled demo", H3),
          Paragraph("py examples/demo.py        # full pipeline on a sample corpus<br/>"
                    "py -m pytest -q            # 6 tests", CODE)]
    s += [Paragraph("Runs anywhere, upgrades anywhere", H2),
          Paragraph("DeepRecall runs end-to-end with <b>zero heavy dependencies</b> "
                    "(pure-Python fallbacks for embeddings, BM25, the graph, reranking "
                    "and generation). Install optional backends and the same code "
                    "auto-upgrades - no rewrites.", BODY)]
    s += [info_table([
        ["Install", "Upgrades"],
        ["sentence-transformers", "Real semantic embeddings + cross-encoder rerank."],
        ["anthropic + API key", "Fluent LLM answers (claude-opus-4-8) vs extractive."],
        ["chromadb / neo4j / elasticsearch", "Production-scale vector / graph / keyword stores."],
        ["unstructured / layout models", "PDF & Word parsing with visual structure."],
    ], [5.3 * cm, 11.1 * cm])]
    s += [Spacer(1, 3 * mm),
          callout("Study-workflow ideas",
                  "&bull; Drop a semester of lecture notes into one folder and quiz "
                  "yourself with cited answers.<br/>"
                  "&bull; Ask \"what are the warnings/exceptions in chapter 6?\" to "
                  "build a gotchas list.<br/>"
                  "&bull; Ask decision questions to auto-extract comparison tables for "
                  "revision.<br/>"
                  "&bull; Trust the \"I don't know\" - it tells you where your notes "
                  "have gaps to fill.")]
    s += [Spacer(1, 5 * mm),
          Paragraph("Project: C:\\Users\\emona\\OneDrive\\Desktop\\DeepRecall"
                    "  -  MIT licensed  -  built as an extensible reference "
                    "implementation.", SMALL)]

    doc.build(s)
    return OUT


def _flow_table():
    def stage(n, title, sub):
        inner = [Paragraph(f"<b>{n}. {title}</b>",
                           style("fs", fontName="Helvetica-Bold", fontSize=10,
                                 textColor=colors.white, spaceAfter=2)),
                 Paragraph(sub, style("fsub", fontSize=8.3, leading=11,
                                      textColor=colors.HexColor("#dbeafe")))]
        return inner

    data = [[stage("1", "Ingestion", "parse -> enrich -> chunk by meaning"),
             stage("2", "Hybrid retrieval", "4 indices -> RRF -> boost -> rerank"),
             stage("3", "Generation", "grounded, cited, confidence-scored")]]
    t = Table(data, colWidths=[5.4 * cm, 5.5 * cm, 5.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), ACCENT),
        ("BACKGROUND", (1, 0), (1, 0), ACCENT2),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#0284c7")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEAFTER", (0, 0), (0, 0), 3, colors.white),
        ("LINEAFTER", (1, 0), (1, 0), 3, colors.white),
    ]))
    return t


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}  ({path.stat().st_size // 1024} KB)")
