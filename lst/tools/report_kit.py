"""Shared report kit: one content model rendered to Markdown, DOCX and PDF.

Why this file exists
--------------------
The project must deliver, for every exercise, a bilingual (Persian / English)
report in three formats (Markdown, DOCX, PDF) with the *same* content.  Writing
three files by hand guarantees they drift apart, so this kit renders all three
from a single structured content model.

Layout model
------------
A report is an explicit list of ``Page`` objects.  Every page is terminated with
a hard page break, and the builder *verifies* that the estimated height of the
page content fits inside the printable area (see ``estimate_height``).  Because
the same geometry, font, font sizes and spacing are used for the DOCX and the
PDF, the page count reported by the PDF writer is also the page count of the
DOCX file.  That makes the "20-40 pages per report" requirement verifiable
instead of guessed.

Persian text handling
---------------------
* DOCX  : the run is flagged as complex script (``<w:cs/>``) and the paragraph
  is marked RTL (``<w:bidi/>``) so Word/Uniscribe performs the contextual
  shaping and the bidi reordering itself.  Text is stored as logical Unicode.
* PDF   : reportlab has no shaper, so text is pre-processed with
  ``arabic_reshaper`` + ``python-bidi`` before drawing.
* Markdown: stored as logical Unicode (GitHub renders it correctly).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from fontTools.ttLib import TTFont

# --------------------------------------------------------------------------
# Geometry and typography (identical for DOCX and PDF)
# --------------------------------------------------------------------------

PAGE_W_CM, PAGE_H_CM = 21.0, 29.7          # A4 portrait
MARGIN_X_CM, MARGIN_TOP_CM, MARGIN_BOT_CM = 1.9, 1.7, 1.7
TEXT_W_CM = PAGE_W_CM - 2 * MARGIN_X_CM
TEXT_H_CM = PAGE_H_CM - MARGIN_TOP_CM - MARGIN_BOT_CM

CM = 28.3464567                              # pt per cm

FS_COVER_TITLE = 27
FS_COVER_SUB = 14
FS_PAGE_TITLE = 16
FS_H1 = 13.5
FS_H2 = 12.0
FS_BODY = 11.0
FS_TABLE = 9.6
FS_CODE = 9.0
FS_CAPTION = 9.0

LH_BODY = 1.30
LH_BULLET = 1.24
LH_TITLE = 1.18

SPACE_AFTER_TITLE = 9
SPACE_AFTER_H1 = 6
SPACE_AFTER_H2 = 4
SPACE_AFTER_BLOCK = 5
BULLET_INDENT_CM = 0.55

# Safety factor applied when estimating whether a page fits.  Real Word
# line-breaking differs slightly from ours; 1.06 absorbs that difference.
SAFETY = 1.06

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONT_REGULAR = os.path.join(FONTS_DIR, "Vazirmatn-400.ttf")
FONT_BOLD = os.path.join(FONTS_DIR, "Vazirmatn-700.ttf")
FONT_NAME = "Vazirmatn"

# --------------------------------------------------------------------------
# Persian shaping (PDF / matplotlib only)
# --------------------------------------------------------------------------

import arabic_reshaper  # noqa: E402
from bidi.algorithm import get_display  # noqa: E402

_RESHAPER = arabic_reshaper.ArabicReshaper(
    {"language": "Farsi", "support_ligatures": False, "delete_harakat": False}
)


def fa(text: str) -> str:
    """Return ``text`` shaped and bidi-reordered, ready for reportlab/matplotlib."""
    return get_display(_RESHAPER.reshape(str(text)))


def fa_paragraph(text: str) -> str:
    """Shape a multi-line block (line order is preserved, not reversed)."""
    return "\n".join(fa(line) for line in str(text).split("\n"))


_AR_RE = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")


def is_rtl(text: str) -> bool:
    return bool(_AR_RE.search(text or ""))


# --------------------------------------------------------------------------
# Font metrics used by the layout estimator
# --------------------------------------------------------------------------

class _Metrics:
    def __init__(self):
        self._cache = {}

    def _font(self, bold: bool) -> TTFont:
        key = "b" if bold else "r"
        if key not in self._cache:
            self._cache[key] = TTFont(FONT_BOLD if bold else FONT_REGULAR, fontNumber=0)
        return self._cache[key]

    @staticmethod
    def _advances(font: TTFont) -> dict:
        upm = font["head"].unitsPerEm
        cmap = font.getBestCmap()
        hmtx = font["hmtx"]
        out = {}
        for code, gname in cmap.items():
            out[code] = hmtx[gname][0] / upm
        return out

    def width(self, text: str, size_pt: float, bold: bool = False) -> float:
        """Advance width of ``text`` in points (no shaping, no kerning)."""
        adv = self._advances(self._font(bold))
        upm = self._font(bold)["head"].unitsPerEm
        default = self._font(bold)["hmtx"]["space"][0] / upm
        total = 0.0
        for ch in str(text):
            total += adv.get(ord(ch), default)
        return total * size_pt


METRICS = _Metrics()

# --------------------------------------------------------------------------
# Content model
# --------------------------------------------------------------------------

BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
MONO_RE = re.compile(r"`([^`]+)`")


def _segments(text: str):
    """Split a string into (text, bold, mono) runs using **bold** and `code`."""
    out, pos = [], 0
    for m in re.finditer(r"\*\*(.+?)\*\*|`([^`]+)`", text):
        if m.start() > pos:
            out.append((text[pos:m.start()], False, False))
        if m.group(1) is not None:
            out.append((m.group(1), True, False))
        else:
            out.append((m.group(2), False, True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False, False))
    return out or [(text, False, False)]


@dataclass
class Block:
    kind: str
    data: dict = field(default_factory=dict)


def cover(meta: Sequence[Tuple[str, str]]):
    """Cover page.  Title/subtitle come from the Report object."""
    return Block("cover", {"meta": list(meta)})


def toc():
    return Block("toc", {})


def ptitle(text):
    return Block("ptitle", {"text": text})


def h1(text):
    return Block("h1", {"text": text})


def h2(text):
    return Block("h2", {"text": text})


def para(text):
    return Block("para", {"text": text})


def bullets(items: Sequence[str], numbered: bool = False):
    return Block("bullets", {"items": list(items), "numbered": numbered})


def table(head: Sequence[str], rows: Sequence[Sequence], widths: Optional[Sequence[float]] = None,
          caption: str = ""):
    return Block("table", {"head": list(head), "rows": [list(r) for r in rows],
                           "widths": list(widths) if widths else None, "caption": caption})


def kv(pairs: Sequence[Sequence[str]], caption: str = ""):
    return Block("kv", {"pairs": [list(x) for x in pairs], "caption": caption})


def image(path: str, width_cm: float = 15.0, caption: str = ""):
    return Block("image", {"path": path, "width_cm": width_cm, "caption": caption})


def code(lines: Sequence[str], caption: str = ""):
    return Block("code", {"lines": list(lines), "caption": caption})


def formula(text: str, caption: str = ""):
    return Block("formula", {"text": text, "caption": caption})


def note(text: str, caption: str = ""):
    return Block("note", {"text": text, "caption": caption})


def spacer(pt: float = 6):
    return Block("spacer", {"pt": pt})


@dataclass
class Page:
    blocks: List[Block]


class Report:
    """An explicitly paginated, bilingual-capable report."""

    def __init__(self, title: str, subtitle: str, lang: str = "fa",
                 cover_meta: Optional[Sequence[Tuple[str, str]]] = None,
                 rtl: Optional[bool] = None):
        self.title = title
        self.subtitle = subtitle
        self.lang = lang                      # "fa" or "en"
        self.rtl = (lang == "fa") if rtl is None else rtl
        self.cover_meta = list(cover_meta or [])
        self.pages: List[Page] = []
        self.figure_paths: List[str] = []

    # -- authoring ------------------------------------------------------
    def page(self, *blocks) -> "Report":
        self.pages.append(Page(list(blocks)))
        for b in blocks:
            if b.kind == "image":
                self.figure_paths.append(b.data["path"])
        return self

    # -- layout ---------------------------------------------------------
    def _wrap(self, text: str, size: float, bold: bool, width_pt: float) -> int:
        if not text.strip():
            return 1
        words, lines, cur = str(text).split(), 0, ""
        for w in words:
            trial = (cur + " " + w).strip()
            if METRICS.width(trial, size, bold) <= width_pt or not cur:
                cur = trial
            else:
                lines += 1
                cur = w
        return lines + (1 if cur else 0)

    def estimate_height(self, page: Page) -> float:
        """Estimated height of a page's content, in points."""
        w = TEXT_W_CM * CM
        total = 0.0
        for b in page.blocks:
            k, d = b.kind, b.data
            if k == "cover" or k == "toc":
                total += 0                      # full page by construction
            elif k == "ptitle":
                total += FS_PAGE_TITLE * LH_TITLE + SPACE_AFTER_TITLE
            elif k == "h1":
                total += FS_H1 * 1.2 + SPACE_AFTER_H1
            elif k == "h2":
                total += FS_H2 * 1.2 + SPACE_AFTER_H2
            elif k == "para":
                n = self._wrap(d["text"], FS_BODY, False, w)
                total += n * FS_BODY * LH_BODY + SPACE_AFTER_BLOCK
            elif k == "bullets":
                bw = w - BULLET_INDENT_CM * CM
                for it in d["items"]:
                    n = self._wrap(it, FS_BODY, False, bw)
                    total += n * FS_BODY * LH_BULLET + 1.5
                total += SPACE_AFTER_BLOCK
            elif k == "table":
                total += self._table_height(d, FS_TABLE, w, False)
            elif k == "kv":
                total += len(d["pairs"]) * (FS_TABLE * 1.55) + 4 + SPACE_AFTER_BLOCK
            elif k == "image":
                total += d["width_cm"] * CM * self._img_ratio(d["path"]) + 4
                if d["caption"]:
                    total += FS_CAPTION * 1.35
                total += SPACE_AFTER_BLOCK
            elif k == "code":
                total += len(d["lines"]) * FS_CODE * 1.32 + 8
                if d["caption"]:
                    total += FS_CAPTION * 1.35
                total += SPACE_AFTER_BLOCK
            elif k == "formula":
                total += len(d["text"].split("\n")) * (FS_BODY + 3) * 1.35 + 4
                if d["caption"]:
                    total += FS_CAPTION * 1.35
                total += SPACE_AFTER_BLOCK
            elif k == "note":
                n = self._wrap(d["text"], FS_BODY - 0.5, False, w - 16)
                total += n * (FS_BODY - 0.5) * 1.3 + 12 + SPACE_AFTER_BLOCK
            elif k == "spacer":
                total += d["pt"]
        return total

    def _table_height(self, d, size, w, with_caption=True) -> float:
        ncol = len(d["head"])
        cw = (w / ncol) - 6
        rows = [d["head"]] + list(d["rows"])
        h = 0.0
        for r in rows:
            lines = 1
            for c in r:
                lines = max(lines, self._wrap(str(c), size, False, cw))
            h += lines * size * 1.28 + 3
        if with_caption and d.get("caption"):
            h += FS_CAPTION * 1.35
        return h + SPACE_AFTER_BLOCK

    _ratio_cache = {}

    @classmethod
    def _img_ratio(cls, path: str) -> float:
        if path in cls._ratio_cache:
            return cls._ratio_cache[path]
        try:
            from PIL import Image
            with Image.open(path) as im:
                r = im.height / im.width
        except Exception:
            r = 0.55
        cls._ratio_cache[path] = r
        return r

    def validate(self, verbose: bool = False) -> List[Tuple[int, float, float]]:
        """Return [(page_index, used_pt, usable_pt)] for pages that overflow."""
        usable = TEXT_H_CM * CM
        bad = []
        for i, pg in enumerate(self.pages):
            used = self.estimate_height(pg)
            if used * SAFETY > usable and pg.blocks and pg.blocks[0].kind not in ("cover", "toc"):
                bad.append((i, used, usable))
                if verbose:
                    print(f"  page {i + 1}: {used:.0f}pt of {usable:.0f}pt  OVERFLOW")
        return bad

    def page_count(self) -> int:
        return len(self.pages)

    def toc_entries(self):
        """[(level, text, page_number)] using 1-based physical page numbers.

        Only page titles are listed so that the table of contents always fits on
        a single page for any report built with this kit.
        """
        out = []
        for i, pg in enumerate(self.pages):
            for b in pg.blocks:
                if b.kind == "ptitle":
                    out.append((1, b.data["text"], i + 1))
        return out


# --------------------------------------------------------------------------
# Markdown renderer (source of truth for GitHub)
# --------------------------------------------------------------------------

def _md_escape_table(cell) -> str:
    return str(cell).replace("|", "\\|").replace("\n", " ")


def render_markdown(rep: Report, intro: str = "") -> str:
    L = []
    L.append(f"# {rep.title}\n")
    if rep.subtitle:
        L.append(f"**{rep.subtitle}**\n")
    for k, v in rep.cover_meta:
        L.append(f"- **{k}:** {v}")
    L.append("")
    if intro:
        L.append(intro.strip() + "\n")
    # table of contents (markdown link-less list)
    L.append("## Table of contents\n")
    for level, text, pno in rep.toc_entries():
        L.append(f"{'  ' * (level - 1)}- {text} (p. {pno})")
    L.append("")
    nfig = 0
    for i, pg in enumerate(rep.pages):
        L.append(f"\n<!-- page {i + 1} -->\n")
        for b in pg.blocks:
            k, d = b.kind, b.data
            if k == "cover":
                continue
            if k == "toc":
                continue
            elif k == "ptitle":
                L.append(f"\n## {d['text']}\n")
            elif k == "h1":
                L.append(f"\n### {d['text']}\n")
            elif k == "h2":
                L.append(f"\n#### {d['text']}\n")
            elif k == "para":
                L.append(d["text"] + "\n")
            elif k == "bullets":
                for j, it in enumerate(d["items"]):
                    mark = f"{j + 1}. " if d["numbered"] else "- "
                    L.append(mark + it)
                L.append("")
            elif k == "table":
                head = "| " + " | ".join(_md_escape_table(c) for c in d["head"]) + " |"
                L.append(head)
                L.append("|" + "|".join(["---"] * len(d["head"])) + "|")
                for r in d["rows"]:
                    L.append("| " + " | ".join(_md_escape_table(c) for c in r) + " |")
                L.append("")
                if d["caption"]:
                    L.append(f"*{d['caption']}*\n")
            elif k == "kv":
                L.append("| " + " | ".join(_md_escape_table(c) for c in d["pairs"][0]) + " |"
                         if d["pairs"] else "")
                L.append("|---|---|")
                for r in d["pairs"][1:]:
                    L.append("| " + " | ".join(_md_escape_table(c) for c in r) + " |")
                L.append("")
                if d["caption"]:
                    L.append(f"*{d['caption']}*\n")
            elif k == "image":
                nfig += 1
                rel = os.path.basename(d["path"])
                L.append(f"![Figure {nfig}: {d['caption']}]({rel})\n")
                if d["caption"]:
                    L.append(f"*Figure {nfig}. {d['caption']}*\n")
            elif k == "code":
                L.append("```text")
                L.extend(d["lines"])
                L.append("```")
                if d["caption"]:
                    L.append(f"*{d['caption']}*\n")
            elif k == "formula":
                L.append("```text")
                L.extend(d["text"].split("\n"))
                L.append("```")
                if d["caption"]:
                    L.append(f"*{d['caption']}*\n")
            elif k == "note":
                L.append(f"> **{d.get('caption') or 'Note'}.** {d['text']}\n")
            elif k == "spacer":
                pass
    return "\n".join(L)


# --------------------------------------------------------------------------
# DOCX renderer
# --------------------------------------------------------------------------

def _docx_set_rtl(paragraph, rtl: bool, align_right: bool):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr = paragraph._p.get_or_add_pPr()
    bidi = pPr.find(qn("w:bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi")
        pPr.append(bidi)
    bidi.set(qn("w:val"), "1" if rtl else "0")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT if align_right else WD_ALIGN_PARAGRAPH.LEFT


def _docx_run(paragraph, text, size, bold=False, mono=False, rtl=True):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import Pt
    run = paragraph.add_run()
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rPr.append(rf)
    family = "Consolas" if mono else FONT_NAME
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), family)
    if rtl and not mono:
        cs = rPr.find(qn("w:cs"))
        if cs is None:
            cs = OxmlElement("w:cs")
            rPr.append(cs)
    sz = rPr.find(qn("w:sz"))
    if sz is None:
        sz = OxmlElement("w:sz")
        rPr.append(sz)
    sz.set(qn("w:val"), str(int(size * 2)))
    szcs = OxmlElement("w:szCs")
    szcs.set(qn("w:val"), str(int(size * 2)))
    rPr.append(szcs)
    run.bold = bold
    run.font.size = Pt(size)
    run.text = text
    return run


def _docx_runs(paragraph, text, size, rtl=True, default_bold=False):
    for seg, isb, ism in _segments(text):
        _docx_run(paragraph, seg, size, bold=(isb or default_bold), mono=ism, rtl=rtl)


def _docx_para(doc, rep, size=FS_BODY, align_right=None, space_after=0, space_before=0,
               line_spacing=None):
    from docx.shared import Pt
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    if line_spacing:
        pf.line_spacing = line_spacing
    _docx_set_rtl(p, rep.rtl, (align_right if align_right is not None else rep.rtl))
    return p


def _cell_shade(cell, hexcolor):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hexcolor)
    tcPr.append(sh)


def _docx_table(doc, rep, head, rows, widths=None, size=FS_TABLE):
    from docx.shared import Cm, Pt
    ncol = len(head)
    t = doc.add_table(rows=1, cols=ncol)
    t.style = "Table Grid"
    t.autofit = True
    hdr = t.rows[0].cells
    for i, h in enumerate(head):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.space_before = Pt(1)
        _docx_set_rtl(p, rep.rtl, rep.rtl)
        _docx_runs(p, str(h), size, rtl=rep.rtl)
        for r in p.runs:
            r.bold = True
        _cell_shade(hdr[i], "DCE6F1")
    for r_i, row in enumerate(rows):
        cells = t.add_row().cells
        for i, c in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            _docx_set_rtl(p, rep.rtl, rep.rtl)
            _docx_runs(p, str(c), size, rtl=rep.rtl)
        if r_i % 2 == 1:
            for c in cells:
                _cell_shade(c, "F4F6FA")
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    return t


def build_docx(rep: Report, path: str, figures_dir: Optional[str] = None) -> str:
    from docx import Document
    from docx.shared import Cm, Pt
    from docx.enum.section import WD_SECTION
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(PAGE_W_CM), Cm(PAGE_H_CM)
    sec.left_margin = sec.right_margin = Cm(MARGIN_X_CM)
    sec.top_margin, sec.bottom_margin = Cm(MARGIN_TOP_CM), Cm(MARGIN_BOT_CM)

    style = doc.styles["Normal"]
    style.font.name = FONT_NAME
    style.font.size = Pt(FS_BODY)
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), FONT_NAME)
    cs = rpr.find(qn("w:cs"))
    if cs is None:
        cs = OxmlElement("w:cs")
        rpr.append(cs)

    # ---- footer with page number -------------------------------------
    footer_p = sec.footer.paragraphs[0]
    footer_p.alignment = 1
    _docx_run(footer_p, "", FS_CAPTION, rtl=False)
    run = footer_p.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    footer_p._p.append(fld)

    nfig = 0
    toc_page_index = next((i for i, pg in enumerate(rep.pages)
                           if any(b.kind == "toc" for b in pg.blocks)), None)

    for i, pg in enumerate(rep.pages):
        if i > 0:
            doc.add_page_break()
        for b in pg.blocks:
            k, d = b.kind, b.data
            if k == "cover":
                for _ in range(3):
                    _docx_para(doc, rep, size=FS_BODY, space_after=0)
                p = _docx_para(doc, rep, size=FS_COVER_TITLE, space_after=10)
                _docx_run(p, rep.title, FS_COVER_TITLE, bold=True, rtl=rep.rtl)
                if rep.subtitle:
                    p = _docx_para(doc, rep, size=FS_COVER_SUB, space_after=16)
                    _docx_run(p, rep.subtitle, FS_COVER_SUB, rtl=rep.rtl)
                for key, val in d["meta"]:
                    p = _docx_para(doc, rep, size=FS_BODY, space_after=3)
                    _docx_run(p, f"{key}: ", FS_BODY, bold=True, rtl=rep.rtl)
                    _docx_run(p, str(val), FS_BODY, rtl=rep.rtl)
            elif k == "toc":
                p = _docx_para(doc, rep, size=FS_PAGE_TITLE, space_after=8)
                _docx_run(p, d.get("title") or ("فهرست مطالب" if rep.lang == "fa" else "Table of contents"),
                          FS_PAGE_TITLE, bold=True, rtl=rep.rtl)
                for level, text, pno in rep.toc_entries():
                    p = _docx_para(doc, rep, size=FS_BODY - 0.5, space_after=1)
                    pf = p.paragraph_format
                    pf.left_indent = Cm(0.0 if level == 1 else 0.8)
                    _docx_run(p, text, FS_BODY - 0.5, bold=(level == 1), rtl=rep.rtl)
                    _docx_run(p, "  " + ("." * 4) + f" {pno}", FS_BODY - 0.5, rtl=rep.rtl)
            elif k == "ptitle":
                p = _docx_para(doc, rep, size=FS_PAGE_TITLE, space_after=SPACE_AFTER_TITLE)
                _docx_run(p, d["text"], FS_PAGE_TITLE, bold=True, rtl=rep.rtl)
            elif k == "h1":
                p = _docx_para(doc, rep, size=FS_H1, space_after=SPACE_AFTER_H1, space_before=2)
                _docx_run(p, d["text"], FS_H1, bold=True, rtl=rep.rtl)
            elif k == "h2":
                p = _docx_para(doc, rep, size=FS_H2, space_after=SPACE_AFTER_H2, space_before=2)
                _docx_run(p, d["text"], FS_H2, bold=True, rtl=rep.rtl)
            elif k == "para":
                p = _docx_para(doc, rep, size=FS_BODY, space_after=SPACE_AFTER_BLOCK,
                               line_spacing=LH_BODY)
                _docx_runs(p, d["text"], FS_BODY, rtl=rep.rtl)
            elif k == "bullets":
                for j, it in enumerate(d["items"]):
                    p = _docx_para(doc, rep, size=FS_BODY, space_after=1, line_spacing=LH_BULLET)
                    pf = p.paragraph_format
                    if rep.rtl:
                        pf.right_indent = Cm(0)
                        pf.left_indent = Cm(BULLET_INDENT_CM)
                    else:
                        pf.left_indent = Cm(BULLET_INDENT_CM)
                    mark = f"{j + 1}. " if d["numbered"] else "\u2022  "
                    _docx_run(p, mark, FS_BODY, rtl=rep.rtl)
                    _docx_runs(p, it, FS_BODY, rtl=rep.rtl)
            elif k == "table":
                _docx_table(doc, rep, d["head"], d["rows"], d["widths"])
                if d["caption"]:
                    nfig += 1
                    p = _docx_para(doc, rep, size=FS_CAPTION, space_after=SPACE_AFTER_BLOCK,
                                   space_before=2)
                    _docx_run(p, (f"جدول {nfig}. " if rep.lang == "fa" else f"Table {nfig}. ")
                              + d["caption"], FS_CAPTION, rtl=rep.rtl)
            elif k == "kv":
                _docx_table(doc, rep, list(d["pairs"][0]), list(d["pairs"][1:]),
                            [5.0, TEXT_W_CM - 5.0])
                if d["caption"]:
                    nfig += 1
                    p = _docx_para(doc, rep, size=FS_CAPTION, space_after=SPACE_AFTER_BLOCK,
                                   space_before=2)
                    _docx_run(p, (f"جدول {nfig}. " if rep.lang == "fa" else f"Table {nfig}. ")
                              + d["caption"], FS_CAPTION, rtl=rep.rtl)
            elif k == "image":
                nfig += 1
                src = d["path"]
                if figures_dir:
                    src = os.path.join(figures_dir, os.path.basename(src))
                p = _docx_para(doc, rep, size=FS_BODY, space_after=2)
                try:
                    p.add_run().add_picture(src, width=Cm(d["width_cm"]))
                except Exception as exc:  # pragma: no cover - defensive
                    _docx_run(p, f"[missing image: {src} ({exc})]", FS_BODY, rtl=rep.rtl)
                if d["caption"]:
                    cp = _docx_para(doc, rep, size=FS_CAPTION, space_after=SPACE_AFTER_BLOCK)
                    _docx_run(cp, (f"شکل {nfig}. " if rep.lang == "fa" else f"Figure {nfig}. ")
                              + d["caption"], FS_CAPTION, rtl=rep.rtl)
            elif k == "code":
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                for line in d["lines"]:
                    p = _docx_para(doc, rep, size=FS_CODE, space_after=0, align_right=False)
                    p.paragraph_format.left_indent = Cm(0.4)
                    p.paragraph_format.line_spacing = 1.0
                    _docx_run(p, line if line else " ", FS_CODE, mono=True, rtl=False)
                if d["caption"]:
                    cp = _docx_para(doc, rep, size=FS_CAPTION, space_after=SPACE_AFTER_BLOCK,
                                    space_before=2)
                    _docx_run(cp, d["caption"], FS_CAPTION, rtl=rep.rtl)
            elif k == "formula":
                for line in d["text"].split("\n"):
                    p = _docx_para(doc, rep, size=FS_BODY + 1, space_after=0, align_right=False)
                    p.alignment = 1
                    _docx_run(p, line, FS_BODY + 1, mono=True, rtl=False)
                if d["caption"]:
                    cp = _docx_para(doc, rep, size=FS_CAPTION, space_after=SPACE_AFTER_BLOCK,
                                    space_before=2)
                    _docx_run(cp, d["caption"], FS_CAPTION, rtl=rep.rtl)
            elif k == "note":
                p = _docx_para(doc, rep, size=FS_BODY - 0.5, space_after=SPACE_AFTER_BLOCK)
                label = d.get("caption") or ("نکته" if rep.lang == "fa" else "Note")
                _docx_run(p, label + ": ", FS_BODY - 0.5, bold=True, rtl=rep.rtl)
                _docx_runs(p, d["text"], FS_BODY - 0.5, rtl=rep.rtl)
            elif k == "spacer":
                p = _docx_para(doc, rep, size=6, space_after=0)
                p.paragraph_format.line_spacing = 0.5

    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    doc.save(path)
    return path


# --------------------------------------------------------------------------
# PDF renderer (reportlab) - exact page count
# --------------------------------------------------------------------------

from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont as RLTTF  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,  # noqa: E402
                                Spacer, Table as RLTable, TableStyle, Image as RLImage,
                                PageBreak, ListFlowable, ListItem)
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER  # noqa: E402

pdfmetrics.registerFont(RLTTF("Vazirmatn", FONT_REGULAR))
pdfmetrics.registerFont(RLTTF("Vazirmatn-Bold", FONT_BOLD))
pdfmetrics.registerFontFamily("Vazirmatn", normal="Vazirmatn", bold="Vazirmatn-Bold",
                              italic="Vazirmatn", boldItalic="Vazirmatn-Bold")
try:
    pdfmetrics.registerFont(RLTTF("Mono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
    MONO_FONT = "Mono"
except Exception:                                   # pragma: no cover
    MONO_FONT = "Courier"


def _pdf_style(name, size, bold=False, align=None, rtl=False, leading=None,
               font=MONO_FONT):
    if rtl:
        fname = "Vazirmatn-Bold" if bold else "Vazirmatn"
    else:
        fname = font if name.startswith("code") or name.startswith("formula") else (
            "Vazirmatn-Bold" if bold else "Vazirmatn")
    al = align if align is not None else (TA_RIGHT if rtl else TA_LEFT)
    return ParagraphStyle(name, fontName=fname, fontSize=size,
                          leading=leading or size * 1.28, alignment=al,
                          spaceAfter=0, spaceBefore=0, wordWrap="RTL" if rtl else "LTR")


SYMBOL_MAP = {
    "\u2192": "-&gt;", "\u2190": "&lt;-", "\u2194": "&lt;-&gt;", "\u21d2": "=&gt;",
    "\u2264": "&lt;=", "\u2265": "&gt;=", "\u2260": "!=", "\u2248": "~",
    "\u03a3": "sum", "\u221a": "sqrt", "\u221e": "inf", "\u00b1": "+/-",
    "\u25aa": "*", "\u25a0": "#", "\u25cf": "*", "\u25cb": "o",
    "\u25b2": "^", "\u25bc": "v", "\u00b0": "deg", "\u2200": "for all",
    "\u2203": "exists", "\u2208": "in", "\u2211": "sum", "\u220f": "prod",
}

MISSING_GLYPHS = []

_FONT_CMAP = None


def _cmap():
    global _FONT_CMAP
    if _FONT_CMAP is None:
        _FONT_CMAP = set(TTFont(FONT_REGULAR, fontNumber=0).getBestCmap().keys())
    return _FONT_CMAP


def _pdf_text(text, rtl=True):
    """Escape XML and, for RTL, shape + reorder the string."""
    esc = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for k, v in SYMBOL_MAP.items():
        esc = esc.replace(k, v)
    if not rtl:
        return esc
    out = fa(esc)
    cm = _cmap()
    bad = [ch for ch in out if ord(ch) not in cm and ch not in "\n\t"]
    if bad:
        MISSING_GLYPHS.extend(sorted(set(bad)))
        out = "".join(ch if (ord(ch) in cm or ch in "\n\t") else "?" for ch in out)
    return out


def _pdf_rich(text, rtl=True, bold_all=False):
    """Convert **bold** / `code` markup to reportlab inline tags."""
    out = []
    for seg, isb, ism in _segments(str(text)):
        s = _pdf_text(seg, rtl)
        if ism:
            out.append(f'<font face="{MONO_FONT}" size="{FS_BODY - 0.5}">{s}</font>')
        elif isb or bold_all:
            out.append(f"<b>{s}</b>")
        else:
            out.append(s)
    return "".join(out)


def _styles(rtl: bool):
    """Build the paragraph styles for a report."""
    return {
        "cover_title": _pdf_style("cover_title", FS_COVER_TITLE, bold=True, align=TA_CENTER,
                                  rtl=rtl, leading=FS_COVER_TITLE * 1.3),
        "cover_sub": _pdf_style("cover_sub", FS_COVER_SUB, align=TA_CENTER, rtl=rtl,
                                leading=FS_COVER_SUB * 1.4),
        "cover_meta": _pdf_style("cover_meta", FS_BODY, align=TA_CENTER, rtl=rtl,
                                 leading=FS_BODY * 1.6),
        "ptitle": _pdf_style("ptitle", FS_PAGE_TITLE, bold=True, rtl=rtl,
                             leading=FS_PAGE_TITLE * 1.25),
        "h1": _pdf_style("h1", FS_H1, bold=True, rtl=rtl, leading=FS_H1 * 1.25),
        "h2": _pdf_style("h2", FS_H2, bold=True, rtl=rtl, leading=FS_H2 * 1.25),
        "body": _pdf_style("body", FS_BODY, rtl=rtl, leading=FS_BODY * LH_BODY),
        "bullet": _pdf_style("bullet", FS_BODY, rtl=rtl, leading=FS_BODY * LH_BULLET),
        "cap": _pdf_style("cap", FS_CAPTION, rtl=rtl, leading=FS_CAPTION * 1.4, align=TA_CENTER),
        "code": _pdf_style("code", FS_CODE, align=TA_LEFT, rtl=False, leading=FS_CODE * 1.3,
                           font=MONO_FONT),
        "formula": _pdf_style("formula", FS_BODY + 1, align=TA_CENTER, rtl=False,
                              leading=(FS_BODY + 1) * 1.35, font=MONO_FONT),
        "cell": _pdf_style("cell", FS_TABLE, rtl=rtl, leading=FS_TABLE * 1.28),
        "cellh": _pdf_style("cellh", FS_TABLE, bold=True, rtl=rtl, leading=FS_TABLE * 1.28),
    }


def _block_flowables(rep: Report, b: Block, S, figures_dir, nfig):
    """Return (flowables, new_figure_number) for one block."""
    rtl = rep.rtl
    out = []
    k, d = b.kind, b.data
    if k == "cover":
        out.append(Spacer(1, 3.2 * cm))
        out.append(Paragraph(_pdf_text(rep.title, rtl), S["cover_title"]))
        out.append(Spacer(1, 0.5 * cm))
        if rep.subtitle:
            out.append(Paragraph(_pdf_rich(rep.subtitle, rtl), S["cover_sub"]))
        out.append(Spacer(1, 1.4 * cm))
        for key, val in d["meta"]:
            out.append(Paragraph(f"<b>{_pdf_text(key, rtl)}</b>  {_pdf_text(val, rtl)}",
                                 S["cover_meta"]))
    elif k == "toc":
        out.append(Paragraph(_pdf_text(d.get("title")
                                       or ("فهرست مطالب" if rep.lang == "fa"
                                           else "Table of contents"), rtl), S["ptitle"]))
        out.append(Spacer(1, 0.3 * cm))
        tstyle = _pdf_style("toctext", FS_BODY - 1.5, rtl=rtl,
                            leading=(FS_BODY - 1.5) * 1.35)
        tdata = [[str(pno), Paragraph(_pdf_text(text, rtl), tstyle)]
                 for level, text, pno in rep.toc_entries()]
        tt = RLTable(tdata, colWidths=[1.2 * cm, (TEXT_W_CM - 1.2) * cm])
        tt.setStyle(TableStyle([
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
            ("TOPPADDING", (0, 0), (-1, -1), 0.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#e3e8f0")),
        ]))
        out.append(tt)
    elif k == "ptitle":
        out.append(Paragraph(_pdf_text(d["text"], rtl), S["ptitle"]))
        out.append(Spacer(1, 0.22 * cm))
    elif k == "h1":
        out.append(Spacer(1, 0.1 * cm))
        out.append(Paragraph(_pdf_text(d["text"], rtl), S["h1"]))
        out.append(Spacer(1, 0.08 * cm))
    elif k == "h2":
        out.append(Paragraph(_pdf_text(d["text"], rtl), S["h2"]))
    elif k == "para":
        out.append(Paragraph(_pdf_rich(d["text"], rtl), S["body"]))
        out.append(Spacer(1, 0.14 * cm))
    elif k == "bullets":
        bstyle = _pdf_style("bulletr", FS_BODY, rtl=rtl, leading=FS_BODY * LH_BULLET)
        bstyle.leftIndent = BULLET_INDENT_CM * cm
        bstyle.spaceAfter = 1.5
        for j, it in enumerate(d["items"]):
            mark = f"{j + 1}." if d["numbered"] else "\u2022"
            out.append(Paragraph(_pdf_text(mark, rtl) + "\u00a0\u00a0" + _pdf_rich(it, rtl),
                                 bstyle))
        out.append(Spacer(1, 0.14 * cm))
    elif k in ("table", "kv"):
        if k == "table":
            head, rows = d["head"], d["rows"]
        else:
            head, rows = list(d["pairs"][0]), list(d["pairs"][1:])
        ncol = len(head)
        cw = (TEXT_W_CM * cm / ncol)
        data = [[Paragraph(_pdf_text(str(c), rtl), S["cellh"]) for c in head]]
        for r in rows:
            data.append([Paragraph(_pdf_text(str(c), rtl), S["cell"]) for c in r])
        tt = RLTable(data, colWidths=[cw] * ncol, repeatRows=1)
        tt.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fb2cc")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fa")]),
        ]))
        out.append(tt)
        if d["caption"]:
            nfig += 1
            out.append(Spacer(1, 0.08 * cm))
            out.append(Paragraph(_pdf_text((f"جدول {nfig}. " if rep.lang == "fa"
                                            else f"Table {nfig}. ") + d["caption"], rtl),
                                 S["cap"]))
        out.append(Spacer(1, 0.14 * cm))
    elif k == "image":
        nfig += 1
        src = d["path"]
        if figures_dir:
            src = os.path.join(figures_dir, os.path.basename(src))
        try:
            out.append(RLImage(src, width=d["width_cm"] * cm,
                               height=d["width_cm"] * cm * Report._img_ratio(src)))
        except Exception as exc:                              # pragma: no cover
            out.append(Paragraph(f"[missing image {src}: {exc}]", S["body"]))
        if d["caption"]:
            out.append(Spacer(1, 0.06 * cm))
            out.append(Paragraph(_pdf_text((f"شکل {nfig}. " if rep.lang == "fa"
                                            else f"Figure {nfig}. ") + d["caption"], rtl),
                                 S["cap"]))
        out.append(Spacer(1, 0.14 * cm))
    elif k == "code":
        for line in d["lines"]:
            out.append(Paragraph(_pdf_text(line if line else " ", False).replace(" ", "&nbsp;"),
                                 S["code"]))
        if d["caption"]:
            out.append(Spacer(1, 0.06 * cm))
            out.append(Paragraph(_pdf_text(d["caption"], rtl), S["cap"]))
        out.append(Spacer(1, 0.14 * cm))
    elif k == "formula":
        for line in d["text"].split("\n"):
            out.append(Paragraph(_pdf_text(line if line else " ", False).replace(" ", "&nbsp;"),
                                 S["formula"]))
        if d["caption"]:
            out.append(Spacer(1, 0.06 * cm))
            out.append(Paragraph(_pdf_text(d["caption"], rtl), S["cap"]))
        out.append(Spacer(1, 0.14 * cm))
    elif k == "note":
        label = d.get("caption") or ("نکته" if rep.lang == "fa" else "Note")
        body = f"<b>{_pdf_text(label, rtl)}:</b> {_pdf_rich(d['text'], rtl)}"
        tt = RLTable([[Paragraph(body, _pdf_style("noteb", FS_BODY - 0.5, rtl=rtl,
                                                  leading=(FS_BODY - 0.5) * 1.3))]],
                     colWidths=[TEXT_W_CM * cm])
        tt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f2f5fb")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9fb2cc")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        out.append(tt)
        out.append(Spacer(1, 0.14 * cm))
    elif k == "spacer":
        out.append(Spacer(1, d["pt"]))
    return out, nfig


def exact_heights(rep: Report, figures_dir: Optional[str] = None):
    """Measured height of every page, in points, as reportlab sees it.

    ``flowable.wrap()`` returns the height that reportlab will actually reserve,
    so this is exact for the PDF.  The DOCX uses the same geometry, font and
    sizes, so the same numbers are a very good approximation there as well.
    """
    S = _styles(rep.rtl)
    avail_w = TEXT_W_CM * cm
    frame_h = TEXT_H_CM * cm
    out, nfig = [], 0
    for pg in rep.pages:
        fl, nfig_local = [], nfig
        for b in pg.blocks:
            f, nfig_local = _block_flowables(rep, b, S, figures_dir, nfig_local)
            fl.extend(f)
        nfig = nfig_local
        h = 0.0
        for f in fl:
            try:
                h += f.wrap(avail_w, frame_h)[1]
            except Exception:                                  # pragma: no cover
                pass
        out.append(h)
    return out


def build_pdf(rep: Report, path: str, figures_dir: Optional[str] = None,
              footer_note: str = "") -> str:
    rtl = rep.rtl
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)

    frame = Frame(MARGIN_X_CM * cm, MARGIN_BOT_CM * cm, TEXT_W_CM * cm, TEXT_H_CM * cm,
                  id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def decorate(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Vazirmatn", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        y = 1.05 * cm
        if footer_note:
            canvas.drawString(MARGIN_X_CM * cm, y, footer_note)
        canvas.drawRightString(PAGE_W_CM * cm - MARGIN_X_CM * cm, y, str(canvas.getPageNumber()))
        canvas.setStrokeColor(colors.HexColor("#c9d2e0"))
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_X_CM * cm, y + 0.35 * cm,
                    PAGE_W_CM * cm - MARGIN_X_CM * cm, y + 0.35 * cm)
        canvas.restoreState()

    doc = BaseDocTemplate(path, pagesize=A4,
                          leftMargin=MARGIN_X_CM * cm, rightMargin=MARGIN_X_CM * cm,
                          topMargin=MARGIN_TOP_CM * cm, bottomMargin=MARGIN_BOT_CM * cm,
                          title=rep.title, author="Multilevel-Queue-Scheduling project")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorate)])

    S = _styles(rtl)
    story, nfig = [], 0
    for i, pg in enumerate(rep.pages):
        if i > 0:
            story.append(PageBreak())
        for b in pg.blocks:
            fl, nfig = _block_flowables(rep, b, S, figures_dir, nfig)
            story.extend(fl)

    doc.build(story)
    return path


# --------------------------------------------------------------------------
# Page-count helpers
# --------------------------------------------------------------------------

def pdf_page_count(path: str) -> int:
    """Exact physical page count, read back from the produced PDF."""
    with open(path, "rb") as f:
        data = f.read()
    n = data.count(b"/Type /Page\n") + data.count(b"/Type /Page/") + \
        data.count(b"/Type /Page>>")
    if n == 0:                              # fall back to a Count entry
        import re as _re
        m = _re.search(rb"/Count\s+(\d+)", data)
        n = int(m.group(1)) if m else 0
    return n
