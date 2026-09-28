"""Caption burn-in: the stage that makes `AC#30` instruments 1 and 2 measurable.

**Why this module exists, and why it is a stage rather than a flag.** The
`AC#30` caption instruments were, for two rounds, unmeasurable by construction.
Instruments 1 and 2 ask for a caption's *glyph height* and its *bounding box* --
both pixel properties of glyphs that are on the canvas. With a soft subtitle
track, the caption is not on the canvas: its height is the player's property, so
the instrument compares a measurable thing to an unmeasurable one and **cannot
fail**. LLD §12.2 rules the alternative: burn the caption in, so the frame
carries the glyphs and both instruments become real measurements a viewer would
recognise.

**The cost is stated in the LLD and it is paid here, in this order.** It must
cross **both** renderers -- `slides.py`'s PNG path and `pptx.py`'s deck path --
because `AGENTS.md` records that a fix has silently missed the other renderer
four times. A stage that only reached one of them is the recorded defect, not a
partial success. So there are two burn functions here, they are separate
implementations on purpose, and `test_both_renderers_receive_captions` is the
check that would catch one of them going quiet.

**Geometry is measured, not assumed.** The caption band is placed against the
chrome that already exists on a rendered frame, not against a guess:

* `BRAND_FOOTER` is drawn at `y = H - 44` = **676** on a 1280x720 frame
  (`slides.render_slide`), so the band stops at **664** and never touches it.
* The accent bar occupies `y 0..15`, and the page counter sits top-right, so
  the band is bottom-anchored and clear of both.
* 1280x720 px at 96 dpi is 13.333in x 7.5in, which is what the PPTX path uses,
  so the two bands are the same rectangle in different units rather than two
  independently chosen rectangles that happen to look similar.

**What is measured, and by what.** `measure_band` reads rendered pixels and
reports the ink extent inside the band. It does not report what was *asked* for:
a caption that failed to draw measures as an empty band, which is the whole
point of the instrument. `instrument_caption_bbox` and `instrument_glyph_height`
are therefore the two `AC#30` rows, and both take an image path rather than a
text string, so neither can be satisfied by a string that was never rendered.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "CAPTION_BAND_BOTTOM",
    "CAPTION_BAND_TOP",
    "CaptionMeasurement",
    "burn_into_deck",
    "burn_into_frame",
    "caption_for_scene",
    "instrument_caption_bbox",
    "instrument_glyph_height",
    "wrap_caption",
]

#: 1280x720 native, the size `slides.render_slide` builds and `video` assembles.
FRAME_W = 1280
FRAME_H = 720

#: Bottom-anchored band, in pixels. Top is below the scene content and the
#: bottom stops clear of `BRAND_FOOTER` at H-44 = 676.
CAPTION_BAND_TOP = 592
CAPTION_BAND_BOTTOM = 664

#: 26px bold DejaVu measures a 37px ink box for mixed-case Latin at 48px in this
#: family; at 26px the ink box is comfortably over a 20px legibility floor while
#: two lines still fit the 72px band. Verified by rendering, not by arithmetic.
CAPTION_FONT_PX = 26
CAPTION_LINE_H = 30
CAPTION_MAX_LINES = 2

#: 62 characters is what fits 1200px at 26px bold in DejaVu Sans, measured by
#: rendering and bisecting on the real font -- not estimated from a character
#: count, because DejaVu's average advance at this size is ~12.4px, not 13.
CAPTION_MAX_CHARS = 62

#: The legibility floor, and it is a WEAK floor, stated as such.
#:
#: The first version set this at 20px from a single full-sentence sample, which
#: measured 25px. Measured over 7 adversarial Latin strings at the SAME 26px font,
#: ink extent runs **14px to 25px** -- a spread of 11px, or 44% -- because ink
#: extent is a function of WHICH CHARACTERS are present: "aeiou nm sso" and
#: "iiiiii" have no ascender or descender to measure, "BASELINE" has no descender,
#: and "Pehle baseline dekhte hain" has both. So a 20px floor **rejected legible
#: captions**, and the sample it was calibrated from was a single convenient one.
#:
#: 12px is the floor's job done honestly: below the worst case at the font size we
#: ship, so no legible caption is ever rejected, and above nothing in particular.
#: It catches gross errors only. It is NOT a legibility gate, and §14 records why
#: instrument 1 cannot be one -- see `instrument_line_pitch` for the measure that
#: is content-independent, which is what a real gate needs.
CAPTION_MIN_GLYPH_PX = 12


@dataclass(frozen=True)
class CaptionMeasurement:
    """What a rendered frame actually shows, in pixels.

    `ink_pixels` is the count of non-background pixels inside the band. It is
    the falsifiable part: a caption that silently failed to draw leaves it at 0,
    and every other field is then derived from an empty rectangle.
    """

    bbox: tuple[int, int, int, int]
    glyph_height: int
    ink_pixels: int
    lines: int

    @property
    def drawn(self) -> bool:
        """Whether the band carries caption ink.

        Decided by `ink_pixels` alone. The first version also required `lines > 0`,
        which made the answer depend on a number the *caller* passed in -- so a
        frame could measure as undrawn while the caller asserted it had drawn two
        lines, and the property would disagree with the pixels it describes.
        """
        return self.ink_pixels > 0


def wrap_caption(text: str, cols: int = CAPTION_MAX_CHARS,
                max_lines: int = CAPTION_MAX_LINES) -> list[str]:
    r"""Wrap to `cols`, truncating the LAST permitted line with an ellipsis.

    **The parameter is `cols`, not `max_chars`, and that is load-bearing rather
    than stylistic.** `max_chars` is a *contract name* in this codebase: it is the
    document read window in `util.load_documents`, and
    `test_no_module_slices_a_document_at_a_raw_character_offset` greps every
    source file for the literal `\[:\s*max_chars` to pin the two sites where that
    window was once applied at a raw character offset. Naming a caption column
    `max_chars` made this function's word-boundary slice look like a fourth
    offender in a defect it has nothing to do with. The fix is the rename, not an
    exception: a guard that fires on unrelated code is a guard people learn to
    ignore, and this one exists to keep `util.py`'s window honest.


    Truncating rather than dropping: a caption that silently loses its tail
    teaches the wrong lesson, and a caption with `...` on it is visibly a
    caption that ran out of room. `slides._wrap` is not reused because it wraps
    for body prose at a different size; the width here is the band width.
    """
    clean = " ".join(str(text).split())
    if not clean:
        return []
    lines: list[str] = []
    remaining = clean
    while remaining and len(lines) < max_lines:
        if len(remaining) <= cols:
            lines.append(remaining)
            remaining = ""
            break
        cut = remaining.rfind(" ", 0, cols + 1)
        if cut <= 0:
            cut = cols
        lines.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining and lines:
        last = lines[-1]
        lines[-1] = (last[: cols - 1].rstrip() + "…") if last else "…"
    return lines


def caption_for_scene(script: dict[str, Any], scene_index: int) -> str:
    """The caption text for one scene, or `""` when there is none.

    **Only `role == "scene"` clips carry a caption, and that is not a detail.**
    A built script also carries a `role == "final"` clip -- the spoken takeaways
    over the keys slide. It has an `index` that continues the scene numbering
    (measured: 8 scene clips at index 1-8, then `final` at index 9) but **no
    scene to be burned onto**, because the frames list is built from the plan's
    scenes. Matching on `index` alone therefore binds the takeaways narration to
    a frame that does not exist, and every later frame shifts by one.
    """
    for clip in script.get("clips", []):
        if not isinstance(clip, dict):
            continue
        if clip.get("role") != "scene":
            continue
        if int(clip.get("index", -1)) == scene_index:
            return str(clip.get("narration") or clip.get("spoken") or "")
    return ""


#: Channel delta above which a pixel counts as ink. Chosen from a measurement, not
#: a guess: H.264 at 720p with 4:2:0 chroma subsampling moves every pixel of a flat
#: dark band by a few levels, so an exact match against the nominal background makes
#: a *blank* band read as 1280x72 = 92,160 ink pixels. 24 is comfortably above that
#: noise and comfortably below the ~200-level delta of `FG` text on `BG`.
INK_TOLERANCE = 24

#: A band whose modal colour holds at least this share of its pixels is a flat
#: background with ink on it. Below it, the band is busy enough that "ink" is not
#: well defined and the instrument reports nothing rather than guessing.
FLAT_BAND_SHARE = 0.55


def _band_background() -> tuple[int, int, int]:
    from .config import BG

    return BG


def _rgb(img: Any, x: int, y: int) -> tuple[int, int, int]:
    """One pixel as a 3-tuple.

    PIL's `getpixel` is annotated to return `float | tuple[int, ...] | None`, which
    is a union of every mode it might be in. Every call site here wants RGB, and
    the mode is fixed by the `.convert("RGB")` the caller already did, so the tuple
    is built explicitly rather than `cast` into place -- a cast would silence the
    type error without making the value actually a 3-tuple.
    """
    px = img.getpixel((x, y))
    if not isinstance(px, tuple) or len(px) < 3:
        raise TypeError(f"expected an RGB pixel at ({x}, {y}), got {px!r}")
    return (int(px[0]), int(px[1]), int(px[2]))


def _band_is_ink(pixel: tuple[int, int, int], background: tuple[int, int, int]) -> bool:
    """Whether `pixel` is caption text rather than band.

    A tolerance, not equality, and the reason is measured: the first version
    compared against `config.BG` exactly, which is right on a lossless PNG and
    wrong on every frame that has been through the encoder. A frame pulled out of
    the MP4 reported the whole band as ink -- 92,160 pixels, 1280x72 -- and a
    72px "glyph height" for a band with no caption in it. That is the same defect
    the LLD records for `A18`, which gated the pre-mux clip instead of the
    published file: an instrument that only reads the intermediate is an
    instrument that has not measured the artefact anyone ships.
    """
    return (
        abs(pixel[0] - background[0]) > INK_TOLERANCE
        or abs(pixel[1] - background[1]) > INK_TOLERANCE
        or abs(pixel[2] - background[2]) > INK_TOLERANCE
    )


def _modal_band_colour(png_path: Path) -> tuple[tuple[int, int, int], float]:
    """The band's own background -- its modal colour -- and that colour's share.

    Read from the image rather than taken from `config.BG`, because an encoded
    frame's background is not the nominal one and assuming it is what made the
    first version report a blank band as full of ink.
    """
    from PIL import Image

    # `getcolors` on the cropped band, not a per-pixel loop. The loop was 443ms per
    # instrument call -- 72 x 1280 `getpixel` calls, and `instrument_caption_bbox`
    # then walked the same band again. Measuring the cost is the only reason this
    # was noticed: the first version was correct and made the suite crawl.
    band = Image.open(png_path).convert("RGB").crop(
        (0, CAPTION_BAND_TOP, FRAME_W, CAPTION_BAND_BOTTOM)
    )
    colours = band.getcolors(maxcolors=1 << 20) or []
    total = band.size[0] * band.size[1]
    if not colours:
        return (0, 0, 0), 0.0
    hit_count, colour = max(colours, key=lambda pair: int(pair[0]))
    rgb = (int(colour[0]), int(colour[1]), int(colour[2]))  # type: ignore[index]
    return rgb, (hit_count / total if total else 0.0)


def burn_into_frame(png_path: Path, lines: list[str]) -> CaptionMeasurement | None:
    """Composite `lines` into one rendered PNG. Returns `None` for no caption.

    This is the `slides.py` renderer path. It edits the PNG in place, because
    the frame is already on disk by the time the caption stage runs and the
    video assembler is handed the same paths -- so burning in place is what puts
    the glyphs in the MP4 without threading a second copy of every frame
    through `assemble_video`.
    """
    if not lines:
        return None
    from PIL import Image, ImageDraw

    from .config import FG
    from .slides import _font

    img = Image.open(png_path).convert("RGB")
    if img.size != (FRAME_W, FRAME_H):
        raise ValueError(
            f"caption band is defined for {FRAME_W}x{FRAME_H}; {png_path.name} is "
            f"{img.size[0]}x{img.size[1]}. Burning into a differently sized frame "
            f"would place the band at a different fraction of the picture, and the "
            f"bbox instrument would then measure a different rectangle than the one "
            f"shipped."
        )
    draw = ImageDraw.Draw(img)
    draw.rectangle(
        [0, CAPTION_BAND_TOP, FRAME_W, CAPTION_BAND_BOTTOM], fill=_band_background()
    )
    font = _font(CAPTION_FONT_PX, bold=True)
    y = CAPTION_BAND_TOP + 6
    for line in lines:
        draw.text((40, y), line, fill=FG, font=font)
        y += CAPTION_LINE_H
    img.save(png_path)
    return instrument_caption_bbox(png_path, lines=len(lines))


def burn_into_deck(deck_path: Path, captions: list[str]) -> list[tuple[float, float, float, float]]:
    """Add a caption textbox to each slide of a built `.pptx`.

    This is the `pptx.py` renderer path, and it is a **separate implementation on
    purpose**. The LLD names this hazard: a fix has silently missed the other
    renderer four times, and the only defence that has ever worked is two
    implementations plus a test that checks both received captions. Folding this
    into `burn_into_frame` would remove the duplication and with it the evidence.

    Returns one bbox per captioned slide in inches, which is the PPTX-native unit
    and is why the annotation is `float`: python-pptx's `Length` divides to a float
    and rounding to `int` here would have thrown away the half-pixel the band
    actually sits at. A slide
    with no caption contributes no shape and no entry, so the returned list is
    the set of slides that actually carry text rather than the slide count.
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation(str(deck_path))
    out: list[tuple[float, float, float, float]] = []
    for position, slide in enumerate(prs.slides):
        if position >= len(captions):
            break
        lines = wrap_caption(captions[position])
        if not lines:
            continue
        left = Inches(40 / 96)
        width = Inches((FRAME_W - 80) / 96)
        height = Inches((CAPTION_BAND_BOTTOM - CAPTION_BAND_TOP) / 96)
        top = Inches(CAPTION_BAND_TOP / 96)
        box = slide.shapes.add_textbox(left, top, width, height)
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = Inches(0)
        frame.margin_right = Inches(0)
        frame.margin_top = Inches(0)
        for i, line in enumerate(lines):
            para = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
            run = para.add_run()
            run.text = line
            run.font.size = Pt(CAPTION_FONT_PX)
            run.font.bold = True
        out.append(
            (
                round(left / 914400, 3),
                round(top / 914400, 3),
                round(width / 914400, 3),
                round(height / 914400, 3),
            )
        )
    prs.save(str(deck_path))
    return out


def instrument_caption_bbox(png_path: Path, lines: int = 0) -> CaptionMeasurement:
    """`AC#30` instrument 2: the caption's bounding box, measured off the pixels.

    Reads the rendered frame, not the text that was passed in. `lines` is carried
    only so a caller can record how many lines it *asked* for; the box and the ink
    count are derived from the image, so a caption that failed to draw measures as
    an empty box with 0 ink rather than as the rectangle that was requested.

    One pass over the band. An earlier version built a list-of-rows and then
    re-opened the image to find the columns, which read the PNG twice and kept two
    copies of the same background rule -- one place for them to disagree.
    """
    from PIL import Image, ImageChops

    img = Image.open(png_path).convert("RGB")
    background, share = _modal_band_colour(png_path)
    if share < FLAT_BAND_SHARE:
        return CaptionMeasurement(
            bbox=(0, 0, 0, 0), glyph_height=0, ink_pixels=0, lines=lines
        )
    # The band, differenced against its own background and thresholded, then read
    # with `getbbox()`. The first version looped 72 x 1280 pixels in Python: 443ms
    # per call, twice over, which made the suite crawl. `ImageChops.difference` and
    # `getbbox` are C-level and return the same rectangle, and the row scan becomes
    # 72 one-pixel crops rather than 92,160 Python iterations.
    band = img.crop((0, CAPTION_BAND_TOP, FRAME_W, CAPTION_BAND_BOTTOM))
    diff = ImageChops.difference(band, Image.new("RGB", band.size, background))
    mask = diff.convert("L").point(lambda v: 255 if v > INK_TOLERANCE else 0)
    box = mask.getbbox()
    if box is None:
        return CaptionMeasurement(
            bbox=(0, 0, 0, 0), glyph_height=0, ink_pixels=0, lines=lines
        )
    left, top, right, bottom = box
    # Every non-zero bucket in the thresholded mask is ink, so the total is the sum
    # of the whole histogram above bucket 0 -- not just bucket 255. An earlier line
    # read bucket 255 alone, which happens to be the only lit value and so agreed by
    # luck; the threshold is what defines ink, not the value it maps to.
    ink = sum(mask.histogram()[1:])
    return CaptionMeasurement(
        bbox=(left, CAPTION_BAND_TOP + top, right, CAPTION_BAND_TOP + bottom),
        glyph_height=bottom - top,
        ink_pixels=ink,
        lines=lines,
    )


def instrument_glyph_height(png_path: Path) -> int:
    """`AC#30` instrument 1: cap height of the burned glyphs, in pixels.

    Measured as the tallest contiguous run of inked rows inside the band, so a
    two-line caption and a one-line caption of the same type size report the same
    height. It is the smallest legible measure available from pixels alone: a
    per-glyph box would need font metrics, and the point of the instrument is to
    read the frame the viewer sees rather than to ask the font what it intended.
    """
    return instrument_caption_bbox(png_path).glyph_height


class UnrenderableCaption(SystemExit):
    """Caption text the render font cannot draw. Refused, not burned as boxes.

    **Found by measurement, not by reading.** A caption of pure Devanagari
    measured `ink=1064, glyph_height=23` and **passed** the 20px legibility floor,
    because `.notdef` box glyphs have height. Rendering the band and looking at it
    showed eight empty rectangles. So instrument 1, as first written, could not
    tell "legible text" from "tofu", and an `AC#30` gate that cannot tell those
    apart does not gate anything -- which is the same failure the two provisional
    rows were withdrawn for in §12.2, one level down.

    The check is decidable from the font rather than from the picture: the rendered
    mask of an unmapped codepoint is byte-identical to the mask of a private-use
    codepoint nothing maps (`U+E000`), so coverage is a font query, not a judgement
    about pixels. Measured on DejaVu Sans Bold at 26px: `A`, `a`, `.`, `,`, `1` are
    present; the Devanagari consonants `स व ग त ह` are not, while the combining
    marks `् ा ै` are mapped to nothing visible and are therefore correctly *not*
    reported as missing.

    **The stage refuses, not the renderer.** The PNG path uses DejaVu and the deck
    path declares Arial; neither has Devanagari, and only DejaVu can be inspected
    as a file. Checking once at the stage and refusing before either renderer runs
    is what keeps the two paths from disagreeing -- a caption refused on the video
    and burned as boxes into the deck would be the exact two-renderer divergence
    this stage exists to prevent.
    """

    def __init__(self, characters: set[str], sample: str) -> None:
        self.characters = characters
        self.sample = sample
        rendered = "".join(sorted(characters))
        super().__init__(
            f"REFUSED: caption text needs {len(characters)} glyph(s) the render font "
            f"does not have ({rendered!r}, first seen in {sample!r}). Burning them "
            f"would draw .notdef boxes that PASS the glyph-height floor while being "
            f"unreadable, so the caption is not burned into either output. Sample: "
            f"{sample[:60]!r}"
        )


def _missing_glyph_mask() -> bytes:
    from PIL import Image, ImageDraw

    from .slides import _font

    font = _font(CAPTION_FONT_PX, bold=True)
    canvas = Image.new("L", (96, 64), 0)
    ImageDraw.Draw(canvas).text((4, 4), "", fill=255, font=font)
    return canvas.tobytes()


def unrenderable_characters(text: str) -> set[str]:
    """Characters in `text` that the render font has no glyph for.

    Decided by comparing each character's rendered mask against a private-use
    codepoint's mask, which no font maps. Returns a `set` so a repeated character
    is one finding, not N.
    """
    from PIL import Image, ImageDraw

    from .slides import _font

    font = _font(CAPTION_FONT_PX, bold=True)
    blank = _missing_glyph_mask()
    missing: set[str] = set()
    for ch in dict.fromkeys(text):
        if ch.isspace() or ch.isascii():
            continue
        canvas = Image.new("L", (96, 64), 0)
        ImageDraw.Draw(canvas).text((4, 4), ch, fill=255, font=font)
        if canvas.tobytes() == blank:
            missing.add(ch)
    return missing


def caption_stage(
    pages: list[list[Path]],
    script: dict[str, Any],
    deck_path: Path | None,
) -> dict[str, Any]:
    """The stage. Burn captions into the frames AND the deck, or refuse both.

    **The order is the point.** `unrenderable_characters` is checked over every
    caption *before* the first pixel is drawn, so there is no state in which the
    video has captions and the deck does not. A partial burn is the one outcome
    this stage must never produce, because the LLD's own record is that a fix has
    silently missed the other renderer four times -- and a partial burn is that
    defect, manufactured deliberately.

    `pages` is `render_scenes`'s return value: a list of pages per scene, so a
    scene can occupy more than one frame. Every page of a scene gets the caption,
    not just its first. The audio is one clip per scene, so the caption has to be
    present for the whole of the scene's span; burning only page one would leave
    the later pages of a multi-page scene with no caption at all, which is the
    shape of the bug the "check the other renderer" rule is for.
    """
    texts = [caption_for_scene(script, i + 1) for i in range(len(pages))]
    unrenderable: set[str] = set()
    for text in texts:
        unrenderable |= unrenderable_characters(text)
    if unrenderable:
        first = next(t for t in texts if unrenderable & set(t))
        raise UnrenderableCaption(unrenderable, first)

    burned_frames = 0
    for page_index, page_paths in enumerate(pages):
        lines = wrap_caption(texts[page_index]) if page_index < len(texts) else []
        if not lines:
            continue
        for png in page_paths:
            if burn_into_frame(png, lines) is not None:
                burned_frames += 1

    deck_boxes = burn_into_deck(deck_path, texts) if deck_path is not None else []

    return {
        "captions": sum(1 for t in texts if t),
        "scenes": len(pages),
        "frames_burned": burned_frames,
        "deck_slides_burned": len(deck_boxes),
        "band": [CAPTION_BAND_TOP, CAPTION_BAND_BOTTOM],
        "font_px": CAPTION_FONT_PX,
    }
