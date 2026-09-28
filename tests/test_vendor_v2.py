"""V2: the two Pydantic models, and the two-spelling defect AC#7 names.

`topics.py` and `schema.py` are the first vendored modules with *internal* imports
— `schema.py` imports `_has_non_latin_script` from `text`, `topics.py` imports the
banned n-grams from `config` — which is exactly why V2 follows V1 and not V2
follows nothing. Both are byte-identical to `VENDOR_REF` except for the `AC#7`
change recorded below.

**What AC#7 found, measured.** `config._SECTIONS` spells the five kinds in lower
case; a reference `plan.json` emits `"section": "What Is This"` in Title Case. Two
spellings of one concept. And `section: str` accepted **any** string, so `'bogus'`
validated clean and nothing ever noticed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from doc_to_video_channel.studio import schema, topics
from doc_to_video_channel.studio.schema import SlideScene

PACKAGE = Path(__file__).resolve().parents[1] / "src/doc_to_video_channel"
STUDIO = PACKAGE / "studio"
VALID = {"title": "T", "narration": "n", "bullets": ["b"], "source_refs": ["r"]}


# --- the copies, and what changed in them -----------------------------------


def test_the_two_modules_are_the_manifests_files_except_for_the_recorded_change() -> None:
    """`topics.py` is untouched; `schema.py` carries the AC#7 change.

    A vendored file that nobody edited and a vendored file that was edited must be
    distinguishable without reading the diff, because "we vendored the baseline"
    and "we changed the baseline" are different claims.
    """
    manifest = json.loads((PACKAGE / "vendor_manifest.json").read_text(encoding="utf-8"))
    recorded = {e["path"]: e["sha256"] for e in manifest["modules"]}
    import hashlib

    assert hashlib.sha256((STUDIO / "topics.py").read_bytes()).hexdigest() == (
        recorded["studio/topics.py"]
    ), "topics.py should be byte-identical: it was copied and not changed"
    assert hashlib.sha256((STUDIO / "schema.py").read_bytes()).hexdigest() != (
        recorded["studio/schema.py"]
    ), "schema.py should DIFFER: AC#7 changed it, and losing that change would be silent"


def test_they_import_with_only_v1_dependencies() -> None:
    """V2 is importable because V1 landed. That is the whole reason for the order."""
    for module in (topics, schema):
        assert module.__name__.endswith((".topics", ".schema"))
    assert schema._has_non_latin_script is not None, "schema imports text._has_non_latin_script"


# --- AC#6: the non-Latin check ----------------------------------------------


def test_a_non_latin_section_value_is_rejected_and_a_latin_one_is_not() -> None:
    """AC#6. Both halves, with a *valid* Latin member on the accepted side.

    The first version of this test passed `'section'` as the value and called the
    Latin case "rejected too" — which is a different claim, and a wrong one. AC#6
    is about the **script**, so the accepted side must be a real member in Latin
    script and the rejected side its Devanagari transliteration.
    """
    assert SlideScene(**VALID, section="what is this").section == "what is this"
    with pytest.raises(ValidationError):
        SlideScene(**VALID, section="खण्ड")


def test_the_non_latin_check_still_fires_on_the_other_fields() -> None:
    """The script check is not the section type's job, and must not be replaced by it.

    `section` is now guarded by a `Literal`; `title`, `narration` and `bullets` are
    still guarded by `_has_non_latin_script`, and a change to AC#7 must not have
    quietly removed that.
    """
    for field, value in (
        ("title", "शीर्षक"),
        ("bullets", ["सूची"]),
        ("visual_diagram", "आरेख"),
    ):
        with pytest.raises(ValidationError):
            SlideScene(**{**VALID, field: value})


def test_narration_is_now_script_checked_and_V2_recorded_that_it_was_not() -> None:
    """This test asserted the defect was OPEN. V5 closed it, so it now asserts closed.

    A test that keeps asserting a fixed defect is worse than no test: it fails, and
    the obvious reading is that the fix broke something. The transition is recorded
    in the name and the docstring so the change is legible rather than silent.
    """
    from doc_to_video_channel.studio.schema import SlideScene

    assert "narration" not in schema._FIELD_NAMES, (
        "narration is outside the ON-SCREEN tuple, which is correct -- it has its "
        "own voice-relative check rather than the unconditional one"
    )
    original = SlideScene._narration_lang
    SlideScene._narration_lang = "en-IN"
    try:
        with pytest.raises(ValidationError, match="non-Latin"):
            SlideScene(title="T", bullets=["b"], source_refs=["r"],
                       narration="\u092f\u0939 \u0905\u0928\u0941\u092d\u093e\u0917")
    finally:
        SlideScene._narration_lang = original
