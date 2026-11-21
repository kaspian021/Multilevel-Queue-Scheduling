#!/usr/bin/env python3
"""Append branch-specific appendices to reports and verify actual PDF page counts."""
from __future__ import annotations
import os, re, shutil, subprocess, tempfile
from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docxcompose.composer import Composer
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]; DOCS=ROOT/"docs"
REPORT_STEMS={"Exercise-1-Algorithm-Introduction":"REPORT","Exercise-2-MLQ-EDF-RM-Comparison":"COMPARISON","Exercise-3-EDF-RM-Manual-Scheduling":"MANUAL_SOLUTION","Exercise-4-Dekker-Peterson-Semaphore-Monitor":"COMPARISON","Exercise-6-Paper-And-Seminar":"PAPER","Exercise-7-Readers-Writers-Comparison":"REPORT"}
def set_rtl(p):
    pp=p._p.get_or_add_pPr(); b=pp.find(qn("w:bidi"))
    if b is None: b=OxmlElement("w:bidi"); pp.append(b)
    b.set(qn("w:val"),"1"); p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    for r in p.runs:
        rp=r._r.get_or_add_rPr(); rtl=rp.find(qn("w:rtl"))
        if rtl is None: rtl=OxmlElement("w:rtl"); rp.append(rtl)
        rtl.set(qn("w:val"),"1"); f=rp.find(qn("w:rFonts"))
        if f is None: f=OxmlElement("w:rFonts"); rp.append(f)
        f.set(qn("w:ascii"),"Noto Naskh Arabic"); f.set(qn("w:hAnsi"),"Noto Naskh Arabic"); f.set(qn("w:cs"),"Noto Naskh Arabic")
def patch_rtl(path):
    d=Document(path)
    for p in d.paragraphs:
        if re.search(r"[\u0600-\u06FF]",p.text): set_rtl(p)
    for t in d.tables:
        bv=t._tbl.tblPr.find(qn("w:bidiVisual"))
        if bv is None: bv=OxmlElement("w:bidiVisual"); t._tbl.tblPr.append(bv)
        bv.set(qn("w:val"),"1")
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if re.search(r"[\u0600-\u06FF]",p.text): set_rtl(p)
    d.save(path)
def run(cmd,cwd=None):
    print("+"," ".join(map(str,cmd)),flush=True); subprocess.run(list(map(str,cmd)),cwd=cwd,check=True)
def build_one(stem,lang):
    name=f"{stem}_{lang}"; current=DOCS/f"{name}.docx"; appendix=DOCS/f"APPENDIX_{lang}.md"
    base=DOCS/".base"; base.mkdir(parents=True,exist_ok=True); original=base/f"{name}.docx"
    if not appendix.is_file(): raise FileNotFoundError(appendix)
    if not original.exists():
        if not current.is_file(): raise FileNotFoundError(current)
        shutil.copy2(current,original)
    src=appendix.read_text(encoding="utf-8")
    src=re.sub(r"<!--\s*page\s+\d+\s*-->",r"\n\\newpage\n",src); src="\\newpage\n\n"+src
    with tempfile.TemporaryDirectory(prefix="report-build-") as tmp:
        tmp=Path(tmp); pdfdir=tmp/"pdf"; pdfdir.mkdir(); prepared=DOCS/f".appendix_build_{lang}.md"
        appendix_docx=tmp/f"{name}_appendix.docx"; merged=tmp/f"{name}.docx"
        try:
            prepared.write_text(src,encoding="utf-8")
            run(["pandoc",prepared.name,"--from=markdown+raw_tex","--to=docx",f"--reference-doc={original.name}",f"--output={appendix_docx}","--resource-path=.:.."],cwd=DOCS)
        finally: prepared.unlink(missing_ok=True)
        if lang=="FA": patch_rtl(appendix_docx)
        composer=Composer(Document(original)); composer.append(Document(appendix_docx)); composer.save(merged)
        profile=tmp/"lo-profile"
        run(["libreoffice","--headless","--norestore","--nodefault","--nofirststartwizard",f"-env:UserInstallation=file://{profile}","--convert-to","pdf","--outdir",str(pdfdir),str(merged)])
        pdf=pdfdir/f"{name}.pdf"
        if not pdf.is_file() or pdf.stat().st_size<10000: raise RuntimeError(f"PDF conversion failed: {pdf}")
        pages=len(PdfReader(str(pdf)).pages); print(f"VERIFIED {name}: {pages} PDF pages",flush=True)
        if pages<=40: raise RuntimeError(f"{name} has {pages} pages; expected more than 40")
        shutil.copy2(merged,current); shutil.copy2(pdf,DOCS/f"{name}.pdf"); return pages
def main():
    branch=os.environ.get("GITHUB_REF_NAME") or subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip()
    if branch not in REPORT_STEMS: raise SystemExit(f"No report mapping for {branch!r}")
    stem=REPORT_STEMS[branch]; counts={l:build_one(stem,l) for l in ("FA","EN")}
    print(f"Final page counts for {branch}: {counts}",flush=True)
if __name__=="__main__": main()
