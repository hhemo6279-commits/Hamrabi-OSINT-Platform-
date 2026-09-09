"""PDF report generator — produces a professional investigation report with
executive summary, target, findings, evidence, sources, confidence, graph
summary and timeline."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import textwrap as _textwrap

from app.core.config import REPORT_DIR
from app.models.entities import Investigation
from app.modules.confidence import status_label


def _register_arabic_font() -> bool:
    """Register a system TTF that can render Arabic glyphs."""
    global _AR_FONT_REGISTERED
    if _AR_FONT_REGISTERED or pdfmetrics is None:
        return _AR_FONT_REGISTERED
    import os
    candidates = [
        os.environ.get("WINDIR", r"C:\Windows") + r"\Fonts\arial.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        os.environ.get("WINDIR", r"C:\Windows") + r"\Fonts\arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(ARABIC_FONT, path))
                _AR_FONT_REGISTERED = True
                return True
            except Exception:
                continue
    return False


def _ar(text: str) -> str:
    """Reshape + bidi-reorder an Arabic string for PDF display."""
    if not ARABIC_SHAPING or not text:
        return text or ""
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def _ap(text: str, styles, parent="Normal", size=9, text_color=None) -> Paragraph:
    """Render an Arabic paragraph with correct shaping + font."""
    if text_color is None:
        text_color = colors.HexColor("#c9a35a")
    body = _ar(text)
    if _register_arabic_font():
        body = f"<font name='{ARABIC_FONT}'>{body}</font>"
    return Paragraph(body, ParagraphStyle(
        name=f"Ar{id(text)}", parent=styles[parent], fontSize=size,
        alignment=2, textColor=text_color))

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    PDF_AVAILABLE = True
except ImportError:
    TTFont = None
    pdfmetrics = None
    PDF_AVAILABLE = False

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SHAPING = True
except ImportError:
    ARABIC_SHAPING = False

ARABIC_FONT = "ArabicFont"
_AR_FONT_REGISTERED = False


def generate_pdf(inv: Investigation) -> Path | None:
    if not PDF_AVAILABLE:
        return None

    path = REPORT_DIR / f"{inv.id}.pdf"

    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Muted", parent=styles["BodyText"], fontSize=8,
                              textColor=colors.HexColor("#666666")))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story = [
        Paragraph("ENKI — OSINT Investigation Report", styles["Title"]),
        _ap("منصة انكي — تقرير فحص استخباراتي", styles, parent="Title", size=14,
            text_color=colors.HexColor("#2e8b57")),
        Spacer(1, 4 * mm),
        Paragraph(f"Generated: {now}", styles["Muted"]),
        Paragraph(f"Investigation ID: <font name='Courier'>{inv.id}</font>",
                  styles["Muted"]),
        Paragraph(f"Target: <b>{escape(inv.raw_input)}</b>"
                  f"&nbsp;&nbsp;Type: <b>{inv.input_type}</b>", styles["Normal"]),
        Spacer(1, 4 * mm),
    ]
    if ARABIC_SHAPING:
        story.append(Paragraph("ملخص تنفيذي", styles["Heading1"]))
        ar_sum = (
            f"هذا التقرير يلخص تحقيقا في الاستخبارات مفتوحة المصدر على الهدف "
            f"{_ar(inv.raw_input)} من النوع {_ar(inv.input_type)}. "
            f"استخرج النظام {_ar(str(len(inv.entities)))} كيانا وجال {_ar(str(len(inv.findings)))} "
            f"دليلا من مصادر عامة، وبنى {_ar(str(len(inv.relationships)))} علاقة. "
            "جميع البيانات من مصادر عامة مصرح بها فقط.")
        story.append(_ap(ar_sum, styles))
    story += [
        Paragraph("Executive Summary", styles["Heading1"]),
        Paragraph(_exec_summary(inv), styles["BodyText"]),
        PageBreak(),
        Paragraph("Entities", styles["Heading1"]),
        Spacer(1, 2 * mm),
        Paragraph("Findings", styles["Heading1"]),
    ]
    _entities_table(inv, story, styles)
    for f in inv.findings:
        story.append(_finding_block(f, styles))
        story.append(Spacer(1, 6 * mm))

    if inv.ai_summary or inv.ai_classification:
        story.append(PageBreak())
        story.append(Paragraph("AI Analysis", styles["Heading1"]))
        if inv.ai_classification:
            story.append(Paragraph(f"<b>Classification:</b> {escape(inv.ai_classification)}",
                                   styles["BodyText"]))
        if inv.ai_summary:
            story.append(Paragraph(escape(inv.ai_summary), styles["BodyText"]))

    social = _social_section(inv)
    if social:
        story.append(PageBreak())
        story.append(Paragraph("Social Media Analysis", styles["Heading1"]))
        story.append(Paragraph(social, styles["BodyText"]))

    if inv.findings or inv.entities:
        story.append(PageBreak())
        story.append(Paragraph("Timeline", styles["Heading1"]))
        story.extend(_timeline_block(inv))
        story.append(Spacer(1, 4 * mm))

    if inv.relationships:
        story.append(PageBreak())
        story.append(Paragraph("Correlation Graph", styles["Heading1"]))
        story.append(Paragraph("Relationships between entities (visual graph in UI):",
                               styles["BodyText"]))
        rows = [["Source", "Relation", "Target", "Confidence"]]
        for r in inv.relationships:
            s = next((e.value for e in inv.entities if e.id == r.source_id), r.source_id)
            t = next((e.value for e in inv.entities if e.id == r.target_id), r.target_id)
            rows.append([escape(s), escape(r.relation), escape(t), f"{r.confidence:.0%}"])
        table = Table(rows, colWidths=[50 * mm, 45 * mm, 50 * mm, 30 * mm])
        table.setStyle(_table_style())
        story.append(table)

    story.append(Paragraph("Sources & Confidence", styles["Heading1"]))
    story.append(Paragraph(_source_summary(inv), styles["BodyText"]))

    doc.build(story)
    return path


def _timeline_block(inv) -> list:
    rows = [["Step", "Action", "Detail"]]
    step = 1
    rows.append([str(step), "Input received", escape(inv.raw_input)])
    step += 1
    for e in inv.entities:
        rows.append([str(step), f"Entity extracted ({e.type})", escape(e.value)])
        step += 1
    for f in inv.findings:
        rows.append([str(step), f"Collection via {f.source}",
                     escape(f.key)[:80]])
        step += 1
    for r in inv.relationships:
        rows.append([str(step), f"Correlation: {r.relation}",
                     f"{r.source_id[:8]} → {r.target_id[:8]} ({r.confidence:.0%})"])
        step += 1
    rows.append([str(step), "Report generated", inv.created_at[:19].replace("T", " ")])
    table = Table(rows, colWidths=[20 * mm, 55 * mm, 100 * mm])
    table.setStyle(_table_style())
    return [table]


def _finding_block(f, styles) -> Paragraph:
    text = f"<b>[{f.source.upper()}]</b> {escape(f.key)} — "
    text += f"confidence <b>{f.confidence:.0%}</b> ({status_label(f.confidence)}), "
    text += f"{f.evidence_count} evidence, query <font name='Courier'>{escape(f.query)}</font>"
    body = _textwrap.shorten(repr(f.value), width=300, placeholder="...")
    return Paragraph(text + f"<br/><font size=8 color='#444444'>{escape(body)}</font>",
                     styles["BodyText"])


def _entities_table(inv, story, styles):
    rows = [["Entity", "Type", "ID"]]
    for e in inv.entities:
        rows.append([escape(e.value), e.type, f"<font name='Courier'>{escape(e.id)}</font>"])
    table = Table(rows, colWidths=[70 * mm, 45 * mm, 60 * mm])
    table.setStyle(_table_style())
    story.append(table)


def _table_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])


def _exec_summary(inv) -> str:
    n_entity = len(inv.entities)
    n_findings = len(inv.findings)
    n_links = len(inv.relationships)
    top = max((f.confidence for f in inv.findings), default=0.0)
    return (
        f"This report summarizes an OSINT investigation on <b>{escape(inv.raw_input)}</b> "
        f"({inv.input_type}). The pipeline extracted <b>{n_entity}</b> entities, collected "
        f"<b>{n_findings}</b> evidence-recorded findings from public sources, and built "
        f"<b>{n_links}</b> correlation links. Aggregate confidence: <b>{top:.0%}</b>. "
        "All data comes from public, authorised sources only."
    )


def _social_section(inv) -> str:
    rows = []
    for f in inv.findings:
        if f.source != "social":
            continue
        value = f.value or {}
        handle = value.get("handle")
        analysis = value.get("analysis") or {}
        counts = analysis.get("counts") or {}
        rows.append(
            f"<li><b>@{escape(handle)}</b> - total comments "
            f"{analysis.get('total', 0)} (positive {counts.get('positive', 0)}, "
            f"negative {counts.get('negative', 0)}, neutral "
            f"{counts.get('neutral', 0)}), {analysis.get('good_ratio', 0):.0%} "
            "positive.</li>")
        for p in (value.get("platforms") or []):
            rows.append(
                f"<li>{escape(p.get('platform', ''))} - exists={p.get('exists')}, "
                f"publisher={escape(p.get('publisher') or '-')}, "
                f"location={escape(p.get('location') or '-')}</li>")
    if not rows:
        return ""
    return "<b>Comment analysis</b><ul>" + "".join(rows) + "</ul>"


def _source_summary(inv) -> str:
    counts: dict[str, int] = {}
    for f in inv.findings:
        counts[f.source] = counts.get(f.source, 0) + 1
    if not counts:
        return "No findings recorded in this investigation."
    rows = ["<ul>"]
    for src, n in sorted(counts.items(), key=lambda x: -x[1]):
        rows.append(f"<li><b>{escape(src)}</b>: {n} finding(s)</li>")
    rows.append("</ul>")
    return "".join(rows)


def escape(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))