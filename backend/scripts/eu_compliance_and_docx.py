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


def md_to_docx(md_path: Path, docx_path: Path, doc_title: str = None):
    doc = Document()
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Inches(0.8)
        s.left_margin = s.right_margin = Inches(0.9)
    style = doc.styles["Normal"]; style.font.name = "Calibri"; style.font.size = Pt(11)

    text = md_path.read_text()
    lines = text.splitlines()
    for line in lines:
        strip = line.strip()
        if strip == "" or strip == "---":
            if strip == "---": doc.add_paragraph()
            continue
        if strip.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.2)
            r = p.add_run(strip[2:]); r.italic = True; r.font.color.rgb = RGBColor(0x7C, 0x53, 0x16)
            continue
        if strip.startswith("### "):
            doc.add_heading(strip[4:], level=3); continue
        if strip.startswith("## "):
            doc.add_heading(strip[3:], level=2); continue
        if strip.startswith("# "):
            h = doc.add_heading(strip[2:], level=1); continue
        if strip.startswith("|"):
            # inline table row — collect this and subsequent | lines
            # (handled below in a small loop by re-reading)
            pass
        if strip.startswith("- "):
            p = doc.add_paragraph(style="List Bullet"); _inline(p, strip[2:]); continue
        m = re.match(r"^(\d+)\.\s+(.*)$", strip)
        if m:
            p = doc.add_paragraph(style="List Number"); _inline(p, m.group(2)); continue
        p = doc.add_paragraph(); _inline(p, strip)

    # Simple table pass — collect any consecutive lines starting with |
    # and materialize them as tables at the end. (Kept simple; drafts use
    # tables sparingly.)
    tblock, in_tbl = [], False
    for line in lines:
        s = line.strip()
        if s.startswith("|"):
            in_tbl = True; tblock.append(s)
        else:
            if in_tbl and tblock:
                rows = [r for r in tblock if not re.fullmatch(r"\|(\s*:?-+:?\s*\|)+", r)]
                if rows:
                    parsed = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
                    w = max(len(r) for r in parsed)
                    t = doc.add_table(rows=len(parsed), cols=w); t.style = "Light Grid Accent 1"
                    for ri, row in enumerate(parsed):
                        for ci in range(w):
                            cell = t.rows[ri].cells[ci]; cell.text = ""
                            _inline(cell.paragraphs[0], row[ci] if ci < len(row) else "")
                            if ri == 0:
                                for r_ in cell.paragraphs[0].runs: r_.bold = True
                    doc.add_paragraph()
                tblock, in_tbl = [], False

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
    out = ["| # | Draft | Category | Download |", "|---|---|---|---|"]
    for i, d in enumerate(DRAFT_LEGAL_DOCS, 1):
        slug = d["slug"]
        key = f"draft-{slug}"
        url = f"{DRAFT_DL_BASE}/{key}"
        out.append(f"| {i} | **{d['display_name']}** | {d['category']} | {url} |")
    return "\n".join(out)


def rebuild_briefing():
    src = LEGAL_DIR / "LEGAL_BRIEFING_FOR_COUNSEL.md"
    docx = LEGAL_DIR / "LEGAL_BRIEFING_FOR_COUNSEL.docx"
    text = src.read_text()
    if "EU / UK Compliance Considerations" not in text:
        # Insert the EU block right after §4 (Data & Privacy)
        insertion_point = text.find("## 5. Third-Party Integrations")
        if insertion_point > 0:
            text = text[:insertion_point] + EU_BLOCK_IN_BRIEFING + "\n" + text[insertion_point:]

    # Append the draft table if not already present
    if "8b. Draft documents — direct download links" not in text:
        # need the manifest — import it via sys.path shim
        import sys
        sys.path.insert(0, str(LEGAL_DIR))
        table = _briefing_direct_link_block()
        text += "\n\n" + table + "\n"

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
