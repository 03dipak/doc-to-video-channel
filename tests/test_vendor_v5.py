"""V5: the last ten modules, the writer chokepoint, A43, and A44.

V5 is where the tree finally imports, so most of this file is about consequences
that only become checkable now: the §5.6 harness can see **both** `_ask_llm_stable`
bindings, the writer has two call sites to route, and `A44` has the voice registry
it was waiting for.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from doc_to_video_channel import planning_harness as ph
from doc_to_video_channel.studio import schema, voice, writer
from doc_to_video_channel.studio.plan import plan_lesson

PACKAGE = Path(__file__).resolve().parents[1] / "src/doc_to_video_channel"
STUDIO = PACKAGE / "studio"
V5_MODULES = ("cli", "duration", "llm", "narration", "pptx", "slides",
              "speech", "validate", "video", "voice")


# --- the tree finally imports -------------------------------------------------


def test_all_sixteen_vendored_modules_import() -> None:
    """The headline of V5. It was false at V4, by design of the build order."""
    import importlib

    for name in ("util", "text", "config", "topics", "schema", "plan", *V5_MODULES):
        assert importlib.import_module(f"doc_to_video_channel.studio.{name}") is not None
    assert callable(plan_lesson)


def test_the_v5_copies_diverged_only_where_recorded() -> None:
    """Ten modules, and every divergence is an annotation -- nothing functional.

    A vendored file that nobody edited and one that was edited must be
    distinguishable without reading the diff.
    """
    import hashlib

    manifest = json.loads((PACKAGE / "vendor_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["modules"]:
        if entry["decision"] != "copy":
            continue
        target = STUDIO / Path(entry["path"]).name
        if not target.is_file():
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        edits = list(entry.get("channel_edits") or [])
        if edits:
            assert digest != entry["sha256"], f"{target.name}: edits lost"
        else:
            assert digest == entry["sha256"], f"{target.name}: unrecorded divergence"


# --- 5.6: BOTH bindings, which only V5 can assert ---------------------------


def test_the_harness_now_sees_both_ask_llm_stable_bindings() -> None:
    """`plan.py` and `narration.py` each hold one. Patching one is blind to the other.

    This replaces the V4 test that asserted `patched == []`, and the replacement is
    the point: at V5 both exist, so the two-binding requirement becomes a real
    check rather than a note.
    """
    patched = ph.install_stub()
    assert "plan" in patched, "plan.py holds a binding"
    assert "narration" in patched, (
        "narration.py holds the second binding and the LLD says patching only one "
        "makes the harness structurally blind to the narration chain"
    )
    assert ph.plan_lesson_is_runnable()[0], "plan_lesson must be callable at V5"


def test_the_harness_digests_the_artefact_that_carries_the_narration() -> None:
    """§5.6: the plan dict cannot see a narration-only variation, so digest the script.

    Asserted on the function, not on a comment, and the negative half matters: the
    plan-digest route is exactly what the LLD measured as blind.
    """
    import inspect

    source = inspect.getsource(ph.digest_script)
    assert "tts_script" in source or "read_bytes" in source
    assert "plan" not in source.lower().split("def digest_script")[1].split("\n\n")[0]


# --- the writer: one door, and it refuses ------------------------------------


def test_both_render_call_sites_route_through_the_writer() -> None:
    """`AC#26` needs a control that cannot be bypassed, and a control needs one door.

    Two call sites, both inside `cli.main`. If a third appears, the chokepoint is
    no longer one, so the count is asserted rather than assumed.
    """
    cli = (STUDIO / "cli.py").read_text(encoding="utf-8")
    video = (STUDIO / "video.py").read_text(encoding="utf-8")
    assert cli.count("_render_media(") == 2, "the two call sites changed; update this"
    # `_render_media` is DEFINED in video.py and only CALLED from cli.py, so the
    # control belongs in video.py. Asserting the import lived in cli.py was my
    # first mistake, and it would have pushed the control to the wrong file.
    assert "def _render_media" in video, "the single definition must be in video.py"
    assert "write_media(plan, out_base" in video, "the chokepoint must be inside it"
    assert "from .writer import write_media" in video


def test_a_fixture_artefact_is_refused_with_exit_four(tmp_path: Path) -> None:
    """`AC#26`'s witness, and the code is **4**, not the 2 `AC#26`'s text says.

    §12.1 gives 2 to argparse's usage error and reserves 4 for "refused on
    purpose". A refusal exiting 2 would be indistinguishable from a typo.
    """
    plan: dict[str, Any] = {"title": "t", "fixture": True, "source_files": ["a.docx"]}
    with pytest.raises(writer.FixtureRefusal) as caught:
        writer.write_media(plan, tmp_path / "out", "a7d63e0")
    assert caught.value.code == writer.EXIT_REFUSED == 4
    assert not (tmp_path / "out.media.json").exists(), (
        "a refusal that left a manifest behind is a refusal that ran the thing it "
        "refuses"
    )


def test_the_same_manifest_with_the_bit_false_is_written(tmp_path: Path) -> None:
    """The other half of `AC#26`'s witness: not-false must WRITE."""
    plan: dict[str, Any] = {"title": "t", "fixture": False, "source_files": ["a.md"]}
    target = writer.write_media(plan, tmp_path / "out", "a7d63e0")
    written = json.loads(target.read_text(encoding="utf-8"))
    assert written["fixture"] is False
    assert written["vendor_ref"] == "a7d63e0", "the stamp travels with the reference"


def test_an_absent_bit_means_not_a_fixture(tmp_path: Path) -> None:
    """Absent is False, not "unknown" -- or every ordinary build would refuse."""
    target = writer.write_media({"title": "t"}, tmp_path / "out", "a7d63e0")
    assert json.loads(target.read_text(encoding="utf-8"))["fixture"] is False


# --- A44: the narration check, now that the voice registry exists ------------


def test_a44_is_voice_relative_not_absolute() -> None:
    """The measurement that decided the ruling: the default voice is HINDI.

    An absolute rule would be wrong in both directions -- it would break the
    default voice, which can pronounce Devanagari, and allow the English voice to
    narrate gibberish.
    """
    voices = {name: v.tts_voice for name, v in voice._VOICES.items()}
    assert voices["mhe-mix"].startswith("hi-IN"), (
        f"the default voice is {voices['mhe-mix']!r}; if it is no longer Hindi, "
        f"the A44 ruling needs revisiting"
    )
    assert voices["english"].startswith("en-IN")


@pytest.mark.parametrize(
    ("lang", "narration", "accepted"),
    [("en-IN", "plain english", True), ("en-IN", "यह अनुभाग", False),
     ("en-IN", "日本語", False), ("hi-IN", "यह अनुभाग", True)],
)
def test_the_narration_script_check_follows_the_voice(
    lang: str, narration: str, accepted: bool
) -> None:
    original = schema.SlideScene._narration_lang
    schema.SlideScene._narration_lang = lang
    try:
        base = {"title": "T", "bullets": ["b"], "source_refs": ["r"]}
        if accepted:
            assert schema.SlideScene(**base, narration=narration).narration == narration
        else:
            with pytest.raises(ValidationError, match="non-Latin"):
                schema.SlideScene(**base, narration=narration)
    finally:
        schema.SlideScene._narration_lang = original


def test_a44_removed_the_defect_V2_recorded() -> None:
    """The test that V2 wrote when the defect was open now asserts it is closed."""
    assert "narration" not in schema._FIELD_NAMES, (
        "narration is still outside the on-screen tuple -- that is correct and "
        "expected; it has its own voice-relative check"
    )
    original = schema.SlideScene._narration_lang
    schema.SlideScene._narration_lang = "en-IN"
    try:
        with pytest.raises(ValidationError):
            schema.SlideScene(title="T", bullets=["b"], source_refs=["r"],
                             narration="यह अनुभाग")
    finally:
        schema.SlideScene._narration_lang = original


# --- A43: satisfied by the declaration, not the heuristic -------------------


def test_a43_is_covered_by_the_storyboard_not_by_a_heuristic() -> None:
    """`_entity_tokens` still does not recognise `uv`, and that is now on purpose.

    The LLD's own discipline is a declaration a human can falsify over a heuristic.
    The storyboard declares the commands, and `spoken_command_trigrams` protects the
    trigrams inside them -- so patching `_entity_tokens` would be a guess where a
    declaration already exists. This test says so, so the ledger row is not
    "fixed" a second time by someone who has not read this.
    """
    from doc_to_video_channel.storyboard import spoken_command_trigrams
    from doc_to_video_channel.studio.narration import _entity_tokens

    assert "uv" not in _entity_tokens("run uv --version")
    assert "uv dash dash" in spoken_command_trigrams("uv --version")
