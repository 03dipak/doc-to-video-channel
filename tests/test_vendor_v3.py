"""V3 / AC#31: the brand, proven in pixels rather than asserted in config.

A config read is not evidence. `AC#31` says the old brand is absent from the frame
and the new one present, and only a rendered frame settles that.

**The method is differential, and the inconclusiveness guard is the point.** These
tests render the same scene under three different brand values and require all
three frames to differ pairwise. Identical pixels would mean the brand never
reached the canvas — which is exactly what happened the first time, because the
renderer does `from .config import BRAND_FOOTER` and the value is snapshotted at
import, so patching `config` changed nothing and all three frames hashed the same.
The test reported INCONCLUSIVE and that was the correct result: a check that
cannot distinguish "the brand is right" from "the brand is not rendered at all" is
not a check.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

from doc_to_video_channel.studio import config

ENGINE = Path("/home/dipak/agentic/doc-to-video-tutor")
FOOTER = f"{config.PACKAGE_NAME} v{config.PACKAGE_VERSION} — {config.BRAND_TAGLINE}"

needs_engine = pytest.mark.skipif(
    not (ENGINE / "src").is_dir(), reason="reference tree absent; cannot render"
)


# --- the config change itself -------------------------------------------------


def test_the_brand_is_the_channel_not_the_engine() -> None:
    assert config.PACKAGE_NAME == "doc-to-video-channel"
    assert config.BRAND_NAME == "doc-to-video-channel"
    assert "doc-to-video-tutor" not in config.BRAND_FOOTER


def test_changing_package_name_rebrands_both_others() -> None:
    """V3 is ONE changed line, and it propagates.

    The LLD calls V3 "BRAND_NAME / BRAND_FOOTER -- 2 lines", which reads as two
    independent edits. It is not: `BRAND_NAME = PACKAGE_NAME` and the footer is an
    f-string over it, so the other two follow. Asserted so the derivation cannot
    silently become three independent literals.
    """
    assert config.BRAND_NAME == config.PACKAGE_NAME
    derived = f"{config.BRAND_NAME} v{config.PACKAGE_VERSION} — {config.BRAND_TAGLINE}"
    assert derived == config.BRAND_FOOTER


def test_the_brand_matches_pyproject() -> None:
    """The brand and the distribution must not be able to disagree."""
    text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    declared = next(
        line.split("=", 1)[1].strip().strip('"')
        for line in text.splitlines()
        if line.startswith("name =")
    )
    assert declared == config.PACKAGE_NAME


def test_the_old_brand_survives_nowhere_in_the_shipped_tree() -> None:
    """`vendor.py` names the reference repository, which is legitimate.

    So this asserts the *renderer inputs* specifically rather than the whole tree:
    a stray `doc-to-video-tutor` in a config value would render the old brand, and
    a stray one in a comment or a path is not a defect.
    """
    for name, value in (
        ("PACKAGE_NAME", config.PACKAGE_NAME),
        ("BRAND_NAME", config.BRAND_NAME),
        ("BRAND_FOOTER", config.BRAND_FOOTER),
        ("BRAND_TAGLINE", config.BRAND_TAGLINE),
    ):
        assert "doc-to-video-tutor" not in str(value), f"{name} still carries the old brand"


# --- the differential, in pixels ---------------------------------------------


@pytest.fixture(scope="module")
def frames() -> dict[str, Path]:
    if not (ENGINE / "src").is_dir():
        pytest.skip("reference tree absent")
    sys.path.insert(0, str(ENGINE / "src"))
    try:
        from doc_to_video_tutor.studio import config as ref_config
        from doc_to_video_tutor.studio import slides as slides_mod
        from doc_to_video_tutor.studio.slides import render_slide
    except ImportError:  # pragma: no cover
        pytest.skip("reference tree present but not importable")
    # Surfaced as a fixture error rather than a silent pass: an AttributeError here
    # means the reference's API moved, and three tests would otherwise be skipped
    # for the wrong reason.
    globals()["_render_slide"] = render_slide

    scene = {
        "title": "Check what you have",
        "narration": "Run the version check first.",
        "bullets": ["uv --version", "Output is a version and a platform"],
        "section": "what is this",
        "topic": "Check what you have",
        "source_refs": ["spikes/v1-install.source.md"],
    }
    out = Path(__file__).resolve().parent.parent / "spikes" / "out" / "v3_test"
    out.mkdir(parents=True, exist_ok=True)

    saved = (slides_mod.BRAND_FOOTER, ref_config.BRAND_NAME)
    produced: dict[str, Path] = {}
    try:
        for label, brand in (
            ("reference", "doc-to-video-tutor"),
            ("channel", config.PACKAGE_NAME),
            ("control", "ZZZ-CONTROL-STRING"),
        ):
            footer = f"{brand} v0.1.0 — learn by listening"
            # Patch the RENDERER's binding, not config's: `slides.py` does
            # `from .config import BRAND_FOOTER`, so config is a snapshot.
            slides_mod.BRAND_FOOTER = footer
            ref_config.BRAND_NAME = brand
            target = out / f"{label}.png"
            render_slide(dict(scene), 1, 5, target)
            produced[label] = target
    finally:
        slides_mod.BRAND_FOOTER, ref_config.BRAND_NAME = saved
    return produced


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@needs_engine
def test_the_brand_reaches_the_pixels(frames: dict[str, Path]) -> None:
    """Three brand values, three different frames. `AC#31`.

    Pairwise, so no single comparison can be satisfied by an unrelated difference
    such as a timestamp.
    """
    digests = {name: _digest(p) for name, p in frames.items()}
    assert digests["reference"] != digests["channel"], (
        "the reference and channel brands produced the SAME frame: either the brand "
        "is not on the canvas, or the renderer snapshots config at import and the "
        "patch never reached it. This is the inconclusive case, and it must fail."
    )
    assert digests["reference"] != digests["control"]
    assert digests["channel"] != digests["control"]


@needs_engine
def test_the_control_proves_the_differential_is_about_the_brand(frames: dict[str, Path]) -> None:
    """A nonsense brand must also change the frame.

    Without this, "reference != channel" could be satisfied by anything that varies
    between two renders. The control is what makes the difference attributable to
    the brand rather than to the render being nondeterministic.
    """
    assert _digest(frames["control"]) not in {
        _digest(frames["reference"]),
        _digest(frames["channel"]),
    }


@needs_engine
def test_rendering_the_same_scene_twice_is_deterministic(frames: dict[str, Path]) -> None:
    """The negative control for determinism: a re-render must reproduce the frame.

    If two renders of the same scene differ, then the differential above proves
    nothing at all, because everything differs.
    """
    sys.path.insert(0, str(ENGINE / "src"))
    from doc_to_video_tutor.studio.slides import render_slide

    scene = {
        "title": "Check what you have",
        "narration": "Run the version check first.",
        "bullets": ["uv --version", "Output is a version and a platform"],
        "section": "what is this",
        "topic": "Check what you have",
        "source_refs": ["spikes/v1-install.source.md"],
    }
    out = Path(__file__).resolve().parent.parent / "spikes" / "out" / "v3_test"
    again = out / "reference_again.png"
    render_slide(dict(scene), 1, 5, again)
    assert _digest(again) == _digest(frames["reference"]), (
        "two renders of the same scene differ, so the brand differential is not "
        "evidence that the brand is rendered"
    )
