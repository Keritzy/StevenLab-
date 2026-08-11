"""
Evidence report generation (PDF via reportlab / HTML fallback).
Compiles case info, metadata, ELA findings, handwriting profile, OCR text,
and keyword triage into one dated, page-numbered report.
"""
from __future__ import annotations
import html
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, PageBreak)

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1x", parent=styles["Heading1"], fontSize=16,
                    spaceAfter=6, textColor=colors.HexColor("#1a1a2e"))
H2 = ParagraphStyle("H2x", parent=styles["Heading2"], fontSize=13,
                    spaceBefore=10, spaceAfter=4,
                    textColor=colors.HexColor("#16213e"))
BODY = ParagraphStyle("BodyX", parent=styles["BodyText"], fontSize=10,
                      leading=14)
SMALL = ParagraphStyle("SmallX", parent=BODY, fontSize=8, textColor=colors.grey)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(inch, 0.5 * inch,
                      f"Handwriting Forensics Studio — {doc.page}")
    canvas.restoreState()


def _kv_table(rows: list[tuple]) -> Table:
    t = Table([[Paragraph(f"<b>{k}</b>", SMALL), Paragraph(str(v), SMALL)]
               for k, v in rows], colWidths=[2.0 * inch, 4.4 * inch])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white,
                                              colors.HexColor("#f4f4f8")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def build_pdf(report_data: dict, out_path: str):
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.8 * inch, bottomMargin=0.8 * inch,
                            title="Handwriting Forensics Report",
                            author="Handwriting Forensics Studio")
    story = []

    story.append(Paragraph("HANDWRITING FORENSICS REPORT", H1))
    story.append(Paragraph(
        f"Case: {html.escape(report_data['case_id'])} &nbsp;|&nbsp; "
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;|&nbsp; "
        f"Examiner: {html.escape(report_data.get('examiner', '—'))}", SMALL))
    story.append(Spacer(1, 6))

    # ---- 1. case + file metadata
    story.append(Paragraph("1. Exhibit &amp; File Metadata", H2))
    meta = report_data["metadata"]
    rows = [("Filename", meta["filename"]),
            ("Format / Mode", f"{meta['format']} ({meta['mode']})"),
            ("Dimensions", meta["dimensions"]),
            ("Size", f"{meta['size_bytes']:,} bytes"),
            ("DPI", meta["dpi"]),
            ("File modified", meta["created_mtime"]),
            ("SHA-256", meta["hashes"]["sha256"])]
    for k, v in meta.get("exif", {}).items():
        rows.append((f"EXIF: {k}", v))
    story.append(_kv_table(rows))

    # ---- 2. OCR
    story.append(PageBreak())
    story.append(Paragraph("2. Extracted Text (OCR)", H2))
    ocr = report_data["ocr"]
    story.append(_kv_table([
        ("Languages used", ocr["langs_used"]),
        ("Mean confidence", f"{ocr['mean_conf']}%"),
        ("Minimum word confidence", f"{ocr['min_conf']}%"),
    ]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(html.escape(ocr["text"][:6000] or "(no text found)")
                           .replace("\n", "<br/>"), BODY))

    # keyword triage
    tri = report_data.get("triage", {})
    if tri:
        story.append(Paragraph("Keyword Triage", H2))
        cat_rows = []
        for cat, terms in tri.get("categories", {}).items():
            cat_rows.append((cat.upper(), ", ".join(terms)))
        if cat_rows:
            story.append(_kv_table(cat_rows))
        story.append(Paragraph(
            f"<b>Triage priority: {tri.get('priority', 'NONE')} "
            f"(score {tri.get('score', 0)})</b>", BODY))

    # ---- 3. handwriting profile
    prof = report_data.get("handwriting", {})
    if prof:
        story.append(PageBreak())
        story.append(Paragraph("3. Handwriting Profile", H2))
        rows = []
        for key, nice in [("zones", "Zone distribution (U/M/L)"),
                          ("slant", "Slant angle"),
                          ("baseline", "Baseline trend"),
                          ("pressure", "Pen pressure"),
                          ("stroke", "Stroke width"),
                          ("spacing", "Spacing"),
                          ("size", "Letter size")]:
            r = prof.get(key)
            if r:
                rows.append((nice, r.get("interpretation", "—")))
        if rows:
            story.append(_kv_table(rows))
        if prof.get("flags"):
            story.append(Paragraph("Investigative flags:", H2))
            for f in prof["flags"]:
                story.append(Paragraph(f"• {html.escape(f)}", BODY))

    # ---- 4. image exhibits
    story.append(PageBreak())
    story.append(Paragraph("4. Image Exhibits", H2))
    for title, path in report_data.get("exhibits", []):
        try:
            img = Image(path, width=5.5 * inch,
                        height=5.5 * inch * 0.66)
            img.hAlign = "CENTER"
            story.append(Paragraph(f"<b>{html.escape(title)}</b>", BODY))
            story.append(img)
            story.append(Spacer(1, 8))
        except Exception:
            pass

    # ---- 5. conclusions
    story.append(PageBreak())
    story.append(Paragraph("5. Examiner Conclusions", H2))
    for c in report_data.get("conclusions", []):
        story.append(Paragraph(f"• {html.escape(c)}", BODY))
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "This report is generated by automated forensic tools and must be "
        "reviewed by a qualified forensic document examiner before use in "
        "evidence.", SMALL))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def build_html(report_data: dict, out_path: str):
    """Simple self-contained HTML report (works without reportlab)."""
    esc = html.escape
    parts = [f"""<html><head><meta charset="utf-8"><title>{esc(report_data['case_id'])}</title>
<style>body{{font-family:sans-serif;margin:2em;line-height:1.5}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #999;padding:6px;font-size:13px}}
th{{background:#16213e;color:#fff}}h2{{color:#16213e;border-bottom:2px solid #16213e;padding-bottom:4px}}
img{{max-width:90%;border:1px solid #ccc;margin:6px 0}}</style></head><body>
<h1>HANDWRITING FORENSICS REPORT</h1>
<p><b>Case:</b> {esc(report_data['case_id'])} &nbsp;
<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;
<b>Examiner:</b> {esc(report_data.get('examiner','—'))}</p>"""]

    meta = report_data["metadata"]
    rows = [("Filename", meta["filename"]), ("Format", meta["format"]),
            ("Dimensions", meta["dimensions"]),
            ("Size", f"{meta['size_bytes']:,} bytes"),
            ("SHA-256", meta["hashes"]["sha256"])]
    for k, v in meta.get("exif", {}).items():
        rows.append((f"EXIF {k}", v))
    parts.append("<h2>1. Exhibit &amp; File Metadata</h2><table>")
    for k, v in rows:
        parts.append(f"<tr><th>{esc(k)}</th><td>{esc(str(v))}</td></tr>")
    parts.append("</table>")

    ocr = report_data["ocr"]
    parts.append(f"<h2>2. Extracted Text</h2><p><b>Languages:</b> "
                 f"{esc(ocr['langs_used'])} &nbsp; <b>Mean conf:</b> "
                 f"{ocr['mean_conf']}%</p><pre>{esc(ocr['text'][:8000])}</pre>")

    tri = report_data.get("triage", {})
    if tri.get("categories"):
        parts.append("<h2>Keyword Triage</h2><table>")
        for cat, terms in tri["categories"].items():
            parts.append(f"<tr><th>{esc(cat.upper())}</th>"
                         f"<td>{esc(', '.join(terms))}</td></tr>")
        parts.append("</table>")
        parts.append(f"<p><b>Priority:</b> {tri.get('priority')} "
                     f"(score {tri.get('score')})</p>")

    prof = report_data.get("handwriting", {})
    if prof:
        parts.append("<h2>3. Handwriting Profile</h2><table>")
        for k, r in prof.items():
            if k == "flags":
                continue
            if isinstance(r, dict) and "interpretation" in r:
                parts.append(f"<tr><th>{esc(k)}</th>"
                             f"<td>{esc(r['interpretation'])}</td></tr>")
        parts.append("</table>")
        if prof.get("flags"):
            parts.append("<h3>Investigative flags</h3><ul>" +
                         "".join(f"<li>{esc(f)}</li>" for f in prof["flags"]) +
                         "</ul>")

    parts.append("<h2>4. Image Exhibits</h2>")
    for title, path in report_data.get("exhibits", []):
        try:
            with open(path, "rb") as f:
                import base64
                b64 = base64.b64encode(f.read()).decode()
            ext = path.rsplit(".", 1)[-1].lower()
            mime = "png" if ext == "png" else "jpeg"
            parts.append(f"<p><b>{esc(title)}</b><br>"
                         f'<img src="data:image/{mime};base64,{b64}"></p>')
        except Exception:
            pass

    parts.append("<h2>5. Examiner Conclusions</h2><ul>" +
                 "".join(f"<li>{esc(c)}</li>"
                         for c in report_data.get("conclusions", [])) +
                 "</ul>")
    parts.append("<p style='color:#666;font-size:12px'>Automated forensic "
                 "output — requires review by a qualified examiner.</p></body></html>")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
