"""D1: caption burn-in, and the two `AC#30` instruments it unblocks.

Written against what the stage actually does when it is wrong, not only when it
is right. Each test below has a stated failure it was written to catch, and the
order is deliberate: the wrong input is asserted before the right one wherever
the two could be confused.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from doc_to_video_channel.studio import captions as C
from doc_to_video_channel.studio import slides as S

SCENES = [
    {"heading": "Baseline", "bullets": ["A metric registry exists", "Compare kinds"]},
    {"heading": "Verdict", "bullets": ["The unit matters", "Precedence is structural"]},
]

SCRIPT: dict[str, Any] = {
    "clips": [
        {"role": "scene", "index": 1,
         "narration": "Pehle baseline dekhte hain, taaki comparison sahi ho."},
        {"role": "scene", "index": 2,
         "narration": "Phir verdict, aur unit ka matlab badalta hai."},
        {"role": "final", "index": 3, "narration": "Key takeaways."},
    ]
}


def _render(tmp_path: Path) -> list[list[Path]]:
    pages: list[list[Path]] = []
    for i, scene in enumerate(SCENES, 1):
        png = tmp_path / f"scene{i}.png"
        S.render_slide(scene, i, len(SCENES), png)
        pages.append([png])
    return pages


def _deck(tmp_path: Path) -> Path:
    from pptx import Presentation
    from pptx.util import Inches

    deck = tmp_path / "deck.pptx"
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    for scene in SCENES:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        box = slide.shapes.add_textbox(Inches(0.4), Inches(0.7), Inches(9), Inches(1))
        box.text_frame.text = scene["heading"]
    prs.save(str(deck))
    return deck


# --- the mapping rule, which is where a caption lands on the WRONG frame ------


def test_only_scene_clips_carry_a_caption() -> None:
    """The `final` clip has index 3 and no frame. Bound by index alone it would
    claim a frame that does not exist, and every later caption shifts by one."""
    assert C.caption_for_scene(SCRIPT, 1)
    assert C.caption_for_scene(SCRIPT, 2)
    assert C.caption_for_scene(SCRIPT, 3) == "", "the final clip has no scene to burn onto"
    assert C.caption_for_scene(SCRIPT, 99) == ""


def test_a_scene_with_no_clip_gets_no_caption_rather_than_a_neighbours() -> None:
    sparse = {"clips": [{"role": "scene", "index": 1, "narration": "Only the first."}]}
    assert C.caption_for_scene(sparse, 1)
    assert C.caption_for_scene(sparse, 2) == "", "must not fall back to the previous clip"


# --- instrument 1: glyph height, and the case it first got wrong --------------


def test_glyph_height_does_not_move_when_a_second_line_is_added(tmp_path: Path) -> None:
    """A block height doubles with the line count; a glyph height cannot.

    The first version returned the band's full ink extent, so one line measured
    25px and two lines measured 55px. A legibility floor on that number passes a
    caption that is too small to read as long as it is also two lines.
    """
    heights = []
    for max_lines in (1, 2):
        pages = _render(tmp_path)
        C.burn_into_frame(pages[0][0], C.wrap_caption(SCRIPT["clips"][0]["narration"],
                                                      max_lines=max_lines))
        heights.append(C.instrument_glyph_height(pages[0][0]))
    assert heights[0] == heights[1], (
        f"glyph height moved with the line count: {heights}. The instrument is "
        f"measuring a text block, not a glyph."
    )


def test_a_caption_that_drew_nothing_fails_the_floor(tmp_path: Path) -> None:
    """The floor must catch the empty band, not just the small one."""
    pages = _render(tmp_path)
    measured = C.instrument_caption_bbox(pages[0][0], lines=2)
    assert measured.ink_pixels == 0
    assert measured.glyph_height == 0
    assert not measured.drawn
    assert measured.glyph_height < C.CAPTION_MIN_GLYPH_PX, (
        "an undrawn band must not satisfy the legibility floor"
    )


def test_a_legible_caption_meets_the_floor(tmp_path: Path) -> None:
    pages = _render(tmp_path)
    C.burn_into_frame(pages[0][0], C.wrap_caption("Baseline snapshot and compare"))
    assert C.instrument_glyph_height(pages[0][0]) >= C.CAPTION_MIN_GLYPH_PX


# --- the tofu hole, which is why the stage refuses ---------------------------


def test_unrenderable_characters_finds_devanagari_and_spares_latin() -> None:
    assert C.unrenderable_characters("Baseline snapshot, step 1.") == set()
    missing = C.unrenderable_characters("स्वागत")
    assert missing, "DejaVu Sans Bold has no Devanagari; this must be detected"
    assert all(not ch.isascii() for ch in missing)


def test_combining_marks_are_not_reported_missing() -> None:
    """A combining mark maps to nothing *visible*, which is not the same as
    mapping to `.notdef`. Reporting it would refuse every Devanagari string twice
    over and bury the real consonants in noise."""
    assert C.unrenderable_characters("ा") == set()


def test_a_tofu_caption_passes_the_floor_and_that_is_the_defect(tmp_path: Path) -> None:
    """Pinned deliberately. This is why `UnrenderableCaption` exists.

    Measured: a pure-Devanagari caption burned as eight `.notdef` boxes still
    reports 1064 ink pixels and a 23px glyph height, so it SATISFIES a 20px
    legibility floor while being unreadable. An instrument that cannot tell
    legible text from tofu does not gate anything. If a future font change makes
    this test fail because the glyphs now render, delete this test rather than
    inverting it -- the refusal in `caption_stage` becomes unnecessary, and that
    is a fact worth losing the pin to learn.
    """
    pages = _render(tmp_path)
    measured = C.burn_into_frame(pages[0][0], C.wrap_caption("स्वागत"))
    assert measured is not None
    assert measured.ink_pixels > 0
    assert measured.glyph_height >= C.CAPTION_MIN_GLYPH_PX, (
        "if this no longer holds, the font now renders Devanagari and the "
        "UnrenderableCaption refusal can be reconsidered"
    )


def test_the_stage_refuses_rather_than_burning_boxes(tmp_path: Path) -> None:
    pages = _render(tmp_path)
    deck = _deck(tmp_path)
    script = {"clips": [{"role": "scene", "index": 1, "narration": "स्वागत"}]}
    with pytest.raises(C.UnrenderableCaption) as caught:
        C.caption_stage(pages, script, deck)
    assert caught.value.characters
    # and nothing was drawn into either output
    assert C.instrument_caption_bbox(pages[0][0]).ink_pixels == 0
    from pptx import Presentation

    read_back = Presentation(str(deck))
    for slide in read_back.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                assert "स्वागत" not in shape.text_frame.text


def test_a_refusal_does_not_burn_the_first_scene_either(tmp_path: Path) -> None:
    """A partial burn is the defect this stage exists to prevent.

    The refusal fires before the first pixel, so a two-scene run where only the
    second caption is unrenderable leaves BOTH frames clean. Burning scene one and
    then refusing scene two would ship a video that disagrees with the deck.
    """
    pages = _render(tmp_path)
    script = {"clips": [
        {"role": "scene", "index": 1, "narration": "Perfectly fine Latin caption."},
        {"role": "scene", "index": 2, "narration": "स्वागत"},
    ]}
    with pytest.raises(C.UnrenderableCaption):
        C.caption_stage(pages, script, None)
    for page in pages:
        for png in page:
            assert C.instrument_caption_bbox(png).ink_pixels == 0, (
                f"{png.name} was burned before the refusal fired"
            )


# --- the band geometry, against chrome that already exists -------------------


def test_the_band_clears_the_brand_footer(tmp_path: Path) -> None:
    """`slides.render_slide` draws `BRAND_FOOTER` at y = H - 44 = 676.
    Measured, not assumed: the band's bottom must sit above it."""
    assert C.CAPTION_BAND_BOTTOM < 720 - 44
    pages = _render(tmp_path)
    C.burn_into_frame(pages[0][0], C.wrap_caption("Baseline snapshot and compare"))
    measured = C.instrument_caption_bbox(pages[0][0])
    assert measured.bbox[3] <= C.CAPTION_BAND_BOTTOM
    assert measured.bbox[3] < 720 - 44, "the caption ran into the footer"


def test_the_caption_stays_inside_the_frame(tmp_path: Path) -> None:
    pages = _render(tmp_path)
    C.burn_into_frame(pages[0][0], C.wrap_caption("x " * 200))
    measured = C.instrument_caption_bbox(pages[0][0])
    assert measured.bbox[2] <= C.FRAME_W
    assert measured.bbox[1] >= C.CAPTION_BAND_TOP


def test_a_frame_of_the_wrong_size_is_refused_not_fitted(tmp_path: Path) -> None:
    """Burning into a 640x360 frame would place the band at a different fraction
    of the picture, and the bbox instrument would then measure a rectangle other
    than the one shipped."""
    from PIL import Image

    odd = tmp_path / "odd.png"
    Image.new("RGB", (640, 360), (17, 17, 17)).save(odd)
    with pytest.raises(ValueError, match="1280x720"):
        C.burn_into_frame(odd, ["a caption"])


# --- wrapping ----------------------------------------------------------------


def test_wrapping_returns_nothing_for_empty_text() -> None:
    assert C.wrap_caption("") == []
    assert C.wrap_caption("   \n  ") == []


def test_wrapping_truncates_rather_than_dropping_the_tail() -> None:
    lines = C.wrap_caption("alpha beta gamma delta epsilon zeta eta theta", cols=20)
    assert len(lines) <= 2
    assert lines[-1].endswith("…"), "a dropped tail teaches the wrong lesson"
    assert "theta" not in "".join(lines), "the tail must be gone, not silently present"


# --- the two renderers, which is the whole point -----------------------------


def test_both_renderers_receive_captions(tmp_path: Path) -> None:
    """The LLD's stated cost: the stage must cross BOTH renderers, because a fix
    has silently missed the other one four times. This is the check that has ever
    caught that, and it is the reason `burn_into_frame` and `burn_into_deck` are
    two implementations instead of one."""
    from pptx import Presentation

    pages = _render(tmp_path)
    deck = _deck(tmp_path)
    report = C.caption_stage(pages, SCRIPT, deck)

    assert report["frames_burned"] == len(SCENES), "a frame went unburned"
    assert report["deck_slides_burned"] == len(SCENES), "a slide went unburned"

    read_back = Presentation(str(deck))
    captioned = 0
    for slide in read_back.slides:
        texts = [sh.text_frame.text for sh in slide.shapes if sh.has_text_frame]
        assert any("baseline" in t.lower() or "verdict" in t.lower() for t in texts), (
            f"no caption text in a deck slide: {texts}"
        )
        captioned += 1
    assert captioned == len(SCENES)


def test_every_page_of_a_multi_page_scene_gets_a_caption(tmp_path: Path) -> None:
    """The audio is one clip per scene, so a caption on page one only would leave
    the later pages of that scene with none -- the shape of the two-renderer bug,
    inside a single renderer."""
    pages = _render(tmp_path)
    extra = tmp_path / "scene1b.png"
    S.render_slide(SCENES[0], 1, len(SCENES), extra)
    pages[0].append(extra)
    report = C.caption_stage(pages, SCRIPT, None)
    assert report["frames_burned"] == 3, "a later page of a scene went uncaptioned"
    for png in pages[0]:
        assert C.instrument_caption_bbox(png).ink_pixels > 0


def test_the_final_clip_never_becomes_a_caption(tmp_path: Path) -> None:
    pages = _render(tmp_path)
    report = C.caption_stage(pages, SCRIPT, None)
    assert report["captions"] == 2, "the final clip has no frame and must not be counted"


# --- the wiring, since a stage nothing calls is a stage that does not run -----


def test_the_stage_is_wired_between_build_pptx_and_assemble_video() -> None:
    """A first version of the chokepoint created `writer.py` and called it from
    nowhere, and the test that asserted the routing is what caught it. Same
    failure mode, so the same defence."""
    source = Path(C.__file__).with_name("video.py").read_text(encoding="utf-8")
    # The CALL, not the name. `source.index("assemble_video(")` matches
    # `def assemble_video(` -- 8,000 characters earlier -- so this test asserted
    # the stage ran before the video module's own definition, and failed for a
    # reason that had nothing to do with the wiring. Matched on the call's own
    # arguments instead, which occur exactly once.
    build = source.index("build_pptx(plan, Path(")
    stage = source.index("caption_report = _caption_stage(")
    assemble = source.index("assemble_video(slides, audios,")
    assert build < stage < assemble, (
        "the stage must run after the deck exists and before the video is "
        f"assembled; found build={build} stage={stage} assemble={assemble}"
    )


def test_the_import_survives_in_a_cold_interpreter() -> None:
    """`slides` is imported by `video`, and the stage needs a real TTF. If the
    font paths broke, this fails at import rather than 4 minutes into a render."""
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0,'src');"
         "from doc_to_video_channel.studio import video, captions;"
         "assert video._caption_stage is captions.caption_stage;"
         "from doc_to_video_channel.studio.slides import _font;"
         "assert _font(26, bold=True) is not None, 'no TTF, captions would burn as 6px bitmap'"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1],
    )
    assert out.returncode == 0, out.stderr


def test_the_manifest_records_the_d1_edit() -> None:
    manifest = json.loads(
        (Path(__file__).resolve().parents[1]
         / "src/doc_to_video_channel/vendor_manifest.json").read_text(encoding="utf-8")
    )
    entry = next(e for e in manifest["modules"] if e["path"] == "studio/video.py")
    assert any("D1" in note for note in entry.get("channel_edits", [])), (
        "an unrecorded edit to a vendored file is a manifest that cannot be trusted"
    )


# --- the three measurement findings, each with the wrong input first ----------


def test_the_instrument_agrees_on_a_lossless_frame_and_an_encoded_one(
    tmp_path: Path,
) -> None:
    """The `A18` defect, repeated for captions, and found by measuring the artefact.

    The first version compared band pixels against `config.BG` **exactly**, which is
    right on a lossless PNG and wrong on every frame that has been through H.264.
    Measured on a frame extracted from a real MP4: 92,160 ink pixels -- the entire
    1280x72 band -- and a 72px "glyph height" for a band whose caption was 25px.
    A gate that reads the intermediate instead of the shipped file has not measured
    anything, which is exactly what the LLD records for `A18`.

    The instrument now differences the band against its own modal colour with a
    tolerance, so the answer must be the same on both.
    """
    from PIL import Image

    pages = _render(tmp_path)
    C.burn_into_frame(pages[0][0], C.wrap_caption("Pehle baseline dekhte hain."))
    lossless = C.instrument_caption_bbox(pages[0][0])

    encoded = tmp_path / "encoded.png"
    band = Image.open(pages[0][0]).convert("RGB")
    shifted = band.point(lambda v: max(0, min(255, v + 2)))
    shifted.save(encoded)
    through_codec = C.instrument_caption_bbox(encoded)

    assert through_codec.bbox == lossless.bbox, (
        f"a 2-level shift changed the measured box: {lossless.bbox} -> "
        f"{through_codec.bbox}. The instrument is reading exact pixel equality."
    )
    assert through_codec.glyph_height == lossless.glyph_height


def test_ink_height_depends_on_the_words_so_the_floor_cannot_be_high(
    tmp_path: Path,
) -> None:
    """Pinned deliberately, and it is the reason `CAPTION_MIN_GLYPH_PX` is 12.

    Measured over 7 adversarial Latin strings at ONE fixed 26px font, ink extent
    runs 14px to 25px -- a 44% spread, because it is a function of which
    characters are present. The first floor was 20px, calibrated from a single
    full-sentence sample that measured 25px, so it **rejected legible captions**:
    "aeiou nm sso" and "iiiiii" have no ascender or descender to measure and land
    at 14px. The floor now sits below the worst case, which makes it a weak floor
    that catches gross errors only. If a future font change makes this spread
    collapse, the floor can be raised -- that is the event to watch for.
    """
    cases = {
        "aeiou nm sso": 0,
        "iiiiii": 0,
        "BASELINE SNAPSHOT": 0,
        "same song sins": 0,
        "Step 1, then 2.": 0,
        "H p H p": 0,
        "Pehle baseline, hain": 0,
    }
    heights = []
    for text in cases:
        pages = _render(tmp_path)
        C.burn_into_frame(pages[0][0], C.wrap_caption(text))
        heights.append(C.instrument_glyph_height(pages[0][0]))

    assert min(heights) >= C.CAPTION_MIN_GLYPH_PX, (
        f"the floor rejects a legible caption: worst case {min(heights)}px is under "
        f"the {C.CAPTION_MIN_GLYPH_PX}px floor. {dict(zip(cases, heights, strict=True))}"
    )
    assert max(heights) - min(heights) >= 5, (
        f"ink extent barely varies ({heights}); if a font change flattened it, "
        f"CAPTION_MIN_GLYPH_PX can be raised and the floor stops being weak"
    )


def test_no_line_pitch_instrument_is_shipped() -> None:
    """A measure was built, measured, and removed rather than shipped wrong.

    Ink extent is content-dependent, so a content-independent measure was needed for
    instrument 1 to gate anything. Baseline-to-baseline pitch was the candidate and
    it does not survive contact with the pixels: it needs two INKED lines, and a
    caption padded to two lines has a blank second one, which no pixel measure can
    distinguish from an absent line. Measured: 2-line captions returned 30px, a
    one-line caption returned 6px (its `i` tittles splitting the run) and another
    returned 0. Three candidates, three failures -- ink extent, nominal-background
    equality, run-gap pitch -- so the finding is recorded and instrument 1 is left
    reporting a true pixel fact with an honestly weak floor, rather than gating on
    a number that returns 0 or 6 unpredictably.
    """
    assert not hasattr(C, "instrument_line_pitch"), (
        "if a content-independent pitch measure is wanted, it must first be shown "
        "to give one value across captions with different characters and line "
        "counts -- not restored from memory"
    )


def test_the_instrument_call_is_not_quadratically_slow(tmp_path: Path) -> None:
    """It was 443ms per call and made the suite crawl; correctness was never the
    complaint. The band is 72 x 1280 = 92,160 pixels and the Python loop read every
    one of them twice."""
    import time

    pages = _render(tmp_path)
    C.burn_into_frame(pages[0][0], C.wrap_caption("Pehle baseline dekhte hain."))
    start = time.monotonic()
    for _ in range(5):
        C.instrument_caption_bbox(pages[0][0])
    per_call = (time.monotonic() - start) / 5
    assert per_call < 0.25, f"instrument call is {per_call * 1000:.0f}ms"


def test_the_lld_records_instrument_one_as_ungateable() -> None:
    """Owner-ruled 2026-09-28. `AC#30` is not satisfiable as written, and the
    reason is in the design record rather than only in a commit message.

    Round 7 caught an acceptance criterion phrased as an adjective with no
    instrument that could fail. Marking this one ungateable -- rather than
    rewording it until it reads as covered -- is the same discipline applied
    forward, and this is the check that keeps the ruling from being quietly
    deleted by a later editing pass.
    """
    lld = (
        Path(__file__).resolve().parents[1] / "docs" / "LLD-tutorial-lane.md"
    ).read_text(encoding="utf-8")
    assert "INSTRUMENT 1 IS UNGATEABLE" in lld, (
        "AC#30's instrument-1 ruling has been removed from the LLD. It is an "
        "owner ruling and it is load-bearing: without it the criterion reads as "
        "covered when it is not."
    )
    assert "not satisfiable" in lld, "AC#30 must state that instrument 1 blocks it"


def test_the_weak_floor_stays_weak() -> None:
    """The floor must not be tightened into a gate without the ruling changing.

    It sits below the worst case measured over the adversarial population, so a
    legible caption can never be rejected. A future font change that flattened the
    spread would be the signal to raise it -- and to change `AC#30` with it, not
    silently.
    """
    assert C.CAPTION_MIN_GLYPH_PX <= 14, (
        f"the floor is {C.CAPTION_MIN_GLYPH_PX}px, at or above the 14px worst case "
        f"measured over the adversarial population. At that value it rejects "
        f"legible captions, which is the defect finding 2 recorded."
    )
