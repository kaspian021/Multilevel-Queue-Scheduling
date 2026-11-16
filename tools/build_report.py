"""Render one report content module to Markdown, DOCX and PDF.

Usage::

    python tools/build_report.py ex1_fa exercise-1 REPORT_FA
    python tools/build_report.py ex1_en exercise-1 REPORT_EN

The figures are looked up in ``<exercise>/diagrams`` and the artefacts are
written to ``<exercise>/docs``.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "content"))

import report_kit as rk  # noqa: E402


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    module, exercise, stem = argv[1], argv[2], argv[3]

    mod = __import__(f"content.{module}", fromlist=["build"])
    rep = mod.build()

    fig_dir = os.path.join(REPO, exercise, "diagrams")
    docs = os.path.join(REPO, exercise, "docs")
    os.makedirs(docs, exist_ok=True)

    usable = rk.TEXT_H_CM * rk.CM
    heights = rk.exact_heights(rep, fig_dir)
    overflow = [(i + 1, h, usable) for i, h in enumerate(heights) if h > usable]
    for i, used, lim in overflow:
        print(f"  !! page {i} overflows: {used:.0f}pt measured, {lim:.0f}pt usable")

    missing = [p for p in rep.figure_paths
               if not os.path.exists(os.path.join(fig_dir, os.path.basename(p)))]
    for p in missing:
        print(f"  !! missing figure: {p}")

    md_path = os.path.join(REPO, exercise, f"{stem}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(rk.render_markdown(rep))

    docx_path = rk.build_docx(rep, os.path.join(docs, f"{stem}.docx"), figures_dir=fig_dir)
    pdf_path = rk.build_pdf(rep, os.path.join(docs, f"{stem}.pdf"),
                            figures_dir=fig_dir,
                            footer_note=f"{exercise} / {stem}")

    pages_pdf = rk.pdf_page_count(pdf_path)
    print(json.dumps({
        "module": module,
        "exercise": exercise,
        "stem": stem,
        "pages": rep.page_count(),
        "pdf_pages": pages_pdf,
        "overflow": [i for i, _, _ in overflow],
        "max_page_fill": round(max(heights) / usable, 3) if heights else 0,
        "missing_figures": missing,
        "missing_glyphs": sorted(set(rk.MISSING_GLYPHS)),
        "outputs": [md_path, docx_path, pdf_path],
    }, ensure_ascii=False, indent=1))
    return 1 if (overflow or missing) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
