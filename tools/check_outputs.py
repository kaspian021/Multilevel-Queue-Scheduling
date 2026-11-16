"""Verify the generated artefacts.

Two different page counts are reported, and they are *not* the same kind of
number:

* **PDF pages — exact.**  Read back from the produced PDF file.
* **DOCX pages — measured estimate.**  The DOCX is opened and every paragraph,
  table row and image is measured against the real section geometry using the
  advance widths of the embedded report font.  Word's line-breaking differs
  slightly from this model, so the DOCX figure is an estimate; it is reported
  together with the maximum page fill so the margin of error is visible.

Usage::

    python tools/check_outputs.py exercise-1
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from docx import Document                                     # noqa: E402
from docx.shared import Length                                # noqa: E402
from docx.oxml.ns import qn                                   # noqa: E402

import report_kit as rk                                       # noqa: E402

EMU_PER_PT = 12700
DEFAULT_LINE = 1.15          # Word's default single spacing for a TrueType font


def _emu(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _text_width(text, size_pt, bold):
    return rk.METRICS.width(text, size_pt, bold)


def _run_width_and_size(runs):
    total = 0.0
    size = rk.FS_BODY
    for r in runs:
        sz = r.font.size
        s = sz.pt if sz is not None else rk.FS_BODY
        size = max(size, s)
        total += _text_width(r.text or "", s, bool(r.bold))
    return total, size


def _paragraph_height(p, avail_pt, default_size=rk.FS_BODY):
    pf = p.paragraph_format
    size = default_size
    width = 0.0
    for r in p.runs:
        sz = r.font.size
        s = sz.pt if sz is not None else default_size
        size = max(size, s)
        width += _text_width(r.text or "", s, bool(r.bold))
    line = pf.line_spacing if isinstance(pf.line_spacing, float) else DEFAULT_LINE
    if isinstance(pf.line_spacing, Length):
        line = pf.line_spacing.pt / size
    indents = 0.0
    for attr in ("left_indent", "right_indent"):
        v = getattr(pf, attr)
        if v is not None:
            indents += v.pt
    avail = max(avail_pt - indents, 40.0)
    lines = max(1, int(width / avail) + (1 if width % avail else 0))
    before = pf.space_before.pt if pf.space_before is not None else 0.0
    after = pf.space_after.pt if pf.space_after is not None else 0.0
    return lines * size * line + before + after, size


def estimate_docx_pages(path):
    doc = Document(path)
    sec = doc.sections[0]
    page_h = sec.page_height.pt - sec.top_margin.pt - sec.bottom_margin.pt
    avail = sec.page_width.pt - sec.left_margin.pt - sec.right_margin.pt

    pages, used, max_fill = 1, 0.0, 0.0
    body = doc.element.body

    def add(h):
        nonlocal used, pages, max_fill
        if used + h > page_h:
            pages += 1
            max_fill = max(max_fill, used / page_h)
            used = 0.0
        used += h

    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            para = Paragraph(child, doc)
            if child.findall(f".//{qn('w:br')}"):
                for br in child.findall(f".//{qn('w:br')}"):
                    if br.get(qn("w:type")) == "page":
                        max_fill = max(max_fill, used / page_h)
                        pages += 1
                        used = 0.0
            # embedded picture
            h = 0.0
            for ext in child.findall(f".//{qn('wp:extent')}"):
                cy = _emu(ext.get("cy"))
                if cy:
                    h += cy / EMU_PER_PT
            if h:
                add(h)
            ph, _ = _paragraph_height(para, avail)
            if (para.text or "").strip() or h == 0:
                add(ph)
        elif child.tag == qn("w:tbl"):
            tbl = Table(child, doc)
            for row in tbl.rows:
                rh = 0.0
                for cell in row.cells:
                    cw = (cell.width.pt if cell.width is not None else avail / max(len(row.cells), 1))
                    ch = 0.0
                    for p in cell.paragraphs:
                        ph_, _ = _paragraph_height(p, cw - 6, default_size=rk.FS_TABLE)
                        ch += ph_
                    rh = max(rh, ch)
                add(rh + 2)
    max_fill = max(max_fill, used / page_h)
    return pages, round(max_fill, 3)


def check(exercise):
    docs = os.path.join(REPO, exercise, "docs")
    result = {"exercise": exercise, "files": []}
    if not os.path.isdir(docs):
        return result
    for name in sorted(os.listdir(docs)):
        if not name.lower().endswith((".docx", ".pdf")):
            continue
        path = os.path.join(docs, name)
        entry = {"file": f"{exercise}/docs/{name}", "bytes": os.path.getsize(path)}
        if name.lower().endswith(".pdf"):
            entry["pages"] = rk.pdf_page_count(path)
            entry["pages_kind"] = "exact (read from the PDF)"
        else:
            pages, fill = estimate_docx_pages(path)
            entry["pages"] = pages
            entry["pages_kind"] = "measured estimate (Word reflow may differ)"
            entry["max_page_fill"] = fill
        result["files"].append(entry)
    return result


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    out = [check(a) for a in argv[1:]]
    print(json.dumps(out if len(out) > 1 else out[0], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
