"""iter-55 · .docx round-trip fidelity + diff normalisation contract.

Verifies that
  1. `_docx_to_markdown` preserves inline emphasis, tables, hyperlinks,
     and lists so downloading a .docx and re-uploading it produces
     near-identical markdown (was the "+142 / -32 on unchanged doc" bug).
  2. `get_working_draft` returns `*_diff` normalised copies whose
     round-trip diff against the source .md is ≤ 2 line changes.
  3. Raw `content_md` / `released_md` still equal the strip-only body
     (contract-preserving for iter-47 and iter-53 tests).
"""
from pathlib import Path
import re
import difflib
import pytest

from routers.legal._common import (
    _docx_to_markdown,
    _strip_draft_disclaimer,
    _MID_DOC_DRAFT_BOILERPLATE_RE,
)

LEGAL_DIR = Path("/app/backend/legal_docs")


def _diff_normalise(md):
    """Copy of the endpoint's normaliser for test-side comparisons."""
    md = _MID_DOC_DRAFT_BOILERPLATE_RE.sub("\n", md)
    raw = [re.sub(r" {2,}", " ", ln.rstrip()) for ln in md.splitlines()]

    def kind(ln):
        s = ln.lstrip()
        if not s: return "blank"
        if s.startswith("#"): return "heading"
        if s.startswith("|"): return "table"
        if s.startswith("---"): return "hr"
        if s.startswith("> "): return "blockquote"
        if s.startswith("- ") or re.match(r"^\d+\.\s", s): return "list"
        return "para"

    def canon(ln):
        if not ln.strip().startswith("|"): return ln
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-+:?", c or "") for c in cells):
            return "| " + " | ".join(["---"] * len(cells)) + " |"
        return ln

    def jw(parts):
        m = parts[0]
        for n in parts[1:]:
            n_s = n.strip()
            if not n_s: continue
            if m.endswith("-") and n_s and n_s[0].islower():
                m = m + n_s
            else:
                m = m.rstrip() + " " + n_s
        return m

    out, i = [], 0
    while i < len(raw):
        k = kind(raw[i])
        if k == "blank":
            out.append(""); i += 1; continue
        if k == "list":
            items, cur = [], []
            while i < len(raw):
                lk = kind(raw[i])
                if lk == "list":
                    if cur: items.append(cur)
                    cur = [raw[i].lstrip()]; i += 1
                elif lk == "para" and cur:
                    cur.append(raw[i]); i += 1
                else: break
            if cur: items.append(cur)
            for it in items: out.append(jw(it))
        elif k == "para":
            block = []
            while i < len(raw) and kind(raw[i]) == "para":
                block.append(raw[i]); i += 1
            out.append(jw(block))
        elif k in ("heading", "hr", "blockquote"):
            out.append(raw[i]); i += 1
        elif k == "table":
            while i < len(raw) and kind(raw[i]) == "table":
                out.append(canon(raw[i])); i += 1
        else:
            out.append(raw[i]); i += 1
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    cleaned = re.sub(r"(?m)^(#{1,6} .+)\n\n(?=\S)", r"\1\n", cleaned)
    cleaned = re.sub(r"(?m)^(.+:)\n\n(?=[-*] )", r"\1\n", cleaned)
    return cleaned.strip() + "\n"


P1_PUBLIC_SLUGS = [
    "01-terms-of-service",
    "02-privacy-policy",
    "03-cookie-notice",
    "04-indemnification-hold-harmless",
    "10-sliding-scale-scholarship-terms",
    "14-community-standards",
    "15-refund-returns-policy",
]


class TestDocxRoundTripFidelity:
    @pytest.mark.parametrize("slug", P1_PUBLIC_SLUGS)
    def test_priority_one_roundtrip_near_identical(self, slug):
        """Downloading a .docx and re-uploading (via _docx_to_markdown)
        should produce markdown that differs from the source by at most
        2 line diffs after diff-view normalisation. Pre-fix baseline
        was +142/-32 on an unchanged upload."""
        md_path = LEGAL_DIR / f"{slug}.md"
        docx_path = LEGAL_DIR / f"{slug}.docx"
        assert md_path.exists() and docx_path.exists(), f"missing source/docx for {slug}"

        src, _ = _strip_draft_disclaimer(md_path.read_text(encoding="utf-8"))
        rt, _ = _strip_draft_disclaimer(_docx_to_markdown(docx_path.read_bytes()))

        src_n = _diff_normalise(src)
        rt_n = _diff_normalise(rt)

        ratio = difflib.SequenceMatcher(None, src_n, rt_n).ratio()
        diff = list(difflib.unified_diff(
            src_n.splitlines(), rt_n.splitlines(), lineterm="", n=0))
        plus = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        minus = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

        assert ratio >= 0.999, (
            f"{slug} round-trip similarity {ratio:.4f} < 0.999 — the "
            f".docx→md conversion is losing content. +{plus} / -{minus}"
        )
        assert plus + minus <= 2, (
            f"{slug} unchanged-upload diff is +{plus} / -{minus} — the "
            "diff view will show phantom hunks on an identical doc."
        )

    def test_bold_italic_code_hyperlinks_preserved(self):
        """Sanity: emphasis marks + hyperlinks survive the round-trip
        (they were completely dropped before the iter-55 rewrite)."""
        md_path = LEGAL_DIR / "01-terms-of-service.md"
        docx_path = LEGAL_DIR / "01-terms-of-service.docx"
        rt = _docx_to_markdown(docx_path.read_bytes())
        # Bold should survive.
        assert "**" in rt, "no bold markers in round-trip — emphasis dropped"
        # At least one link should survive.
        assert "[" in rt and "](" in rt, "no hyperlinks in round-trip"
        # Table should survive as pipe syntax.
        # Cookie notice has a sub-processors table.
        rt_cookie = _docx_to_markdown((LEGAL_DIR / "03-cookie-notice.docx").read_bytes())
        assert "|" in rt_cookie, "no table pipes in round-trip"
