#!/usr/bin/env python3
"""Append branch-specific appendices to reports and verify actual PDF page counts."""
from __future__ import annotations
import os, re, shutil, subprocess, tempfile
from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docxcompose.composer import Composer
from pypdf import PdfReader
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_fa_report import build as build_fa_markdown
ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/"docs"
REPORT_STEMS={"Exercise-1-Algorithm-Introduction":"REPORT","Exercise-2-MLQ-EDF-RM-Comparison":"COMPARISON","Exercise-3-EDF-RM-Manual-Scheduling":"MANUAL_SOLUTION","Exercise-4-Dekker-Peterson-Semaphore-Monitor":"COMPARISON","Exercise-6-Paper-And-Seminar":"PAPER","Exercise-7-Readers-Writers-Comparison":"REPORT"}
PAGE_MARKER=re.compile(r"<!--\s*page\s+\d+\s*-->"); IMAGE=re.compile(r"!\[([^\]]*)\]\(([^)]+)\)"); INLINE=re.compile(r"(\*\*.+?\*\*|\x60.+?\x60|\*.+?\*)")
def set_rtl(p):
 ppr=p._p.get_or_add_pPr(); bidi=ppr.find(qn("w:bidi"))
 if bidi is None: bidi=OxmlElement("w:bidi"); ppr.append(bidi)
 bidi.set(qn("w:val"),"1"); p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
 for run in p.runs:
  rpr=run._r.get_or_add_rPr(); rtl=rpr.find(qn("w:rtl"))
  if rtl is None: rtl=OxmlElement("w:rtl"); rpr.append(rtl)
  rtl.set(qn("w:val"),"1"); fonts=rpr.find(qn("w:rFonts"))
  if fonts is None: fonts=OxmlElement("w:rFonts"); rpr.append(fonts)
  fonts.set(qn("w:ascii"),"Noto Naskh Arabic"); fonts.set(qn("w:hAnsi"),"Noto Naskh Arabic"); fonts.set(qn("w:cs"),"Noto Naskh Arabic")
def add_runs(p,text,rtl=False):
 pos=0
 for m in INLINE.finditer(text):
  if m.start()>pos: p.add_run(text[pos:m.start()])
  token=m.group()
  if token.startswith("**"): r=p.add_run(token[2:-2]); r.bold=True
  elif token.startswith(chr(96)): r=p.add_run(token[1:-1]); r.font.name="DejaVu Sans Mono"; r.font.size=Pt(9)
  else: r=p.add_run(token[1:-1]); r.italic=True
  pos=m.end()
 if pos<len(text): p.add_run(text[pos:])
 if rtl: set_rtl(p)
def make_appendix(md,out,lang):
 text=md.read_text(encoding="utf-8"); markers=list(PAGE_MARKER.finditer(text))
 if not markers: raise RuntimeError(f"No page markers in {md}")
 doc=Document(); sec=doc.sections[0]; sec.page_width=Inches(8.27); sec.page_height=Inches(11.69)
 sec.top_margin=Inches(.72); sec.bottom_margin=Inches(.72); sec.left_margin=Inches(.78); sec.right_margin=Inches(.78)
 foot=sec.footer.paragraphs[0]; foot.alignment=WD_ALIGN_PARAGRAPH.CENTER; run=foot.add_run()
 for tag,attrs,txt in [("w:fldChar",{"w:fldCharType":"begin"},None),("w:instrText",{"xml:space":"preserve"}," PAGE "),("w:fldChar",{"w:fldCharType":"separate"},None),("w:t",{},"1"),("w:fldChar",{"w:fldCharType":"end"},None)]:
  el=OxmlElement(tag)
  for k,v in attrs.items(): el.set(qn(k),v)
  if txt is not None: el.text=txt
  run._r.append(el)
 rtl=lang=="FA"; doc.styles["Normal"].font.name="Noto Naskh Arabic" if rtl else "Aptos"; doc.styles["Normal"].font.size=Pt(11)
 for i,m in enumerate(markers):
  chunk=text[m.end():(markers[i+1].start() if i+1<len(markers) else len(text))].strip()
  first_heading=True
  for block in re.split(r"\n\s*\n",chunk):
   block=block.strip()
   if not block: continue
   lines=[x.strip() for x in block.splitlines() if x.strip()]
   if lines and lines[0].startswith("|") and any("---" in x for x in lines[1:3]):
    rows=[]
    for line in lines:
     compact=line.replace("|","").strip()
     if re.match(r"^:?-{2,}",compact): continue
     cells=[x.strip() for x in line.strip().strip("|").split("|")]
     if cells: rows.append(cells)
    if rows:
     table=doc.add_table(rows=0,cols=max(map(len,rows))); table.style="Table Grid"
     if rtl:
      bv=OxmlElement("w:bidiVisual"); bv.set(qn("w:val"),"1"); table._tbl.tblPr.append(bv)
     for ri,row in enumerate(rows):
      cells=table.add_row().cells
      for ci,cell in enumerate(cells):
       p=cell.paragraphs[0]; add_runs(p,row[ci] if ci<len(row) else "",rtl)
       if ri==0:
        for r in p.runs: r.bold=True
     continue
   if len(lines)==1 and IMAGE.fullmatch(lines[0]):
    im=IMAGE.fullmatch(lines[0]); alt,rel=im.group(1),im.group(2)
    img=(md.parent/rel).resolve()
    if not img.is_file(): img=(ROOT/rel.lstrip("./")).resolve()
    if not img.is_file(): raise FileNotFoundError(f"Missing appendix image {rel}")
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_together=True
    p.add_run().add_picture(str(img),width=Inches(6.15))
    if alt:
     cap=doc.add_paragraph(); cap.alignment=WD_ALIGN_PARAGRAPH.CENTER; add_runs(cap,alt,rtl)
    continue
   if lines[0].startswith("#"):
    level=min(3,len(lines[0])-len(lines[0].lstrip("#"))); p=doc.add_paragraph(style=f"Heading {level}")
    if first_heading: p.paragraph_format.page_break_before=True; first_heading=False
    add_runs(p,lines[0].lstrip("#").strip(),rtl); continue
   if lines[0].startswith(("- ","* ")):
    for line in lines:
     if line.startswith(("- ","* ")): add_runs(doc.add_paragraph(style="List Bullet"),line[2:],rtl)
    continue
   p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(7); p.paragraph_format.line_spacing=1.12
   add_runs(p," ".join(lines),rtl)
 doc.save(out)
def build_one(stem,lang):
 name=f"{stem}_{lang}"; current=DOCS/f"{name}.docx"; appendix=DOCS/f"APPENDIX_{lang}.md"
 base=DOCS/".base"; base.mkdir(parents=True,exist_ok=True); original=base/f"{name}.docx"
 if not appendix.is_file(): raise FileNotFoundError(appendix)
 if not original.exists():
  if not current.is_file(): raise FileNotFoundError(current)
  shutil.copy2(current,original)
 with tempfile.TemporaryDirectory(prefix="report-build-") as tmp:
  tmp=Path(tmp); appendix_docx=tmp/f"{name}_appendix.docx"; merged=tmp/f"{name}.docx"; pdfdir=tmp/"pdf"; pdfdir.mkdir()
  make_appendix(appendix,appendix_docx,lang); composer=Composer(Document(original)); composer.append(Document(appendix_docx)); composer.save(merged)
  profile=tmp/"lo-profile"
  subprocess.run(["libreoffice","--headless","--norestore","--nodefault","--nofirststartwizard",f"-env:UserInstallation=file://{profile}","--convert-to","pdf","--outdir",str(pdfdir),str(merged)],check=True)
  pdf=pdfdir/f"{name}.pdf"
  if not pdf.is_file() or pdf.stat().st_size<10000: raise RuntimeError(f"PDF conversion failed: {pdf}")
  pages=len(PdfReader(str(pdf)).pages); print(f"VERIFIED {name}: {pages} PDF pages",flush=True)
  if pages<=40: raise RuntimeError(f"{name} has {pages} pages; expected more than 40")
  shutil.copy2(merged,current); shutil.copy2(pdf,DOCS/f"{name}.pdf"); return pages
def build(stem,lang):
 if lang=="FA":
  # Persian: laid out directly from the Markdown source (continuous RTL layout,
  # no forced page break per section, LTR code blocks, RTL tables).
  name=f"{stem}_{lang}";md=ROOT/f"{name}.md"
  if not md.is_file():raise FileNotFoundError(md)
  pages=build_fa_markdown(md,DOCS/name,ROOT)
  print(f"VERIFIED {name}: {pages} pages",flush=True)
  if not 20<=pages<=40:raise RuntimeError(f"{name}: {pages} pages, expected 20-40")
  return pages
 return build_one(stem,lang)
def main():
 branch=os.environ.get("GITHUB_REF_NAME") or subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip()
 if branch not in REPORT_STEMS: raise SystemExit(f"No report mapping for {branch!r}")
 stem=REPORT_STEMS[branch]; counts={l:build(stem,l) for l in ("FA","EN")}
 print(f"Final verified page counts for {branch}: {counts}",flush=True)
if __name__=="__main__": main()
