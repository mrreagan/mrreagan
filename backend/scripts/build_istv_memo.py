"""Generate the ISTV Contract Analysis memo as a .docx.

One-off script — produces:
  /app/backend/legal_docs/22-istv-contract-analysis-memo.docx

Registers the doc in _manifest.py so the public download endpoint
(/api/legal/drafts/22-istv-contract-analysis-memo) serves it.

Run:
    cd /app/backend && python scripts/build_istv_memo.py
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor, Inches, Cm

LEGAL_DIR = Path(__file__).resolve().parent.parent / "legal_docs"
LEGAL_DIR.mkdir(exist_ok=True)
SLUG = "22-istv-contract-analysis-memo"
DISPLAY_NAME = "ISTV Contract — Full Text Review & Business Value Memo"
OUT_PATH = LEGAL_DIR / f"{SLUG}.docx"

BRAND_TEAL = RGBColor(0x0F, 0x24, 0x24)
BRAND_GOLD = RGBColor(0xC9, 0xA9, 0x61)
BRAND_MUTED = RGBColor(0x5C, 0x6B, 0x6B)
BRAND_WARN = RGBColor(0x8B, 0x45, 0x13)


def _set_cell_shading(cell, hex_color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def _add_border(paragraph, side: str = "bottom", color: str = "C9A961", size: str = "8") -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    b = OxmlElement(f"w:{side}")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), size)
    b.set(qn("w:space"), "1")
    b.set(qn("w:color"), color)
    p_bdr.append(b)
    p_pr.append(p_bdr)


def add_h1(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Georgia"
    run.font.size = Pt(24)
    run.font.color.rgb = BRAND_TEAL
    run.bold = True
    p.paragraph_format.space_after = Pt(6)
    _add_border(p, "bottom", color="C9A961", size="12")


def add_h2(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Georgia"
    run.font.size = Pt(16)
    run.font.color.rgb = BRAND_TEAL
    run.bold = True
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(4)


def add_h3(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(12)
    run.font.color.rgb = BRAND_WARN
    run.bold = True
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)


def add_body(doc: Document, text: str, italic: bool = False, muted: bool = False) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    # Inline bold ("**...**") + italic ("*...*") markdown
    tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            r = p.add_run(tok[2:-2])
            r.bold = True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            r = p.add_run(tok[1:-1])
            r.italic = True
        else:
            r = p.add_run(tok)
        r.font.name = "Calibri"
        r.font.size = Pt(11)
        if italic:
            r.italic = True
        if muted:
            r.font.color.rgb = BRAND_MUTED


def add_bullet(doc: Document, text: str, indent: float = 0.25) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(indent)
    p.paragraph_format.space_after = Pt(2)
    tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            r = p.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            r = p.add_run(tok[1:-1]); r.italic = True
        else:
            r = p.add_run(tok)
        r.font.name = "Calibri"
        r.font.size = Pt(11)


def add_callout(doc: Document, title: str, body: str, tint: str = "FBF3E4",
                title_color: RGBColor = BRAND_WARN) -> None:
    tbl = doc.add_table(rows=1, cols=1)
    tbl.autofit = True
    cell = tbl.rows[0].cells[0]
    _set_cell_shading(cell, tint)
    # Title
    p = cell.paragraphs[0]
    r = p.add_run(title)
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(11)
    r.font.color.rgb = title_color
    # Body
    p2 = cell.add_paragraph()
    r2 = p2.add_run(body)
    r2.font.name = "Calibri"
    r2.font.size = Pt(11)
    r2.font.color.rgb = BRAND_TEAL
    doc.add_paragraph()  # spacing


def add_quote(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(6)
    _add_border(p, "left", color="C9A961", size="18")
    r = p.add_run(text)
    r.italic = True
    r.font.name = "Georgia"
    r.font.size = Pt(11)
    r.font.color.rgb = BRAND_TEAL


def add_table(doc: Document, headers: list[str], rows: list[list[str]],
              col_widths: list[float] | None = None) -> None:
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = "Light List Accent 1"
    hdr = tbl.rows[0].cells
    for i, h in enumerate(headers):
        p = hdr[i].paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        _set_cell_shading(hdr[i], "0F2424")
        hdr[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    for row in rows:
        cells = tbl.add_row().cells
        for i, val in enumerate(row):
            p = cells[i].paragraphs[0]
            tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", val)
            for tok in tokens:
                if not tok:
                    continue
                if tok.startswith("**") and tok.endswith("**"):
                    r = p.add_run(tok[2:-2]); r.bold = True
                elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                    r = p.add_run(tok[1:-1]); r.italic = True
                else:
                    r = p.add_run(tok)
                r.font.name = "Calibri"
                r.font.size = Pt(10)
    if col_widths:
        for row in tbl.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()


# ============ Build ============
def build() -> Path:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)

    # Cover header
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run("BIRTHRIGHT FOUNDATION")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(9)
    r.font.color.rgb = BRAND_GOLD

    add_h1(doc, "ISTV Contract — Full Text Review\n& Business Value Memo")

    meta = doc.add_paragraph()
    meta.paragraph_format.space_after = Pt(2)
    for label, val in [
        ("Prepared by:", " Steely-eyed business & marketing advisor"),
        ("Persona:", " Advocating exclusively for Birthright's interests"),
        ("Date:", f" {datetime.utcnow().strftime('%B %d, %Y')}"),
        ("Distribution:", " Founders (James & Amanda Reagan), Legal Counsel (Ina), Advisory Team"),
    ]:
        rl = meta.add_run(label); rl.bold = True; rl.font.name = "Arial"; rl.font.size = Pt(10)
        rv = meta.add_run(val); rv.font.name = "Arial"; rv.font.size = Pt(10); rv.font.color.rgb = BRAND_MUTED
        meta.add_run("\n")

    add_body(doc, "**Scope:** (1) Does the actual contract text answer the questions we raised? "
                  "(2) Is $12k justified vs. $3–6k alternatives? "
                  "(3) Is Ina's 2-week entity formation timeline a dealbreaker?")

    # TL;DR
    add_callout(
        doc,
        title="TL;DR",
        body=(
            "The contract makes the deal materially WORSE than Mary's email suggested. It "
            "introduces four new red flags Mary did not mention. Value is unchanged from prior "
            "analysis. $12k is not justified. The 2-week entity timeline is not the dealbreaker "
            "— the contract itself is the dealbreaker. Ina's timeline is protecting you."
        ),
        tint="FBF3E4",
    )

    # ---------- Section 1 ----------
    add_h2(doc, "Section 1 — Does the Contract Answer Our Clarifying Questions?")

    add_h3(doc, "Partially resolved")
    add_table(
        doc,
        headers=["Ask", "Contract text", "Verdict"],
        rows=[
            ["Co-ownership in writing",
             "§2: \"A lifetime use license and co-ownership of your episode and all filmed content\"",
             "**In writing — but see contradiction below.**"],
            ["Lifetime commercial use",
             "§6: \"lifetime, royalty-free, non-transferable commercial use license\"",
             "Confirmed."],
            ["5-year hosting guarantee",
             "§5: \"remain published on at least one platform we own or control for a minimum of 5 years\"",
             "Confirmed."],
        ],
        col_widths=[1.8, 3.4, 1.6],
    )

    add_h3(doc, "The \"co-ownership\" is not what Mary implied")
    add_bullet(doc, "**§2 says \"co-ownership.\"** **§6 says \"commercial-use license.\"** "
                    "These clauses contradict each other, and §12 (Entire Agreement) does not resolve which controls.")
    add_bullet(doc, "**§6 Limitations kill the co-ownership value:** *\"You may not alter, resell, or "
                    "distribute the full episode for OTT or broadcast use without written permission. "
                    "You may not submit the episode to third-party streaming platforms without prior written approval.\"*")
    add_bullet(doc, "You \"co-own\" it but cannot put it on Netflix, Hulu, Amazon Prime, YouTube, "
                    "or anywhere else without ISTV's written permission. That is a license with severe "
                    "use restrictions, dressed up as ownership.")
    add_bullet(doc, "Under Florida contract law, ambiguity in a contract of adhesion generally cuts "
                    "against the drafter (ISTV) — **but litigating that costs more than the $12k fee.** "
                    "In practice, ISTV wins the interpretation.")

    add_h3(doc, "Four NEW red flags Mary did not disclose in her email")

    add_body(doc, "**8. §12 Entire Agreement clause voids Mary's entire email.**")
    add_quote(doc, "\"You acknowledge that you are not relying on any statement, promise, or representation "
                   "outside of this Agreement, including oral representations made by sales or enrollment personnel.\"")
    add_body(doc, "Every softening reassurance Mary sent — \"we always welcome a conversation,\" "
                  "\"we pride ourselves on cast members feeling great,\" \"risk not proportionately the same\" "
                  "— is legally worthless the moment you sign. Only the contract text matters.")

    add_body(doc, "**9. §11 has an anti-chargeback / attorney-fees weapon.**")
    add_quote(doc, "\"If you attempt to circumvent this process by challenging any bank or credit card "
                   "payment to ISTV LLC, ISTV will seek attorneys' fees and costs based on your wrongful challenge.\"")
    add_body(doc, "You cannot use a card dispute to recover funds if ISTV underperforms. Combined with §7 "
                  "(\"non-refundable\"), your money is trapped from the moment the wire clears.")

    add_body(doc, "**10. Class-action waiver + jury-trial waiver.**")
    add_quote(doc, "\"By signing, you waive the right to participate in a class action lawsuit against the "
                   "company and a trial by jury.\"")
    add_body(doc, "Individually arbitrated only, in Miami. If ISTV has systematically underdelivered to "
                  "1,000 cast members, you have no path to pool remedy.")

    add_body(doc, "**11. §9 3-year non-compete — broader than Mary framed it.**")
    add_quote(doc, "\"For 3 years… you agree not to create, operate, or own a rival streaming platform or "
                   "docuseries production business that substantially replicates our business model "
                   "(featuring entrepreneurs documentary-style productions).\"")
    add_body(doc, "Reasonable people would argue Birthright isn't in that business. But it is *adjacent* — "
                  "a couples/community platform that will inevitably produce founder stories, workshops, and "
                  "testimonial content. This clause is broad enough to be weaponized against future Birthright "
                  "content that \"features entrepreneurs\" in a \"documentary-style.\" Add the $100k "
                  "liquidated-damages provision for soliciting one contractor.")

    add_body(doc, "**12. §3 introduces surprise costs.**")
    add_body(doc, "\"$1,000 reshoot fee payable in advance\" if you show up \"fatigued, ill, or on "
                  "medication.\" The Production Company has \"sole and absolute discretion\" to make that "
                  "call. Read plainly: they can call you unfit, pocket the $12k, and charge $1k more for a reshoot.")

    add_h3(doc, "Not resolved")
    add_bullet(doc, "**No editorial takedown right.** §4 confirms ISTV has \"full editorial and creative "
                    "authority.\" You get one round of revisions on the storyline \"as long as they do not "
                    "totally change the content format/flow.\" You cannot pull the episode if it damages your brand.")
    add_bullet(doc, "**Non-reciprocal termination.** §8 lets ISTV terminate for a wide range of reasons "
                    "(past or pending criminal charges, \"misconduct\" including \"harassment, discrimination, "
                    "racism, sexism, or violent behavior\" — all at \"ISTV's sole discretion\") without refund. "
                    "You have no reciprocal termination right.")
    add_bullet(doc, "**No producer indemnity.** §8 makes you indemnify them; nothing runs the other direction.")
    add_bullet(doc, "**Personal-signature exposure.** Signature block asks for First Name / Last Name / Company / "
                    "Title. Company is a field, not a required entity execution. Mary's email confirmed she signs "
                    "individuals routinely. If James signs personally, personal liability follows.")

    # ---------- Section 2 ----------
    add_h2(doc, "Section 2 — Business Value: Does Anything Justify $12k?")

    add_h3(doc, "What you actually get for $12k")
    add_bullet(doc, "Half-day of filming in Miami — *fair market: $2–3k*")
    add_bullet(doc, "Pre-production script support — *fair market: $500–1k*")
    add_bullet(doc, "One 12–15 minute edited episode, one revision — *fair market: $3–5k*")
    add_bullet(doc, "Placement on ISTV Network app inside Roku / Apple TV / Amazon Fire TV — **not** as a "
                    "Prime Video original, but as a channel within those stores. *Fair market of a channel "
                    "slot: near-zero unless someone searches for the ISTV brand.*")
    add_bullet(doc, "Promotional trailer + social graphics + press release + IMDb-application help — *fair market: $500–1k*")
    add_body(doc, "**Fair-market rebuild cost: roughly $6–10k** if you hired a documentary house directly — "
                  "with full ownership, no non-compete, no class-action waiver, no perpetual license to your "
                  "likeness for their marketing, and full takedown rights.")

    add_h3(doc, "The premium ISTV charges is a credential premium")
    add_body(doc, "\"As seen on Amazon Prime / Roku / Apple TV\" — this is genuinely valuable **only** in these two use cases:")
    add_bullet(doc, "Sales/authority pages for high-ticket coaching or B2B services where prospects click a "
                    "logo bar and don't investigate.")
    add_bullet(doc, "Investor decks where a logo carousel adds surface-level credibility.")
    add_body(doc, "Neither is Birthright's primary conversion driver. Birthright converts on story, mission, "
                  "and human trust — not on Amazon Prime placement. **The credential premium is worth "
                  "$2–3k, not the ~$6k gap.**")

    add_h3(doc, "Did anything materially change since our prior analysis?")
    add_body(doc, "**No.** In fact three things got worse once we read the actual contract:")
    add_bullet(doc, "Mary's softening language is legally void (§12).")
    add_bullet(doc, "Chargebacks are booby-trapped (§11).")
    add_bullet(doc, "Non-compete is broader than a mid-market TV deal would ever require.")
    add_body(doc, "The only material positive from Mary's email — co-ownership — is contradicted by §6's "
                  "license framing and rendered practically meaningless by the OTT/streaming restrictions.")

    add_h3(doc, "Alternatives (all give you more control for less money)")
    add_table(
        doc,
        headers=["Option", "Estimated cost", "Ownership", "Editorial control", "Reach"],
        rows=[
            ["Direct documentary producer (2 quotes + LinkedIn outreach)", "$4–8k", "100% you", "Full", "You promote"],
            ["Podcast tour (5–8 mid-tier shows)", "$0–2k outreach", "100% you", "Full", "Comparable"],
            ["Targeted PR retainer (3 months, boutique agency)", "$9–12k", "N/A", "Full", "Higher DA backlinks"],
            ["Own docuseries — Birthright Films Ep. 1", "$6–10k", "100% you", "Full", "Owned distribution, no non-compete"],
            ["**ISTV**", "**$12k + $1k reshoot risk**", "**Contradicted**", "**ISTV has final say**", "**Undisclosed**"],
        ],
        col_widths=[2.4, 1.1, 1.1, 1.2, 1.4],
    )

    add_h3(doc, "The invisible costs of signing")
    add_bullet(doc, "**Opportunity cost of the non-compete** — 3 years locked out of a category Birthright could legitimately enter.")
    add_bullet(doc, "**Perpetual license to your likeness** for ISTV to promote their show (§8: \"You grant "
                    "us a perpetual license to use your submitted content for editorial, promotional, and "
                    "broadcast purposes related to the show\"). Your face becomes marketing for their brand, forever.")
    add_bullet(doc, "**Chargeback trap** — if they underdeliver, you cannot recover funds by any normal consumer remedy.")
    add_bullet(doc, "**Sunk-cost trap on future upsells** — Mary already flagged \"guaranteed views are only "
                    "available in upgraded packages.\" Once you're $12k in, the next $5k feels rational.")

    # ---------- Section 3 ----------
    add_h2(doc, "Section 3 — Is Ina's 2-Week Entity Timeline the Dealbreaker?")
    add_body(doc, "**No. The contract is the dealbreaker.**")
    add_body(doc, "Consider what Ina's timeline actually reveals:")
    add_bullet(doc, "She's telling you it takes 2 weeks to properly form a company that shields you from personal liability.")
    add_bullet(doc, "Mary is telling you she can push the meeting \"a day or so.\"")
    add_bullet(doc, "The gap between those two numbers is the size of the manipulation.")
    add_body(doc, "A counterparty that respects your process gives you the two weeks. A counterparty that has "
                  "closing-quota pressure asks you to sign personally to lock in a \"preferred rate\" that is "
                  "almost certainly available whenever you're actually ready to buy.")

    add_h3(doc, "Test whether the \"preferred rate\" is real")
    add_body(doc, "Reply with the entity-formation timeline explicitly. One of three things happens:")
    add_bullet(doc, "**She holds the rate** → the pressure was theater. You proceed on your timeline.")
    add_bullet(doc, "**She raises the rate modestly** → she has some flexibility. You negotiate.")
    add_bullet(doc, "**She raises the rate significantly or walks** → she was closing on a manufactured "
                    "deadline. This is a gift. You saved $12k plus permanent contractual exposure.")
    add_body(doc, "Any outcome from that test is a win for Birthright.")

    # ---------- Recommendation ----------
    add_h2(doc, "Final Recommendation")
    add_callout(
        doc,
        title="Do not sign this contract.",
        body=(
            "The value is not there. The terms are worse than Mary's summary. The \"co-ownership\" is "
            "contradicted internally. The non-compete is broader than it needs to be. Mary explicitly refuses "
            "to redline."
        ),
        tint="F9E5E1",
        title_color=RGBColor(0x8B, 0x00, 0x00),
    )
    add_body(doc, "If your gut still wants the Amazon Prime logo:")
    add_bullet(doc, "Wait for entity formation (2 weeks — non-negotiable).")
    add_bullet(doc, "Underwrite 100% via sponsors first (Birthright's campaign flow is built for this).")
    add_bullet(doc, "Reply asking specifically: *\"Please point us to the clause that reconciles §2 (co-ownership) "
                    "with §6 (non-transferable license). We need those to align before signing.\"*")
    add_bullet(doc, "If she says \"we don't redline\" again, you have your answer.")

    add_h3(doc, "Best use of the $12k right now")
    add_body(doc, "Fund production of *Birthright Films Episode 1* — an owned docuseries pilot. Same "
                  "production quality, your ownership, your platform, your terms. Distribute it on your site, "
                  "YouTube, Vimeo OTT, and pitch it to Prime Video's Direct program (free submission) for the "
                  "exact same credential without any of the strings.")

    # ---------- Suggested reply ----------
    add_h2(doc, "Suggested Reply to Mary (Firm but Warm)")
    add_quote(doc,
              "Mary — thank you for the thorough walkthrough and for sending the contract. After a careful "
              "read alongside our legal counsel, we're going to pass at this time.\n\n"
              "Two things drove the decision: (a) our counsel confirmed entity formation will take at least "
              "two weeks and we're not comfortable signing personally, and (b) after reviewing §2, §6, §9, "
              "§11 and §12 in the actual contract, the terms don't align with what we're building at Birthright.\n\n"
              "We appreciate your time and the transparency of your reply. If ISTV ever offers a version of "
              "the agreement executed at the entity level with narrower non-compete language and reciprocal "
              "takedown rights, we'd be open to revisiting.\n\n"
              "— James & Amanda")

    add_body(doc, "This closes cleanly, leaves the door open only on your terms, and — critically — creates "
                  "a paper trail showing you declined for specific documented reasons. If ISTV comes back with "
                  "\"we can adjust,\" you will know the \"we don't redline\" posture was negotiable all along, "
                  "which itself is diagnostic.")

    # Disclaimer
    doc.add_paragraph()
    add_callout(
        doc,
        title="Confidentiality & Nature of This Memo",
        body=(
            "This memo is an internal business and strategic advisory document prepared for Birthright "
            "Foundation's founders and outside counsel. It is not a substitute for licensed legal advice. "
            "All contract clause interpretations should be independently verified by qualified counsel "
            "(Florida contract law applies). Distribute only to internal advisors and legal counsel."
        ),
        tint="F4F1EA",
        title_color=BRAND_MUTED,
    )

    doc.save(OUT_PATH)
    return OUT_PATH


def register_in_manifest() -> None:
    """Add this memo to the public download manifest if not already present."""
    manifest_fp = LEGAL_DIR / "_manifest.py"
    if not manifest_fp.exists():
        return
    txt = manifest_fp.read_text()
    if SLUG in txt:
        return
    entry = (
        f'    {{"slug": "{SLUG}", '
        f'"display_name": "{DISPLAY_NAME}", '
        f'"category": "Advisory memos"}},\n'
    )
    # Insert before closing "]"
    new_txt = txt.rstrip()
    if new_txt.endswith("]"):
        new_txt = new_txt[:-1].rstrip()
        if new_txt.endswith(","):
            new_txt = new_txt[:-1]
        new_txt = new_txt + ",\n" + entry + "]\n"
    manifest_fp.write_text(new_txt)


if __name__ == "__main__":
    out = build()
    register_in_manifest()
    print(f"Wrote: {out}")
    print(f"Public URL: /api/legal/drafts/{SLUG}")
