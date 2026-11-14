"""Tests for the Exercise-6 seminar decks.

The requirement for Exercise 6 is a PPTX **with speaker notes**. These tests
check that the decks exist, that every slide has real notes, and that the two
languages carry the same structure.
"""
import json
import os
import sys

import pytest
from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))

from build_deck import (DOCS, _en_slides, _fa_slides, build)      # noqa: E402

EN = os.path.join(DOCS, "SEMINAR_EN.pptx")
FA = os.path.join(DOCS, "SEMINAR_FA.pptx")


@pytest.fixture(scope="module")
def decks():
    if not (os.path.exists(EN) and os.path.exists(FA)):
        build(_en_slides(), EN, "Calibri")
        build(_fa_slides(), FA, "Vazirmatn")
    return {"en": Presentation(EN), "fa": Presentation(FA)}


def test_both_decks_exist():
    assert os.path.exists(EN)
    assert os.path.exists(FA)


@pytest.mark.parametrize("lang", ["en", "fa"])
def test_deck_has_slides(decks, lang):
    assert len(decks[lang].slides) >= 20


@pytest.mark.parametrize("lang", ["en", "fa"])
def test_every_slide_has_speaker_notes(decks, lang):
    for i, slide in enumerate(decks[lang].slides, 1):
        assert slide.has_notes_slide, f"slide {i} has no notes slide"
        text = slide.notes_slide.notes_text_frame.text.strip()
        assert len(text) > 80, f"slide {i} notes are too short: {text!r}"


@pytest.mark.parametrize("lang", ["en", "fa"])
def test_notes_are_not_a_copy_of_the_bullets(decks, lang):
    """The notes are a spoken script, not a restatement of the slide text."""
    for i, slide in enumerate(decks[lang].slides, 1):
        notes = slide.notes_slide.notes_text_frame.text.strip()
        body = "\n".join(sh.text_frame.text for sh in slide.shapes
                         if sh.has_text_frame)
        assert notes != body.strip(), f"slide {i}: notes duplicate the slide"


@pytest.mark.parametrize("lang", ["en", "fa"])
def test_every_slide_has_a_title(decks, lang):
    for i, slide in enumerate(decks[lang].slides, 1):
        texts = [sh.text_frame.text.strip() for sh in slide.shapes
                 if sh.has_text_frame and sh.text_frame.text.strip()]
        assert texts, f"slide {i} is empty"
        assert len(texts[0]) > 3, f"slide {i} has no real title"


def test_the_two_languages_have_the_same_shape():
    en, fa = _en_slides(), _fa_slides()
    assert len(en) == len(fa)
    for a, b in zip(en, fa):
        assert a["kind"] == b["kind"]


def test_persian_deck_marks_paragraphs_rtl():
    from pptx import Presentation as P
    prs = P(FA)
    rtl_seen = 0
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for p in shape.text_frame.paragraphs:
                if p._p.get_or_add_pPr().get("rtl") == "1":
                    rtl_seen += 1
    assert rtl_seen > 20, "Persian paragraphs were not marked right-to-left"


def test_slide_kinds_are_known():
    known = {"title", "section", "bullets", "table", "picture", "closing"}
    for slides in (_en_slides(), _fa_slides()):
        for s in slides:
            assert s["kind"] in known
            assert s.get("notes"), f"slide {s['title']!r} has no notes"


def test_picture_slides_reference_real_figures():
    """Every picture slide must point at a figure that is actually shipped."""
    for slides in (_en_slides(), _fa_slides()):
        for s in slides:
            if s["kind"] != "picture":
                continue
            assert s.get("image"), f"picture slide {s['title']!r} has no image"
            path = os.path.join(ROOT, "diagrams", s["image"])
            assert os.path.exists(path), f"missing figure {path}"
            assert s.get("caption"), f"figure {s['image']} has no caption"


def test_picture_slides_are_embedded_in_the_decks(decks):
    """A picture slide only counts if the PPTX really carries the image."""
    for lang in ("en", "fa"):
        pictures = sum(1 for slide in decks[lang].slides
                       for sh in slide.shapes
                       if sh.shape_type == 13)          # MSO_SHAPE_TYPE.PICTURE
        assert pictures >= 4, f"{lang}: only {pictures} images embedded"


def test_decks_quote_the_published_numbers():
    """The spoken numbers on the slides must come from output/deck_numbers.json.

    ``code/build_deck.py`` is expected to read that file rather than hard-code
    figures, so that a regenerated experiment cannot quietly leave the slides
    quoting stale values.
    """
    with open(os.path.join(ROOT, "output", "deck_numbers.json"),
              encoding="utf-8") as f:
        numbers = json.load(f)
    slides = _en_slides() + _fa_slides()
    blob = json.dumps(slides, ensure_ascii=False)
    for key, value in numbers.items():
        if key.startswith("_"):
            continue
        assert f"{value}" in blob or f"{value:,}" in blob, (
            f"no slide quotes {key} = {value!r}")


def test_tables_have_rectangular_rows():
    for slides in (_en_slides(), _fa_slides()):
        for s in slides:
            if s["kind"] != "table":
                continue
            widths = {len(r) for r in s["rows"]}
            assert widths == {len(s["headers"])}, f"ragged table: {s['title']}"


def test_decks_are_16_by_9(decks):
    for lang in ("en", "fa"):
        w, h = decks[lang].slide_width, decks[lang].slide_height
        assert abs((w / h) - (16 / 9)) < 0.02
