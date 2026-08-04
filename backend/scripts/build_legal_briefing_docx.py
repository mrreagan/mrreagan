"""Generate the Legal Briefing for Counsel as a clean .docx.

Reads the raw briefing text embedded in this script (kept next to the .md
source under /app/memory/) and writes a formatted Word document with:

  * A cover header + version metadata
  * A clickable table of contents (§ links)
  * Every http/https URL rendered as a real Word hyperlink
  * Every in-app path (e.g. `/legal/indemnification`) rendered as a clickable
    hyperlink to the production URL (https://birthright.live + path)
  * Every "instrument to draft" in §8 linked to /admin/legal-docs where the
    counsel-returned draft will be uploaded (or to the existing placeholder
    if one already exists)
  * Proper Word tables (not markdown pipes)
  * Heading styles for §, §.x, and callouts

Output: /app/backend/legal_docs/LEGAL_BRIEFING_FOR_COUNSEL.docx
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor, Inches

SRC = Path(__file__).resolve().parent.parent / "legal_docs" / "LEGAL_BRIEFING_FOR_COUNSEL.md"
OUT = Path(__file__).resolve().parent.parent / "legal_docs" / "LEGAL_BRIEFING_FOR_COUNSEL.docx"

PROD_BASE = "https://birthright.live"

# Instruments in §8 → where the eventual counsel-returned draft will live once
# uploaded. Everything routes through the admin doc-shelf we already built.
DRAFT_TARGET = f"{PROD_BASE}/admin/legal-docs"


# ------------------------------------------------------------------ helpers ---

def add_hyperlink(paragraph, url: str, text: str, color: str = "0563C1", underline: bool = True):
    """Insert a real Word hyperlink into a paragraph. python-docx doesn't expose
    hyperlinks natively so we drop down to the OOXML level."""
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), color)
    rPr.append(c)
    if underline:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(u)
    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


URL_RE = re.compile(r"https?://[^\s)\]<>\"]+", re.IGNORECASE)
# Match backtick-wrapped in-app paths like `/legal/indemnification` or
# `/admin/legal/agreements`. Also matches `POST /api/...` inside backticks.
PATH_RE = re.compile(r"`(/(?:api/)?[a-zA-Z0-9_\-/*{}:]+)`")
CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def render_inline(paragraph, text: str):
    """Render a line of text into `paragraph`, converting URLs, `code`, and
    **bold** to proper Word runs / hyperlinks."""
    # We walk the string, alternating between plain text and matches.
    tokens = []
    i = 0
    while i < len(text):
        # Find the next match of any pattern from position i.
        candidates = []
        for pattern, kind in ((URL_RE, "url"), (BOLD_RE, "bold"), (CODE_RE, "code")):
            m = pattern.search(text, i)
            if m:
                candidates.append((m.start(), m.end(), kind, m))
        if not candidates:
            tokens.append(("text", text[i:]))
            break
        candidates.sort(key=lambda x: x[0])
        start, end, kind, m = candidates[0]
        if start > i:
            tokens.append(("text", text[i:start]))
        tokens.append((kind, m))
        i = end

    for kind, val in tokens:
        if kind == "text":
            paragraph.add_run(val)
        elif kind == "url":
            url = val.group(0).rstrip(".,;:")
            add_hyperlink(paragraph, url, url)
            trailing = val.group(0)[len(url):]
            if trailing:
                paragraph.add_run(trailing)
        elif kind == "bold":
            run = paragraph.add_run(val.group(1))
            run.bold = True
        elif kind == "code":
            content = val.group(1)
            # If it looks like an in-app path, hyperlink it to prod.
            path_match = re.fullmatch(r"(POST |GET |PUT |PATCH |DELETE )?(/(?:api/)?[a-zA-Z0-9_\-/*{}:]+)", content)
            if path_match:
                verb = path_match.group(1) or ""
                path = path_match.group(2)
                # Skip API asterisk-globs like /admin/disputes/* → link to base
                link_path = path.replace("/*", "").replace("{id}", "").replace("{slug}", "").replace("{dispute_id}", "").replace("{key}", "")
                url = f"{PROD_BASE}{link_path}"
                if verb:
                    r = paragraph.add_run(verb)
                    r.font.name = "Consolas"
                    r.font.size = Pt(10)
                add_hyperlink(paragraph, url, path, color="0563C1")
            else:
                run = paragraph.add_run(content)
                run.font.name = "Consolas"
                run.font.size = Pt(10)


# --------------------------------------------------------------- doc build ---

def build():
    text = SRC.read_text()
    doc = Document()

    # Page setup
    for section in doc.sections:
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)

    # Base font
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # ---- Title block ----
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run("Birthright Foundation — Legal Briefing for Counsel")
    run.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = RGBColor(0x1A, 0x24, 0x24)

    meta = doc.add_paragraph()
    meta.paragraph_format.space_after = Pt(2)
    r = meta.add_run("Prepared for: outside counsel forming the entity and drafting agreements.")
    r.italic = True

    meta2 = doc.add_paragraph()
    meta2.paragraph_format.space_after = Pt(2)
    r = meta2.add_run("Prepared by: platform engineering (technical scoping only — not legal analysis).")
    r.italic = True

    meta3 = doc.add_paragraph()
    r = meta3.add_run("Version: February 2026. Production URL: ")
    r.italic = True
    add_hyperlink(meta3, PROD_BASE, PROD_BASE)

    # Callout
    cal = doc.add_paragraph()
    cal.paragraph_format.left_indent = Inches(0.15)
    cal.paragraph_format.space_before = Pt(6)
    cal.paragraph_format.space_after = Pt(12)
    r = cal.add_run(
        "How to use this document: each section describes what exists in the "
        "product today, then flags the concrete legal instruments we believe "
        "need to be drafted, reviewed, or updated. URLs point to live pages "
        "counsel can inspect directly. Nothing in this document is legal "
        "advice; it is a technical dossier."
    )
    r.italic = True

    # ---- Counsel fast-path summary (embedded from 00a-counsel-user-guide) ----
    # Give counsel the billable-time-minimising workflow up front so they
    # never feel obliged to log into the platform for a normal review.
    fast_h = doc.add_heading("Counsel Fast Path — Minimise Your Billable Time", level=1)
    fast_h.paragraph_format.space_before = Pt(18)
    p = doc.add_paragraph()
    r = p.add_run(
        "The cheapest workflow for you is entirely paper-based: download the "
        "two .docx files we sent you, redline in Word with Track Changes, "
        "and email them to legal@birthright.live. Birthright's Executive "
        "Director does every platform click. You never need to sign in to "
        "the site."
    )
    r.italic = True

    p = doc.add_paragraph()
    p.add_run("Push these functions to Birthright's admin so they do not appear on your bill:").italic = True
    for line in [
        "Transcribing your redlines into the platform (~30s per redline).",
        "Applying accepted / rejected roundtrip decisions.",
        "Marking documents as counsel-ratified after your ratification email.",
        "Rebuilding the counsel briefing bundle after edits.",
        "Ticking off the manual review checklist and recording your initials.",
    ]:
        b = doc.add_paragraph(style="List Bullet")
        b.add_run(line)

    p = doc.add_paragraph()
    p.add_run("Please do these personally — they are legal work, not clerical work:").italic = True
    for line in [
        "Substantive legal analysis of every draft.",
        "Rewording of the proposed replacement text in each redline.",
        "The final one-line ratification email per document.",
        "Advice on licensing, insurance, and dispute-jurisdiction choices.",
    ]:
        b = doc.add_paragraph(style="List Bullet")
        b.add_run(line)

    p = doc.add_paragraph()
    p.add_run(
        "The full per-function fast-path table (redline, roundtrip, ratify, "
        "revoke, checklist, activity log, change-log) lives in the standalone "
        "Counsel User Guide — file '00a-counsel-user-guide.docx'."
    ).italic = True
    doc.add_paragraph()  # spacer

    # ---- Parse markdown-ish source into rendered doc ----
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip the source's own front-matter / redundant TOC lines we've
        # already rendered above.
        if stripped.startswith("_Prepared") or stripped.startswith("_Version"):
            i += 1
            continue
        if stripped.startswith("> How to use this document"):
            i += 1
            continue
        if stripped == "" or stripped == "---":
            if stripped == "---":
                doc.add_paragraph()  # small break
            i += 1
            continue

        # Headings
        if stripped.startswith("### "):
            h = doc.add_heading(stripped[4:].strip(), level=3)
            h.paragraph_format.space_before = Pt(10)
            i += 1
            continue
        if stripped.startswith("## "):
            h = doc.add_heading(stripped[3:].strip(), level=2)
            h.paragraph_format.space_before = Pt(14)
            i += 1
            continue
        if stripped.startswith("# "):
            # Already used doc title
            i += 1
            continue

        # Tables — collect consecutive markdown table lines starting with |
        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            # Drop the separator row (---|---)
            rows = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                # Skip separator rows
                if all(re.fullmatch(r":?-+:?", c) for c in cells):
                    continue
                rows.append(cells)
            if not rows:
                continue
            width = max(len(r) for r in rows)
            tbl = doc.add_table(rows=len(rows), cols=width)
            tbl.style = "Light Grid Accent 1"
            for r_idx, row in enumerate(rows):
                for c_idx in range(width):
                    cell = tbl.rows[r_idx].cells[c_idx]
                    cell.text = ""
                    p = cell.paragraphs[0]
                    if c_idx < len(row):
                        render_inline(p, row[c_idx])
                    if r_idx == 0:
                        for run in p.runs:
                            run.bold = True
            doc.add_paragraph()  # spacing after table
            continue

        # Markdown image — ![alt](path). Embed the referenced file as an inline
        # picture. Path is relative to the .md source directory.
        img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if img_match:
            alt_text, img_path = img_match.group(1), img_match.group(2)
            resolved = (SRC.parent / img_path).resolve()
            if resolved.exists():
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                try:
                    run.add_picture(str(resolved), width=Inches(4.5))
                except Exception as e:
                    p.add_run(f"[image embed failed: {alt_text} — {e}]").italic = True
                # Caption (small italic beneath the image)
                if alt_text:
                    cap = doc.add_paragraph()
                    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    cap.paragraph_format.space_after = Pt(10)
                    cr = cap.add_run(alt_text)
                    cr.italic = True
                    cr.font.size = Pt(9)
                    cr.font.color.rgb = RGBColor(0x5C, 0x6B, 0x6B)
            else:
                # Image file missing — render alt text so the doc still builds.
                p = doc.add_paragraph()
                p.add_run(f"[Image not found on disk: {img_path} — alt: {alt_text}]").italic = True
            i += 1
            continue

        # Bullet list
        if stripped.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            render_inline(p, stripped[2:])
            i += 1
            continue

        # Numbered list (1. 2. …)
        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            p = doc.add_paragraph(style="List Number")
            content = m.group(2)
            # If this is one of the §8 "instruments" list items, link the
            # instrument name to the admin doc shelf.
            bold_first = re.match(r"^\*\*([^*]+)\*\*(.*)$", content)
            if bold_first:
                name = bold_first.group(1)
                rest = bold_first.group(2)
                add_hyperlink(p, DRAFT_TARGET, name, color="0563C1")
                render_inline(p, rest)
            else:
                render_inline(p, content)
            i += 1
            continue

        # Plain paragraph
        p = doc.add_paragraph()
        render_inline(p, stripped)
        i += 1

    # ---- Save ----
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
