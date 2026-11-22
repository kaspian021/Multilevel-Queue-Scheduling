#!/usr/bin/env python3
"""Build a compact, correctly right-to-left Persian report (DOCX + PDF) from Markdown.

Usage: build_fa_report.py SOURCE.md OUTPUT_STEM [--root REPO_ROOT]
  -> OUTPUT_STEM.docx and OUTPUT_STEM.pdf

Why this exists: the old pipeline forced a page break per section (pages 20-40 %
full), put code blocks in RTL paragraphs (colons / parentheses flipped) and left
tables left-to-right. This builder lays the document out continuously, keeps
code blocks LTR, tables RTL and figures size-capped, then fills the table of
contents with real page numbers read from the PDF bookmarks.
"""
from __future__ import annotations
import argparse, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from pypdf import PdfReader
from PIL import Image

FA_FONT = "Noto Naskh Arabic"
LATIN_FONT = "Noto Serif"
MONO_FONT = "DejaVu Sans Mono"
ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
INLINE = re.compile(r"(\*\*.+?\*\*|`.+?`|\*[^*\s][^*]*?\*|\[[^\]]+\]\([^)]+\))")
IMG = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
COMMENT = re.compile(r"^\s*<!--.*?-->\s*$")
TOC_ITEM = re.compile(r"^(.*?)\s*\(p\.\s*\d+\)\s*$")
BODY_PT = 12
TEXT_W = 6.75  # inches of usable width


def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def par_shading(p, fill, border_color=None):
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
    pPr.append(shd)
    if border_color:
        b = OxmlElement("w:pBdr")
        side = OxmlElement("w:right")
        side.set(qn("w:val"), "single"); side.set(qn("w:sz"), "18"); side.set(qn("w:space"), "6"); side.set(qn("w:color"), border_color)
        b.append(side); pPr.append(b)


def set_bidi(p, rtl=True):
    pPr = p._p.get_or_add_pPr()
    b = pPr.find(qn("w:bidi"))
    if rtl:
        if b is None:
            b = OxmlElement("w:bidi"); pPr.append(b)
        b.set(qn("w:val"), "1")
        p.alignment = None  # default 'start' edge == right edge in a bidi paragraph
    else:
        if b is not None: pPr.remove(b)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def style_run(r, text, *, mono=False, size=None, bold=None, italic=None, color=None):
    rPr = r._r.get_or_add_rPr()
    f = rPr.find(qn("w:rFonts"))
    if f is None:
        f = OxmlElement("w:rFonts"); rPr.append(f)
    if mono:
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"): f.set(qn(a), MONO_FONT)
    else:
        f.set(qn("w:ascii"), LATIN_FONT); f.set(qn("w:hAnsi"), LATIN_FONT)
        f.set(qn("w:cs"), FA_FONT); f.set(qn("w:eastAsia"), FA_FONT)
    if ARABIC.search(text) and not mono:
        x = OxmlElement("w:rtl"); x.set(qn("w:val"), "1"); rPr.append(x)
    if size: r.font.size = Pt(size)
    if bold is not None:
        r.bold = bold
        if bold:
            bcs = OxmlElement("w:bCs"); rPr.append(bcs)
    if italic is not None: r.italic = italic
    if color: r.font.color.rgb = RGBColor.from_string(color)


def add_inline(p, s, *, size=None, bold=None, italic=None, color=None):
    pos = 0
    def emit(t, **kw):
        if not t: return
        r = p.add_run(t)
        style_run(r, t, size=size, color=color, **{"bold": bold, "italic": italic, **kw})
    for m in INLINE.finditer(s):
        emit(s[pos:m.start()])
        t = m.group()
        if t.startswith("**"): emit(t[2:-2], bold=True)
        elif t.startswith("`"):
            r = p.add_run(t[1:-1]); style_run(r, t, mono=True, size=(size or 11) - 1.5, color=color)
        elif t.startswith("["):
            emit(re.match(r"\[([^\]]+)\]", t).group(1))
        else: emit(t[1:-1], italic=True)
        pos = m.end()
    emit(s[pos:])


def setup_document():
    d = Document()
    sec = d.sections[0]
    sec.page_width = Inches(8.27); sec.page_height = Inches(11.69)
    sec.top_margin = Inches(.8); sec.bottom_margin = Inches(.8)
    sec.left_margin = Inches(.76); sec.right_margin = Inches(.76)
    # footer: centred page number
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run()
    for tag, attrs, val in [("w:fldChar", {"w:fldCharType": "begin"}, None),
                            ("w:instrText", {"xml:space": "preserve"}, " PAGE "),
                            ("w:fldChar", {"w:fldCharType": "separate"}, None),
                            ("w:t", {}, "1"),
                            ("w:fldChar", {"w:fldCharType": "end"}, None)]:
        el = OxmlElement(tag)
        for k, v in attrs.items(): el.set(qn(k), v)
        if val is not None: el.text = val
        r._r.append(el)
    st = d.styles["Normal"]; st.font.name = LATIN_FONT; st.font.size = Pt(BODY_PT)
    rf = st.element.get_or_add_rPr().find(qn("w:rFonts"))
    rf.set(qn("w:cs"), FA_FONT); rf.set(qn("w:eastAsia"), FA_FONT)
    st.paragraph_format.space_after = Pt(5); st.paragraph_format.space_before = Pt(0)
    st.paragraph_format.line_spacing = 1.18
    # complex-script size
    szcs = OxmlElement("w:szCs"); szcs.set(qn("w:val"), str(int(BODY_PT*2))); st.element.get_or_add_rPr().append(szcs)
    for name, size, before, after, color in (("Heading 1", 15, 14, 5, "1F3864"), ("Heading 2", 12.5, 9, 3, "2F5496")):
        h = d.styles[name]; h.font.size = Pt(size); h.font.bold = True; h.font.name = LATIN_FONT
        h.font.color.rgb = RGBColor.from_string(color)
        h.paragraph_format.space_before = Pt(before); h.paragraph_format.space_after = Pt(after)
        h.paragraph_format.keep_with_next = True
        rf = h.element.get_or_add_rPr().find(qn("w:rFonts"))
        for a in ("w:ascii", "w:hAnsi"): rf.set(qn(a), LATIN_FONT)
        for a in ("w:cs", "w:eastAsia"): rf.set(qn(a), FA_FONT)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rf.get(qn(a)) is not None: del rf.attrib[qn(a)]
        h.element.get_or_add_rPr().append(OxmlElement("w:bCs"))
        szc = OxmlElement("w:szCs"); szc.set(qn("w:val"), str(int(size * 2))); h.element.get_or_add_rPr().append(szc)
    return d


def find_image(name, md_dir, root):
    cands = [md_dir / name, root / name.lstrip("./"), (md_dir / name).resolve()]
    for c in cands:
        if c.is_file(): return c
    base = Path(name).name
    for sub in ("diagrams", "docs", "docs/generated", "docs/figures", "assets", "output", "."):
        c = root / sub / base
        if c.is_file(): return c
    hits = [h for h in root.rglob(base) if ".git" not in h.parts]
    if hits: return hits[0]
    raise FileNotFoundError("Missing image " + name)


def add_picture(d, path, caption, keep=False):
    with Image.open(path) as im: w, h = im.size
    max_w, max_h = 6.0, 4.1
    scale = min(max_w / (w / 96), max_h / (h / 96), 99)
    wi = min(max_w, max_h * w / h) if w / h < max_w / max_h else max_w
    wi = min(wi, max_w)
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = bool(caption) or keep; p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(path), width=Inches(wi))
    if caption:
        c = d.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER; c.paragraph_format.space_after = Pt(8)
        set_bidi(c); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_inline(c, caption, size=9, italic=True, color="404040")


def add_table(d, rows):
    ncols = max(map(len, rows))
    t = d.add_table(rows=0, cols=ncols); t.style = "Table Grid"; t.autofit = False
    tblPr = t._tbl.tblPr
    bv = OxmlElement("w:bidiVisual"); bv.set(qn("w:val"), "1"); tblPr.append(bv)
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    weights = []
    for ci in range(ncols):
        L = [len(re.sub(r"[*`]", "", r[ci])) if ci < len(r) else 0 for r in rows]
        weights.append(min(max(max(L), 7), 42) ** 0.85)
    tot = sum(weights); widths = [Inches(TEXT_W * w / tot) for w in weights]
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        trPr = t.rows[-1]._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); trPr.append(cs)
        if ri == 0:
            th = OxmlElement("w:tblHeader"); trPr.append(th)
        for ci, cell in enumerate(cells):
            cell.width = widths[ci]
            p = cell.paragraphs[0]; set_bidi(p)
            p.paragraph_format.space_after = Pt(1); p.paragraph_format.space_before = Pt(1); p.paragraph_format.line_spacing = 1.0
            add_inline(p, row[ci] if ci < len(row) else "", size=9.5, bold=True if ri == 0 else None)
            if ri == 0: set_cell_shading(cell, "D9E2F3")
    sp = d.add_paragraph(); sp.paragraph_format.space_after = Pt(2)
    for r in sp.runs: pass
    sp.paragraph_format.line_spacing = Pt(4)


def add_code(d, lines):
    for i, line in enumerate(lines):
        p = d.add_paragraph(); set_bidi(p, rtl=False)
        pf = p.paragraph_format; pf.space_after = Pt(0); pf.space_before = Pt(0); pf.line_spacing = 1.0
        pf.left_indent = Inches(0.1); pf.right_indent = Inches(0.1)
        pf.keep_together = True
        if i < len(lines) - 1 and len(lines) <= 22: pf.keep_with_next = True
        par_shading(p, "F2F2F2")
        r = p.add_run(line.replace("\t", "    ") if line else " ")
        style_run(r, "x", mono=True, size=8.5)
    gap = d.add_paragraph(); gap.paragraph_format.space_after = Pt(0); gap.paragraph_format.line_spacing = Pt(5)


def parse(md_text):
    """-> list of blocks (kind, payload)"""
    lines = md_text.splitlines(); out = []; i = 0
    while i < len(lines):
        ln = lines[i]; s = ln.strip()
        if not s or COMMENT.match(ln): i += 1; continue
        if s.startswith("```"):
            i += 1; buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"): buf.append(lines[i].rstrip()); i += 1
            i += 1; out.append(("code", buf)); continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) or c == "" for c in cells) or not any(cells):
                    rows.append(cells)
                i += 1
            out.append(("table", rows)); continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m: out.append((f"h{len(m.group(1))}", m.group(2).strip())); i += 1; continue
        m = IMG.match(s)
        if m: out.append(("img", (m.group(1), m.group(2)))); i += 1; continue
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"): buf.append(lines[i].strip().lstrip(">").strip()); i += 1
            out.append(("quote", " ".join(buf))); continue
        if re.match(r"^([-*]|\d+\.)\s+", s):
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                items.append((len(mm.group(1)) >= 2, mm.group(2), mm.group(3))); i += 1
            out.append(("list", items)); continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4}\s|```|\||>|!\[|([-*]|\d+\.)\s)", lines[i].strip()) and not COMMENT.match(lines[i]):
            buf.append(lines[i].strip()); i += 1
        if not buf: buf = [s]; i += 1
        out.append(("para", " ".join(buf)))
    return out


def render(blocks, md_dir, root, toc_pages=None):
    d = setup_document(); first_h1 = True; in_toc = False
    for bi, (kind, val) in enumerate(blocks):
        if kind == "h1":
            p = d.add_paragraph(); set_bidi(p); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(8); p.paragraph_format.space_before = Pt(6)
            add_inline(p, val, size=20, bold=True, color="1F3864"); in_toc = False
        elif kind in ("h2", "h3", "h4"):
            if val.lower().startswith("table of contents"): val = "فهرست مطالب"; in_toc = True
            else: in_toc = False
            p = d.add_paragraph(style="Heading 1" if kind == "h2" else "Heading 2"); set_bidi(p)
            add_inline(p, val)
            if kind == "h4": pass
        elif kind == "para":
            p = d.add_paragraph(); set_bidi(p); add_inline(p, val)
            if re.fullmatch(r"\*[^*].*[^*]\*", val): p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if re.fullmatch(r"\*[^*].*[^*]\*", val) and not ARABIC.search(val) is None:
                for r in p.runs: r.font.size = Pt(9)
        elif kind == "quote":
            p = d.add_paragraph(); set_bidi(p); par_shading(p, "EAF1FB", "2F5496")
            p.paragraph_format.left_indent = Inches(.1); p.paragraph_format.right_indent = Inches(.1)
            p.paragraph_format.space_before = Pt(3); p.paragraph_format.space_after = Pt(8)
            add_inline(p, val, size=10.5)
        elif kind == "list":
            for nested, marker, text in val:
                text_clean = text
                if in_toc:
                    mt = TOC_ITEM.match(text)
                    if mt:
                        title = mt.group(1).strip()
                        pg = (toc_pages or {}).get(title)
                        text_clean = f"{title} (ص {pg})" if pg else title
                p = d.add_paragraph(); set_bidi(p)
                pf = p.paragraph_format; pf.space_after = Pt(1.5 if in_toc else 3)
                pf.right_indent = Inches(0.32 + (0.28 if nested else 0)); pf.first_line_indent = Inches(-0.2)
                bullet = "•" if not marker[0].isdigit() else marker
                add_inline(p, f"{bullet}  " + text_clean, size=10.5 if in_toc else None)
        elif kind == "table":
            add_table(d, val)
        elif kind == "code":
            add_code(d, val)
        elif kind == "img":
            nxt = blocks[bi + 1] if bi + 1 < len(blocks) else None
            has_caption_after = bool(nxt and nxt[0] == "para" and re.match(r"^\*Figure \d+[.:]", nxt[1]))
            add_picture(d, find_image(val[1], md_dir, root), None if has_caption_after else val[0], keep=has_caption_after)
    return d


def to_pdf(docx, outdir):
    prof = Path(tempfile.mkdtemp(prefix="lo-prof-"))
    subprocess.run(["libreoffice", "--headless", "--norestore", "--nodefault", "--nofirststartwizard",
                    f"-env:UserInstallation=file://{prof}", "--convert-to", "pdf", "--outdir", str(outdir), str(docx)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.rmtree(prof, ignore_errors=True)
    return Path(outdir) / (Path(docx).stem + ".pdf")


def outline_pages(pdf):
    rd = PdfReader(str(pdf)); res = {}
    def walk(items):
        for it in items:
            if isinstance(it, list): walk(it)
            else:
                try: res.setdefault(it.title.strip(), rd.get_destination_page_number(it) + 1)
                except Exception: pass
    walk(rd.outline)
    return res


def build(md_path, stem, root):
    md_path = Path(md_path); text = md_path.read_text(encoding="utf-8")
    blocks = parse(text)
    with tempfile.TemporaryDirectory(prefix="fa-build-") as tmp:
        tmp = Path(tmp)
        d = render(blocks, md_path.parent, root); a = tmp / "pass1.docx"; d.save(a)
        pages = outline_pages(to_pdf(a, tmp))
        d = render(blocks, md_path.parent, root, toc_pages=pages)
        out_docx = Path(str(stem) + ".docx"); out_docx.parent.mkdir(parents=True, exist_ok=True)
        d.save(out_docx)
        pdf = to_pdf(out_docx, tmp)
        shutil.copy2(pdf, Path(str(stem) + ".pdf"))
        n = len(PdfReader(str(pdf)).pages)
    print(f"{out_docx.name}: {n} pages"); return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("source"); ap.add_argument("stem"); ap.add_argument("--root", default=".")
    a = ap.parse_args(); build(a.source, a.stem, Path(a.root).resolve())
