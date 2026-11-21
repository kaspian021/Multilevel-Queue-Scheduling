#!/usr/bin/env python3
"""Build extended bilingual reports from original DOCX plus Markdown appendices."""
from __future__ import annotations
import os,re,shutil,subprocess,tempfile
from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches,Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docxcompose.composer import Composer
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/"docs"
STEMS={"Exercise-1-Algorithm-Introduction":"REPORT","Exercise-2-MLQ-EDF-RM-Comparison":"COMPARISON","Exercise-3-EDF-RM-Manual-Scheduling":"MANUAL_SOLUTION","Exercise-4-Dekker-Peterson-Semaphore-Monitor":"COMPARISON","Exercise-6-Paper-And-Seminar":"PAPER","Exercise-7-Readers-Writers-Comparison":"REPORT"}
MARKER=re.compile(r"<!--\s*page\s+\d+\s*-->"); IMG=re.compile(r"!\[([^\]]*)\]\(([^)]+)\)"); INLINE=re.compile(r"(\*\*.+?\*\*|\x60.+?\x60|\*.+?\*)")
def rtl(p):
 pp=p._p.get_or_add_pPr(); b=pp.find(qn("w:bidi"))
 if b is None:b=OxmlElement("w:bidi");pp.append(b)
 b.set(qn("w:val"),"1");p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
 for r in p.runs:
  rp=r._r.get_or_add_rPr();x=rp.find(qn("w:rtl"))
  if x is None:x=OxmlElement("w:rtl");rp.append(x)
  x.set(qn("w:val"),"1");f=rp.find(qn("w:rFonts"))
  if f is None:f=OxmlElement("w:rFonts");rp.append(f)
  f.set(qn("w:ascii"),"Noto Naskh Arabic");f.set(qn("w:hAnsi"),"Noto Naskh Arabic");f.set(qn("w:cs"),"Noto Naskh Arabic")
def runs(p,s,is_rtl):
 pos=0
 for m in INLINE.finditer(s):
  if m.start()>pos:p.add_run(s[pos:m.start()])
  t=m.group()
  if t.startswith("**"):r=p.add_run(t[2:-2]);r.bold=True
  elif t.startswith(chr(96)):r=p.add_run(t[1:-1]);r.font.name="DejaVu Sans Mono";r.font.size=Pt(9)
  else:r=p.add_run(t[1:-1]);r.italic=True
  pos=m.end()
 if pos<len(s):p.add_run(s[pos:])
 if is_rtl:rtl(p)
def appendix_docx(md,out,lang):
 text=md.read_text(encoding="utf-8"); marks=list(MARKER.finditer(text))
 if not marks:raise RuntimeError("No page markers in "+str(md))
 d=Document();sec=d.sections[0];sec.page_width=Inches(8.27);sec.page_height=Inches(11.69)
 sec.top_margin=Inches(.72);sec.bottom_margin=Inches(.72);sec.left_margin=Inches(.78);sec.right_margin=Inches(.78)
 fp=sec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER;rr=fp.add_run()
 for tag,attrs,val in [("w:fldChar",{"w:fldCharType":"begin"},None),("w:instrText",{"xml:space":"preserve"}," PAGE "),("w:fldChar",{"w:fldCharType":"separate"},None),("w:t",{},"1"),("w:fldChar",{"w:fldCharType":"end"},None)]:
  el=OxmlElement(tag)
  for k,v in attrs.items():el.set(qn(k),v)
  if val is not None:el.text=val
  rr._r.append(el)
 is_rtl=lang=="FA";d.styles["Normal"].font.name="Noto Naskh Arabic" if is_rtl else "Aptos";d.styles["Normal"].font.size=Pt(11)
 for i,m in enumerate(marks):
  ch=text[m.end():(marks[i+1].start() if i+1<len(marks) else len(text))].strip(); first=True
  for block in re.split(r"\n\s*\n",ch):
   block=block.strip()
   if not block:continue
   lines=[x.strip() for x in block.splitlines() if x.strip()]
   if lines[0].startswith("|") and any("---" in x for x in lines[1:3]):
    rows=[]
    for line in lines:
     compact=line.replace("|","").strip()
     if re.match(r"^:?-{2,}",compact):continue
     cells=[x.strip() for x in line.strip().strip("|").split("|")]
     if cells:rows.append(cells)
    if rows:
     t=d.add_table(rows=0,cols=max(map(len,rows)));t.style="Table Grid"
     if is_rtl:
      bv=OxmlElement("w:bidiVisual");bv.set(qn("w:val"),"1");t._tbl.tblPr.append(bv)
     for ri,row in enumerate(rows):
      cells=t.add_row().cells
      for ci,c in enumerate(cells):
       p=c.paragraphs[0];runs(p,row[ci] if ci<len(row) else "",is_rtl)
       if ri==0:
        for r in p.runs:r.bold=True
    continue
   if len(lines)==1 and IMG.fullmatch(lines[0]):
    mt=IMG.fullmatch(lines[0]);alt,rel=mt.group(1),mt.group(2);image=(md.parent/rel).resolve()
    if not image.is_file():image=(ROOT/rel.lstrip("./")).resolve()
    if not image.is_file():raise FileNotFoundError("Missing image "+rel)
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_together=True
    p.add_run().add_picture(str(image),width=Inches(6.15))
    if alt:
     cap=d.add_paragraph();cap.alignment=WD_ALIGN_PARAGRAPH.CENTER;runs(cap,alt,is_rtl)
    continue
   if lines[0].startswith("#"):
    lev=min(3,len(lines[0])-len(lines[0].lstrip("#")));p=d.add_paragraph(style=f"Heading {lev}")
    if first:p.paragraph_format.page_break_before=True;first=False
    runs(p,lines[0].lstrip("#").strip(),is_rtl);continue
   if lines[0].startswith(("- ","* ")):
    for line in lines:
     if line.startswith(("- ","* ")):runs(d.add_paragraph(style="List Bullet"),line[2:],is_rtl)
    continue
   p=d.add_paragraph();p.paragraph_format.space_after=Pt(7);p.paragraph_format.line_spacing=1.12;runs(p," ".join(lines),is_rtl)
 d.save(out)
def build(stem,lang):
 name=f"{stem}_{lang}";docx=DOCS/f"{name}.docx";md=DOCS/f"APPENDIX_{lang}.md"
 base=DOCS/".base";base.mkdir(parents=True,exist_ok=True);original=base/f"{name}.docx"
 if not md.is_file():raise FileNotFoundError(md)
 if not original.exists():
  if not docx.is_file():raise FileNotFoundError(docx)
  shutil.copy2(docx,original)
 with tempfile.TemporaryDirectory(prefix="report-build-") as tmp:
  tmp=Path(tmp);add=tmp/f"{name}_appendix.docx";merged=tmp/f"{name}.docx";pdfdir=tmp/"pdf";pdfdir.mkdir()
  appendix_docx(md,add,lang);c=Composer(Document(original));c.append(Document(add));c.save(merged)
  profile=tmp/"lo-profile"
  subprocess.run(["libreoffice","--headless","--norestore","--nodefault","--nofirststartwizard",f"-env:UserInstallation=file://{profile}","--convert-to","pdf","--outdir",str(pdfdir),str(merged)],check=True)
  pdf=pdfdir/f"{name}.pdf"
  if not pdf.is_file() or pdf.stat().st_size<10000:raise RuntimeError("PDF generation failed")
  pages=len(PdfReader(str(pdf)).pages);print(f"VERIFIED {name}: {pages} pages",flush=True)
  if pages<=40:raise RuntimeError(f"{name}: {pages} pages, expected >40")
  shutil.copy2(merged,docx);shutil.copy2(pdf,DOCS/f"{name}.pdf");return pages
def main():
 branch=os.environ.get("GITHUB_REF_NAME") or subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip()
 if branch not in STEMS:raise SystemExit("No report mapping for "+branch)
 stem=STEMS[branch];counts={l:build(stem,l) for l in ("FA","EN")}
 print("Verified pages",branch,counts,flush=True)
if __name__=="__main__":main()
