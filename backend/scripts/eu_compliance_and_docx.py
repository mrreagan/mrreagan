"""Add an EU-compliance addendum to every draft + convert all .md drafts and
the counsel briefing to .docx with clickable hyperlinks.

Also regenerates the counsel briefing itself with a new "EU Compliance
Considerations" section and links each §8 instrument to its specific draft
download URL.

Run: python /app/backend/scripts/eu_compliance_and_docx.py
"""
import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

LEGAL_DIR = Path(__file__).resolve().parent.parent / "legal_docs"
PROD_BASE = "https://birthright.live"
DRAFT_DL_BASE = f"{PROD_BASE}/api/legal/docs"

# -------------------- EU Compliance addendum (appended to every .md) --------

EU_ADDENDUM = """
---

## EU / UK Compliance Addendum

This document was drafted with EU / UK regulatory alignment in mind. Where
this document conflicts with mandatory rights of an EU or UK resident, the
mandatory local rules prevail. In particular:

- **GDPR (EU) 2016/679 and UK GDPR** apply to processing of personal data
  of individuals in the EEA and UK. Where Birthright is the controller,
  the lawful bases relied on are: (i) contract necessity, (ii) legitimate
  interests (balanced by opt-out), (iii) consent (marketing and non-
  essential cookies), and (iv) legal obligation.
- **ePrivacy Directive (2002/58/EC as amended)** applies to cookies and
  similar tracking. Non-essential cookies require prior opt-in consent.
- **EU Consumer Rights Directive (2011/83/EU)** — EU/UK consumers have
  a 14-day right of withdrawal on distance sales of goods and most
  digital services. Where a workshop or digital product has been fully
  performed with the consumer's prior consent, the right may be lost.
- **Digital Services Act (Regulation 2022/2065)** applies to online
  intermediaries offering services in the EU; Birthright's community
  features (posts, DMs, disputes) fall within scope. A single point of
  contact is designated at eu-contact@birthright.live.
- **EU AI Act (Regulation 2024/1689)** applies to providers and deployers
  of AI systems affecting EU users. Birthright's AI features (Help
  Assistant, image generation, image captioning) are labeled as AI-
  assisted and are not used for automated decisions with legal effect.
- **Data transfers out of the EEA/UK/CH** rely on the EU Standard
  Contractual Clauses (2021/914) and the UK International Data Transfer
  Addendum, with a transfer-impact assessment on file for each sub-
  processor.
- **Data Protection Officer (DPO)** — Birthright will designate a DPO
  once threshold criteria under GDPR Art. 37 are met. Contact:
  dpo@birthright.live.
- **DSAR window** — subject access, rectification, erasure, portability,
  and objection requests are responded to within **30 days** (extendable
  by 60 days for complex requests) at privacy@birthright.live.
- **Supervisory authority** — EU/UK residents may lodge a complaint with
  their local supervisory authority; a list is available at
  https://edpb.europa.eu/about-edpb/about-edpb/members_en (EU) and
  https://ico.org.uk (UK).
- **VAT** — Where Birthright's EU B2C digital-service or goods sales
  cross applicable thresholds, VAT registration (One-Stop-Shop or
  country-by-country) will be completed.
"""


def append_eu_addendum():
    added = 0
    for p in sorted(LEGAL_DIR.glob("[0-9][0-9]-*.md")):
        text = p.read_text()
        if "EU / UK Compliance Addendum" in text:
            continue
        p.write_text(text + EU_ADDENDUM)
        added += 1
        print(f"  + EU addendum → {p.name}")
    return added


# --------------------- Markdown → docx converter (lightweight) --------------

def _add_hyperlink(paragraph, url, text):
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    h = OxmlElement("w:hyperlink"); h.set(qn("r:id"), r_id)
    r = OxmlElement("w:r"); rPr = OxmlElement("w:rPr")
    c = OxmlElement("w:color"); c.set(qn("w:val"), "0563C1"); rPr.append(c)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single"); rPr.append(u)
    r.append(rPr)
    t = OxmlElement("w:t"); t.text = text; t.set(qn("xml:space"), "preserve")
    r.append(t); h.append(r); paragraph._p.append(h)


URL_RE = re.compile(r"https?://[^\s)\]<>\"]+")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
CODE_RE = re.compile(r"`([^`]+)`")


def _inline(paragraph, text):
    i, tokens = 0, []
    while i < len(text):
        cands = []
        for rx, k in ((URL_RE, "url"), (BOLD_RE, "bold"), (CODE_RE, "code")):
            m = rx.search(text, i)
            if m: cands.append((m.start(), m.end(), k, m))
        if not cands:
            tokens.append(("t", text[i:])); break
        cands.sort(key=lambda x: x[0])
        s, e, k, m = cands[0]
        if s > i: tokens.append(("t", text[i:s]))
        tokens.append((k, m)); i = e
    for k, v in tokens:
        if k == "t":
            paragraph.add_run(v)
        elif k == "url":
            u = v.group(0).rstrip(".,;:")
            _add_hyperlink(paragraph, u, u)
            tr = v.group(0)[len(u):]
            if tr: paragraph.add_run(tr)
        elif k == "bold":
            r = paragraph.add_run(v.group(1)); r.bold = True
        elif k == "code":
            content = v.group(1)
            m = re.fullmatch(r"(?:(POST|GET|PUT|PATCH|DELETE)\s+)?(/(?:api/)?[a-zA-Z0-9_\-/*{}:]+)", content)
            if m:
                if m.group(1):
                    r = paragraph.add_run(m.group(1) + " "); r.font.name = "Consolas"; r.font.size = Pt(10)
                path = m.group(2).replace("/*", "").replace("{id}", "").replace("{slug}", "")
                _add_hyperlink(paragraph, f"{PROD_BASE}{path}", m.group(2))
            else:
                r = paragraph.add_run(content); r.font.name = "Consolas"; r.font.size = Pt(10)


def _join_wrapped_line(parts):
    """Join a list of soft-wrapped source lines. If a line ends with `-`
    and the next line starts lowercase, treat as intra-word wrap
    (`print-on-` + `demand` → `print-on-demand`); otherwise
    space-separate. Symmetric with _diff_normalise in
    routers/legal/working_drafts.py."""
    merged = parts[0]
    for nxt in parts[1:]:
        nxt_s = nxt.strip()
        if not nxt_s:
            continue
        if merged.endswith("-") and nxt_s and nxt_s[0].islower():
            merged = merged + nxt_s
        else:
            merged = merged.rstrip() + " " + nxt_s
    return merged


def md_to_docx(md_path: Path, docx_path: Path, doc_title: str = None):
    from docx.enum.text import WD_LINE_SPACING
    doc = Document()
    for s in doc.sections:
        # 1-inch margins on all four sides — matches Word's default
        # letter layout and gives counsel a familiar reading width.
        s.top_margin = s.bottom_margin = Inches(1.0)
        s.left_margin = s.right_margin = Inches(1.0)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    # Explicit single spacing on the Normal style (Word's default is
    # `Multiple 1.15` which reads spongy on legal briefs). No paragraph
    # spacing-before/after either — the .md structure carries the rhythm.
    pf = style.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.space_before = Pt(0)
    pf.space_after = Pt(6)   # small gap between paragraphs; no double-space

    text = md_path.read_text()
    # Normalise cosmetic whitespace before parsing: collapse runs of two
    # or more spaces (not at line start — indent-sensitive) down to one,
    # and strip trailing whitespace from every line. Keeps the visible
    # copy tighter and prevents the diff view from tripping over
    # invisible cosmetic drift.
    _norm_lines = []
    for _ln in text.splitlines():
        _stripped_r = _ln.rstrip()
        # Preserve leading whitespace (indentation), collapse
        # internal runs of >=2 spaces down to a single space.
        _lead = _stripped_r[:len(_stripped_r) - len(_stripped_r.lstrip(" "))]
        _rest = _stripped_r[len(_lead):]
        _rest = re.sub(r" {2,}", " ", _rest)
        _norm_lines.append(_lead + _rest)
    text = "\n".join(_norm_lines)
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        strip = line.strip()

        # Blank line / horizontal rule
        if strip == "" or strip == "---":
            if strip == "---":
                doc.add_paragraph()
            i += 1
            continue

        # Blockquote
        if strip.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.2)
            r = p.add_run(strip[2:])
            r.italic = True
            r.font.color.rgb = RGBColor(0x7C, 0x53, 0x16)
            i += 1
            continue

        # Headings
        if strip.startswith("### "):
            doc.add_heading(strip[4:], level=3); i += 1; continue
        if strip.startswith("## "):
            doc.add_heading(strip[3:], level=2); i += 1; continue
        if strip.startswith("# "):
            doc.add_heading(strip[2:], level=1); i += 1; continue

        # Table — grab the whole block right here and render in place
        if strip.startswith("|"):
            tblock = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tblock.append(lines[i].strip())
                i += 1
            rows = []
            for r_ in tblock:
                cells = [c.strip() for c in r_.strip("|").split("|")]
                if all(re.fullmatch(r":?-+:?", c or "") for c in cells):
                    continue  # separator row
                rows.append(cells)
            if not rows:
                continue
            w = max(len(r) for r in rows)
            t = doc.add_table(rows=len(rows), cols=w)
            t.style = "Light Grid Accent 1"
            for ri, row in enumerate(rows):
                for ci in range(w):
                    cell = t.rows[ri].cells[ci]
                    cell.text = ""
                    p = cell.paragraphs[0]
                    if ci < len(row):
                        _inline(p, row[ci])
                    if ri == 0:
                        for run in p.runs:
                            run.bold = True
            doc.add_paragraph()
            continue

        # Bullet — collect continuation lines (subsequent lines that
        # start with 2+ spaces of indent) into the same list item so
        # the .docx round-trip doesn't break the list.
        if strip.startswith("- "):
            item_parts = [strip[2:]]
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("  ") and nxt.strip() and not nxt.strip().startswith("- "):
                    item_parts.append(nxt.strip())
                    i += 1
                else:
                    break
            p = doc.add_paragraph(style="List Bullet")
            _inline(p, _join_wrapped_line(item_parts))
            continue

        # Numbered — same continuation handling.
        m = re.match(r"^(\d+)\.\s+(.*)$", strip)
        if m:
            item_parts = [m.group(2)]
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("  ") and nxt.strip() and not re.match(r"^\d+\.\s+", nxt.strip()):
                    item_parts.append(nxt.strip())
                    i += 1
                else:
                    break
            p = doc.add_paragraph(style="List Number")
            _inline(p, _join_wrapped_line(item_parts))
            continue

        # Plain paragraph — merge consecutive non-empty lines into ONE
        # Word paragraph so soft-wrap columns in the source .md don't
        # produce multi-paragraph docx (and, downstream, false-positive
        # diff hunks on the round-trip).
        para_parts = [strip]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            nxt_s = nxt.strip()
            if not nxt_s:
                break
            # Any new block-opener kicks us out of the current paragraph.
            if (nxt_s.startswith("#") or nxt_s.startswith("- ") or
                nxt_s.startswith("|") or nxt_s.startswith("> ") or
                nxt_s == "---" or re.match(r"^\d+\.\s+", nxt_s)):
                break
            para_parts.append(nxt_s)
            i += 1
        # Join with intra-word-hyphen awareness (symmetric with
        # _diff_normalise in working_drafts.py).
        merged = _join_wrapped_line(para_parts)
        p = doc.add_paragraph()
        _inline(p, merged)

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(docx_path))


# --------------------- Build every .docx --------------------------------

def build_all_docx():
    built = []
    for md in sorted(LEGAL_DIR.glob("[0-9][0-9]-*.md")):
        docx = md.with_suffix(".docx")
        md_to_docx(md, docx)
        built.append(docx)
        print(f"  → {docx.name}  ({docx.stat().st_size // 1024} KB)")
    return built


# --------------------- Update counsel briefing --------------------------

EU_BLOCK_IN_BRIEFING = """
---

## 4a. EU / UK Compliance Considerations (added Feb 2026)

All draft agreements have been generated with EU/UK alignment in mind and
carry an EU/UK Compliance Addendum. The concrete implications for the
platform:

- **GDPR/UK-GDPR** apply to any EEA/UK data subject. Lawful bases mapped:
  contract necessity, legitimate interests (with opt-out), consent
  (marketing / non-essential cookies), legal obligation.
- **Cookie consent (ePrivacy)** — a consent banner is required before
  non-essential cookies fire. Currently: banner not implemented; only
  strictly-necessary cookies are set (Cloudflare, Stripe at checkout).
- **14-day right of withdrawal (Consumer Rights Directive 2011/83/EU)**
  needs to appear in the Refund & Returns Policy for EU consumers and
  the workshop registration flow.
- **Digital Services Act (Reg. 2022/2065)** — community features are in
  scope. Designate a single point of contact `eu-contact@birthright.live`
  and publish a transparency report annually if traffic thresholds are
  crossed.
- **EU AI Act (Reg. 2024/1689)** — AI Help Assistant and AI image
  generation are labeled as AI-assisted. Not used for automated
  decisions with legal effect. Transparency notice is already present in
  the Terms of Service draft §9.
- **International data transfers** rely on the 2021 SCCs + UK IDTA.
  Every sub-processor DPA (§5) must incorporate these where applicable.
- **DPO** — designate `dpo@birthright.live` when the threshold criteria
  in GDPR Art. 37 are met (systematic large-scale monitoring or large-
  scale processing of special-category data).
- **EU VAT** — evaluate One-Stop-Shop registration for cross-border B2C
  sales of digital services (workshops, subscriptions) and physical
  goods.
- **Supervisory authority** — publish the right of EU/UK residents to
  lodge complaints with local supervisory authorities.

---

## 8b. Draft documents — direct download links (added Feb 2026)

The 21 instruments listed in §8 now have first-draft representative
documents available for counsel to review. Every draft is admin-only and
downloadable via the doc-shelf at `/admin/legal-docs`. Direct links:
"""


def _briefing_direct_link_block():
    from _manifest import DRAFT_LEGAL_DOCS  # type: ignore  # local import
    # Use the PUBLIC drafts endpoint so counsel can click without an admin
    # login. The endpoint is safe to expose because every draft is labelled
    # "AI-generated first draft — not legal advice" both top and bottom.
    out = ["| # | Draft | Category | Public download |", "|---|---|---|---|"]
    for i, d in enumerate(DRAFT_LEGAL_DOCS, 1):
        slug = d["slug"]
        url = f"{PROD_BASE}/api/legal/drafts/{slug}"
        out.append(f"| {i} | **{d['display_name']}** | {d['category']} | {url} |")
    return "\n".join(out)


def rebuild_briefing():
    src = LEGAL_DIR / "LEGAL_BRIEFING_FOR_COUNSEL.md"
    docx = LEGAL_DIR / "LEGAL_BRIEFING_FOR_COUNSEL.docx"
    text = src.read_text()

    # Insert / refresh the EU block right after §4 (Data & Privacy)
    if "EU / UK Compliance Considerations" not in text:
        insertion_point = text.find("## 5. Third-Party Integrations")
        if insertion_point > 0:
            text = text[:insertion_point] + EU_BLOCK_IN_BRIEFING + "\n" + text[insertion_point:]

    # Strip any stale §8b table then re-append a fresh one with public links.
    text = re.sub(
        r"\n\n\| # \| Draft \| Category \|.*?(?=\n##|\Z)",
        "",
        text,
        flags=re.DOTALL,
    )
    import sys
    sys.path.insert(0, str(LEGAL_DIR))
    table = _briefing_direct_link_block()
    # Prefix with a small heading so it renders as its own section, not raw pipes.
    section = "\n\n## 8b. Draft documents — public download links\n\n" + table + "\n"
    if "## 8b. Draft documents" not in text:
        text += section
    else:
        text = re.sub(
            r"## 8b\. Draft documents.*?(?=\n##|\Z)",
            section.lstrip("\n"),
            text,
            flags=re.DOTALL,
        )

    src.write_text(text)
    md_to_docx(src, docx)
    print(f"\nRebuilt {docx.name}  ({docx.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    print("=== 1. Adding EU compliance addendum to drafts ===")
    n = append_eu_addendum()
    print(f"  ({n} drafts updated)\n")
    print("=== 2. Building .docx for each draft ===")
    build_all_docx()
    print("\n=== 3. Rebuilding counsel briefing (.md + .docx) with EU section ===")
    rebuild_briefing()
    print("\nDone.")
