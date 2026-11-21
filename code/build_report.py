"""Build the 38-section Exercise 8 Markdown report as a formatted Persian DOCX."""
from __future__ import annotations
import re
from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "REPORT_FA.md"
OUTPUT = ROOT / "docs" / "REPORT_FA.docx"
FONT = "Noto Naskh Arabic"
CODE_FONT = "DejaVu Sans Mono"


def set_rtl(p, rtl=True):
    pPr = p._p.get_or_add_pPr()
    bidi = pPr.find(qn("w:bidi"))
    if bidi is None:
        bidi = OxmlElement("w:bidi"); pPr.append(bidi)
    bidi.set(qn("w:val"), "1" if rtl else "0")
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if rtl else WD_ALIGN_PARAGRAPH.LEFT


def set_font(run, name=FONT, size=8.7, bold=False, italic=False, rtl=True):
    run.font.name = name; run.font.size = Pt(size)
    run.bold = bold; run.italic = italic
    rPr = run._element.get_or_add_rPr()
    rf = rPr.rFonts
    if rf is None:
        rf = OxmlElement("w:rFonts"); rPr.insert(0, rf)
    for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
        rf.set(qn(f"w:{attr}"), name)
    if rtl:
        el = rPr.find(qn("w:rtl"))
        if el is None: el = OxmlElement("w:rtl"); rPr.append(el)
        el.set(qn("w:val"), "1")


def clean(text):
    text = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text.replace("**", "").replace("`", "").replace("~~", "").strip()


def shade(cell, fill="EAF0F6"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), fill); tcPr.append(shd)


def add_table(doc, rows):
    if len(rows) < 2: return
    parsed = [[clean(c.strip()) for c in row.strip().strip("|").split("|")] for row in rows]
    parsed = [r for r in parsed if not all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in r)]
    if not parsed: return
    ncols = max(len(r) for r in parsed)
    table = doc.add_table(rows=1, cols=ncols)
    table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.CENTER
    bidi = OxmlElement("w:bidiVisual"); bidi.set(qn("w:val"), "1"); table._tbl.tblPr.append(bidi)
    for ri, row in enumerate(parsed):
        cells = table.rows[0].cells if ri == 0 else table.add_row().cells
        for ci in range(ncols):
            c = cells[ci]; c.text = ""; p = c.paragraphs[0]; set_rtl(p)
            p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.line_spacing = .92
            r = p.add_run(row[ci] if ci < len(row) else "")
            set_font(r, size=7.1, bold=(ri == 0))
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if ri == 0: shade(c, "DCE6F1")
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_code(doc, code):
    table = doc.add_table(rows=1, cols=1); table.style = "Table Grid"
    cell = table.cell(0, 0); shade(cell, "F4F5F6"); cell.text = ""
    for j, line in enumerate(code.splitlines()):
        p = cell.paragraphs[0] if j == 0 else cell.add_paragraph()
        set_rtl(p, False); p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = .9
        r = p.add_run(line or " "); set_font(r, CODE_FONT, 6.1, rtl=False)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_para(doc, text, kind="body"):
    p = doc.add_paragraph(); set_rtl(p, kind != "code")
    fmt = p.paragraph_format
    fmt.space_after = Pt(2 if kind == "body" else 1)
    fmt.space_before = Pt(0); fmt.line_spacing = .96
    fmt.keep_together = True
    if kind == "bullet":
        p.style = "List Bullet"; set_rtl(p, True)
    r = p.add_run(clean(text))
    set_font(r, size={"body":8.4,"bullet":8.0,"note":7.7,"subhead":9.2,"caption":7.3}.get(kind,8.4),
              italic=kind == "caption", bold=kind == "subhead")
    return p


def add_image(doc, line):
    m = re.search(r"\]\(([^)]+)\)", line)
    if not m: return
    path = (ROOT / m.group(1)).resolve()
    if not path.exists():
        add_para(doc, f"[تصویر تولیدنشده: {m.group(1)}]", "note"); return
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(1); p.paragraph_format.space_before = Pt(1)
    p.add_run().add_picture(str(path), width=Cm(12.8))
    alt = re.match(r"!\[([^]]*)\]", line)
    if alt and alt.group(1): add_para(doc, alt.group(1), "caption")


def parse_page(doc, lines, index):
    title = lines[0].strip()[3:].strip() if lines else f"صفحه {index}"
    p = doc.add_paragraph(); set_rtl(p)
    p.paragraph_format.space_after = Pt(5); p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(title); set_font(r, size=12.0, bold=True)
    i = 1
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == "---": i += 1; continue
        if line.startswith("```"):
            code=[]; i += 1
            while i < len(lines) and lines[i].strip() != "```": code.append(lines[i].rstrip()); i += 1
            add_code(doc, "\n".join(code)); i += 1; continue
        if line.startswith("!["):
            add_image(doc, line); i += 1; continue
        if line.startswith("|"):
            table_rows=[]
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_rows.append(lines[i].strip()); i += 1
            add_table(doc, table_rows); continue
        if line.startswith(">"):
            add_para(doc, line.lstrip("> "), "note"); i += 1; continue
        if line.startswith("- ") or line.startswith("* "):
            add_para(doc, line[2:], "bullet"); i += 1; continue
        if line.startswith("### "):
            add_para(doc, line[4:], "subhead"); i += 1; continue
        if line.startswith("# "):
            add_para(doc, line[2:], "subhead"); i += 1; continue
        if re.match(r"^\*.+\*$", line):
            add_para(doc, line.strip("*"), "caption"); i += 1; continue
        para=[line]; i += 1
        while i < len(lines):
            nxt=lines[i].strip()
            if (not nxt or nxt == "---" or nxt.startswith(("```","![","> ","- ","* ","|","### ","# "))): break
            para.append(nxt); i += 1
        add_para(doc, " ".join(para), "body")


def main():
    text = SOURCE.read_text(encoding="utf-8")
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if re.match(r"^## صفحه \d+:", line)]
    if len(starts) != 38:
        raise SystemExit(f"Expected 38 page sections, found {len(starts)}")
    sections=[]
    for j, start in enumerate(starts):
        end = starts[j+1] if j+1 < len(starts) else len(lines)
        page = lines[start:end]
        while page and page[-1].strip() == "---": page.pop()
        sections.append(page)
    doc=Document(); sec=doc.sections[0]
    sec.page_width=Cm(21); sec.page_height=Cm(29.7)
    sec.top_margin=Cm(1.25); sec.bottom_margin=Cm(1.25)
    sec.left_margin=Cm(1.35); sec.right_margin=Cm(1.35)
    sec.header_distance=Cm(.5); sec.footer_distance=Cm(.5)
    normal=doc.styles["Normal"]; normal.font.name=FONT; normal.font.size=Pt(8.4)
    normal._element.rPr.rFonts.set(qn("w:cs"),FONT); normal._element.rPr.rFonts.set(qn("w:eastAsia"),FONT)
    header=sec.header.paragraphs[0]; set_rtl(header)
    hr=header.add_run("تمرین ۸ | کاربرد MLQ در مسئله فیلسوفان غذاخور"); set_font(hr,size=7.2)
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    set_rtl(footer,False); fr=footer.add_run("Exercise 8 | Page "); set_font(fr,CODE_FONT,7,rtl=False)
    fld=OxmlElement("w:fldSimple"); fld.set(qn("w:instr"),"PAGE"); footer._p.append(fld)
    for number, page in enumerate(sections,1):
        if number > 1: doc.add_page_break()
        parse_page(doc,page,number)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True); doc.save(OUTPUT)
    print(f"Built {OUTPUT} from {len(sections)} sections")

if __name__ == "__main__": main()
