"""V3 / AC#31: prove the brand reaches the pixels, and that the old one is gone.

A config read is not evidence. `AC#31` says the old brand is ABSENT from the frame
and the new one PRESENT, and the only way to know is to render and look at pixels.

**The method is differential, and that matters.** Rendering once with the new brand
and reading `config.BRAND_NAME` would prove nothing: it would be consistent with a
renderer that ignores the brand entirely. So this renders the SAME scene three
times -- baseline brand, channel brand, and a nonsense control -- and requires all
three to differ pairwise. If any two frames are byte-identical, the brand is not on
the canvas and the check has proven nothing.

It uses the reference tree's `render_slide` because the renderers are V5; V3
verifies the BRAND, not the renderer.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ENGINE = Path("/home/dipak/agentic/doc-to-video-tutor")
sys.path.insert(0, str(ENGINE / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doc_to_video_tutor.studio import config as ref_config  # noqa: E402
from doc_to_video_tutor.studio import slides as slides_mod  # noqa: E402
from doc_to_video_tutor.studio.slides import render_slide  # noqa: E402

from doc_to_video_channel.studio import config as channel  # noqa: E402

SCENE = {
    "title": "Check what you have",
    "narration": "Run the version check first.",
    "bullets": ["uv --version", "Output is a version and a platform"],
    "section": "what is this",
    "topic": "Check what you have",
    "source_refs": ["spikes/v1-install.source.md"],
}
OUT = Path(__file__).resolve().parent / "out" / "v3"


def render_with(config_module: object, name: str, value: str) -> Path:
    """Render one scene with `BRAND_NAME` and `PACKAGE_NAME` forced to `value`."""
    original_brand = config_module.BRAND_NAME  # type: ignore[attr-defined]
    original_pkg = config_module.PACKAGE_NAME  # type: ignore[attr-defined]
    original_footer = config_module.BRAND_FOOTER  # type: ignore[attr-defined]
    config_module.BRAND_NAME = value  # type: ignore[attr-defined]
    config_module.PACKAGE_NAME = value  # type: ignore[attr-defined]
    config_module.BRAND_FOOTER = f"{value} v0.1.0 — learn by listening"  # type: ignore[attr-defined]
    # The renderer does `from .config import BRAND_FOOTER`, so the value is
    # SNAPSHOTTED at import. Patching `config.BRAND_FOOTER` after the fact changes
    # nothing -- measured: the first version of this script produced three
    # byte-identical frames and correctly reported INCONCLUSIVE, because it had
    # been measuring nothing at all. Patch the renderer's own binding.
    ref_config.BRAND_NAME = value
    ref_config.PACKAGE_NAME = value
    ref_config.BRAND_FOOTER = f"{value} v0.1.0 — learn by listening"
    slides_mod.BRAND_FOOTER = f"{value} v0.1.0 — learn by listening"
    try:
        target = OUT / f"frame_{name}.png"
        render_slide(dict(SCENE), 1, 5, target)
        return target
    finally:
        config_module.BRAND_NAME = original_brand  # type: ignore[attr-defined]
        config_module.PACKAGE_NAME = original_pkg  # type: ignore[attr-defined]
        config_module.BRAND_FOOTER = original_footer  # type: ignore[attr-defined]
        ref_config.BRAND_NAME = "doc-to-video-tutor"
        ref_config.PACKAGE_NAME = "doc-to-video-tutor"
        ref_config.BRAND_FOOTER = "doc-to-video-tutor v0.1.0 — learn by listening"
        slides_mod.BRAND_FOOTER = "doc-to-video-tutor v0.1.0 — learn by listening"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"reference brand : {ref_config.BRAND_NAME!r}")
    print(f"channel brand   : {channel.BRAND_NAME!r}")
    print(f"channel footer  : {channel.BRAND_FOOTER!r}")
    print()
    frames = {
        "reference": render_with(ref_config, "reference", "doc-to-video-tutor"),
        "channel": render_with(channel, "channel", channel.PACKAGE_NAME),
        "control": render_with(ref_config, "control", "ZZZ-CONTROL-STRING"),
    }
    digests = {name: digest(p) for name, p in frames.items()}
    for name, d in digests.items():
        print(f"  {name:10} {frames[name].name:22} {d}")
    print()
    pairs = [("reference", "channel"), ("reference", "control"), ("channel", "control")]
    ok = True
    for a, b in pairs:
        differ = digests[a] != digests[b]
        ok &= differ
        print(f"  {a} vs {b}: {'DIFFER' if differ else 'IDENTICAL -- the brand is NOT on the canvas'}")
    print()
    print(f"  AC#31 differential: {'PASS' if ok else 'INCONCLUSIVE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
