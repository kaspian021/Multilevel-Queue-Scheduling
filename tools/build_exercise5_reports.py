#!/usr/bin/env python3
"""Build Exercise 5 bilingual Word/PDF reports with charts derived from the actual simulator."""
from __future__ import annotations
import importlib.util, re, subprocess, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/"docs"
MARKER=re.compile(r"<!--\s*page\s+\d+\s*-->")
IMAGE=re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
INLINE=re.compile(r"(\*\*.+?\*\*|\x60.+?\x60|\*.+?\*)")

def load_simulator():
    path=ROOT/"exercise-5"/"mlq_sync_demo.py"
    spec=importlib.util.spec_from_file_location("exercise5_mlq_sync_demo",path)
    if spec is None or spec.loader is None: raise RuntimeError("Cannot load the Exercise 5 simulator")
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def generate_charts():
    module=load_simulator()
    scheduler=module.MLQScheduler(module.example_processes(),"semaphore",quantum=2)
    timeline=scheduler.run()
    metrics=scheduler.metrics()
    out=DOCS/"generated"; out.mkdir(parents=True,exist_ok=True)

    fig,ax=plt.subplots(figsize=(10,4.2))
    pids=list(metrics)
    ymap={pid:i for i,pid in enumerate(pids)}
    for s in timeline:
        ax.barh(ymap[s.pid],s.end-s.start,left=s.start,height=.58)
        ax.text((s.start+s.end)/2,ymap[s.pid],s.pid,ha="center",va="center",fontsize=9)
    ax.set_yticks(range(len(pids)),pids)
    ax.set_xlabel("Simulated time units")
    ax.set_title("MLQ execution trace produced by the simulator")
    ax.set_xlim(0,max(s.end for s in timeline)+.5)
    ax.grid(axis="x",alpha=.25)
    fig.tight_layout(); fig.savefig(out/"gantt.png",dpi=180); plt.close(fig)

    fig,ax=plt.subplots(figsize=(9,4.2))
    x=list(range(len(pids))); width=.36
    waiting=[metrics[pid]["waiting"] for pid in pids]
    turnaround=[metrics[pid]["turnaround"] for pid in pids]
    ax.bar([i-width/2 for i in x],waiting,width,label="Waiting")
    ax.bar([i+width/2 for i in x],turnaround,width,label="Turnaround")
    ax.set_xticks(x,pids); ax.set_ylabel("Simulated time units")
    ax.set_title("Waiting and turnaround by process")
    ax.legend(); ax.grid(axis="y",alpha=.25)
    fig.tight_layout(); fig.savefig(out/"metrics.png",dpi=180); plt.close(fig)

    qtotals={q:sum(s.end-s.start for s in timeline if s.queue==q) for q in (1,2,3)}
    fig,ax=plt.subplots(figsize=(7,4.5))
    ax.pie([qtotals[q] for q in (1,2,3)],labels=[f"Q{q}" for q in (1,2,3)],autopct="%1.1f%%",startangle=90)
    ax.set_title("CPU service share by queue")
    fig.tight_layout(); fig.savefig(out/"queue_share.png",dpi=180); plt.close(fig)
    return timeline,metrics,qtotals

def set_rtl(p):
    ppr=p._p.get_or_add_pPr(); bidi=ppr.find(qn("w:bidi"))
    if bidi is None: bidi=OxmlElement("w:bidi"); ppr.append(bidi)
    bidi.set(qn("w:val"),"1"); p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    for r in p.runs:
        rp=r._r.get_or_add_rPr(); rtl=rp.find(qn("w:rtl"))
        if rtl is None: rtl=OxmlElement("w:rtl"); rp.append(rtl)
        rtl.set(qn("w:val"),"1"); fonts=rp.find(qn("w:rFonts"))
        if fonts is None: fonts=OxmlElement("w:rFonts"); rp.append(fonts)
        fonts.set(qn("w:ascii"),"Noto Naskh Arabic")
        fonts.set(qn("w:hAnsi"),"Noto Naskh Arabic")
        fonts.set(qn("w:cs"),"Noto Naskh Arabic")

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

def add_footer(section):
    p=section.footer.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run()
    for tag,attrs,value in [
      ("w:fldChar",{"w:fldCharType":"begin"},None),
      ("w:instrText",{"xml:space":"preserve"}," PAGE "),
      ("w:fldChar",{"w:fldCharType":"separate"},None),
      ("w:t",{},"1"),
      ("w:fldChar",{"w:fldCharType":"end"},None),
    ]:
      el=OxmlElement(tag)
      for k,v in attrs.items(): el.set(qn(k),v)
      if value is not None: el.text=value
      r._r.append(el)

def build_docx(lang):
    md=DOCS/f"REPORT_{lang}.md"
    text=md.read_text(encoding="utf-8")
    markers=list(MARKER.finditer(text))
    if len(markers)<41: raise RuntimeError(f"Only {len(markers)} sections; require at least 41")
    rtl=(lang=="FA")
    doc=Document(); sec=doc.sections[0]
    sec.page_width=Inches(8.27); sec.page_height=Inches(11.69)
    sec.top_margin=Inches(.72); sec.bottom_margin=Inches(.72)
    sec.left_margin=Inches(.78); sec.right_margin=Inches(.78)
    add_footer(sec)
    doc.styles["Normal"].font.name="Noto Naskh Arabic" if rtl else "Aptos"
    doc.styles["Normal"].font.size=Pt(11)
    doc.core_properties.title="Exercise 5 — MLQ Synchronization"
    doc.core_properties.subject="Deterministic multilevel-queue scheduling trace and synchronization design"
    for idx,m in enumerate(markers):
        end=markers[idx+1].start() if idx+1<len(markers) else len(text)
        chunk=text[m.end():end].strip()
        first_heading=True
        for block in re.split(r"\n\s*\n",chunk):
            block=block.strip()
            if not block: continue
            lines=[x.strip() for x in block.splitlines() if x.strip()]
            if lines[0].startswith("|") and any("---" in x for x in lines[1:3]):
                rows=[]
                for line in lines:
                    compact=line.replace("|","").strip()
                    if re.match(r"^:?-{2,}",compact): continue
                    cells=[v.strip() for v in line.strip().strip("|").split("|")]
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
                                for run in p.runs: run.bold=True
                continue
            if len(lines)==1 and IMAGE.fullmatch(lines[0]):
                mt=IMAGE.fullmatch(lines[0]); alt,rel=mt.group(1),mt.group(2)
                image=(md.parent/rel).resolve()
                if not image.is_file(): raise FileNotFoundError(f"Missing image: {image}")
                p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.keep_together=True
                p.add_run().add_picture(str(image),width=Inches(6.15))
                if alt:
                    cap=doc.add_paragraph(); cap.alignment=WD_ALIGN_PARAGRAPH.CENTER; add_runs(cap,alt,rtl)
                continue
            if lines[0].startswith("#"):
                level=min(3,len(lines[0])-len(lines[0].lstrip("#")))
                p=doc.add_paragraph(style=f"Heading {level}")
                if idx>0 and first_heading: p.paragraph_format.page_break_before=True
                first_heading=False; add_runs(p,lines[0].lstrip("#").strip(),rtl)
                continue
            if lines[0].startswith(("- ","* ")):
                for line in lines:
                    if line.startswith(("- ","* ")): add_runs(doc.add_paragraph(style="List Bullet"),line[2:],rtl)
                continue
            p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(7); p.paragraph_format.line_spacing=1.12
            add_runs(p," ".join(lines),rtl)
    path=DOCS/f"REPORT_{lang}.docx"; doc.save(path); return path

def main():
    generate_charts()
    for lang in ("FA","EN"):
        docx=build_docx(lang)
        with tempfile_dir() as temp:
            profile=temp/"lo-profile"; out=temp/"pdf"; out.mkdir()
            subprocess.run(["libreoffice","--headless","--norestore","--nodefault","--nofirststartwizard",
             f"-env:UserInstallation=file://{profile}","--convert-to","pdf","--outdir",str(out),str(docx)],check=True)
            pdf=out/f"REPORT_{lang}.pdf"
            if not pdf.is_file(): raise RuntimeError(f"Missing PDF: {pdf}")
            pages=len(PdfReader(str(pdf)).pages)
            print(f"VERIFIED REPORT_{lang}: {pages} PDF pages",flush=True)
            if pages<=40: raise RuntimeError(f"REPORT_{lang} has {pages} pages; requirement is more than 40")
            (DOCS/f"REPORT_{lang}.pdf").write_bytes(pdf.read_bytes())

class tempfile_dir:
    def __enter__(self):
        import tempfile
        self._manager=tempfile.TemporaryDirectory(prefix="exercise5-report-")
        return Path(self._manager.__enter__())
    def __exit__(self,*args): return self._manager.__exit__(*args)

if __name__=="__main__": main()
