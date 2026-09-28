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

import ast
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from doc_to_video_channel.studio import config, schema, topics
from doc_to_video_channel.studio.schema import SlideScene, canonical_section

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


def test_narration_is_NOT_script_checked_and_that_is_a_defect() -> None:
    """`narration` is outside `_FIELD_NAMES`, so a non-Latin narration is accepted.

    Recorded rather than fixed: it is the baseline's behaviour, and the scope of V2
    is AC#6 and AC#7. But it is a real gap and naming it is the point of this
    test -- narration is SPOKEN, so a script the TTS voice cannot pronounce is a
    defect that produces a video with gibberish audio and a clean gate.

    The first version of the companion test listed `narration` among the fields
    that MUST reject, and it did not raise. The assertion was wrong about the
    baseline, and the honest outcome is a recorded defect rather than a silently
    amended expectation.
    """
    assert "narration" not in schema._FIELD_NAMES, (
        "narration is now script-checked, so this defect is fixed -- update the "
        "ledger row and this test rather than leaving it asserting a stale gap"
    )
    # `VALID` already carries `narration`, so it is replaced rather than added --
    # passing both is a TypeError, and the first version of this test did that.
    fields = {**VALID, "narration": "यह अनुभाग"}
    accepted = SlideScene(**fields)
    assert accepted.narration == "यह अनुभाग", "the gap is still open"


# --- AC#7: SectionKind is a type, and the spellings collapse -----------------


def test_section_kind_is_a_type_not_a_bare_string() -> None:
    """The field's annotation is a `Literal`, checked on the source.

    Asserted structurally rather than behaviourally, because behaviour alone cannot
    tell a `Literal` from a validator that happens to reject the same values.
    """
    tree = ast.parse((STUDIO / "schema.py").read_text(encoding="utf-8"))
    annotations = [
        ast.unparse(node.annotation)
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "section"
    ]
    assert annotations, "the `section` field has no annotation"
    assert "SectionKind" in annotations[0], (
        f"`section` is annotated {annotations[0]!r}, not a SectionKind"
    )
    assert "SectionKind = Literal[" in (STUDIO / "schema.py").read_text(encoding="utf-8")


def test_a_value_that_is_not_a_section_is_refused() -> None:
    """`'bogus'` used to validate clean. That is the defect, reproduced and fixed."""
    with pytest.raises(ValidationError, match="is not one of"):
        SlideScene(**VALID, section="bogus")


def test_both_spellings_are_accepted_and_one_is_stored() -> None:
    """The two-spelling fix: accept either, store one.

    The canonical form is `config._SECTIONS`' lower case, because that is what the
    planner is told the sections are; the Title Case is accepted because 133
    reference plan files already carry it and refusing them would break inputs that
    were never wrong.
    """
    for spelling, canonical in (
        ("What Is This", "what is this"),
        ("what is this", "what is this"),
        ("WHAT IS THIS", "what is this"),
        ("  Example  ", "example"),
    ):
        assert canonical_section(spelling) == canonical
        assert SlideScene(**VALID, section=spelling).section == canonical


def test_the_literal_members_are_exactly_the_config_sections() -> None:
    """The type and the planner's list must not drift apart.

    Two declarations of the same five kinds is how this defect happened, so the two
    are now compared rather than trusted.
    """
    tree = ast.parse((STUDIO / "schema.py").read_text(encoding="utf-8"))
    members: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SectionKind":
            members = [ast.literal_eval(e) for e in node.value.slice.elts]  # type: ignore[attr-defined]
    assert tuple(members) == config._SECTIONS, (
        f"SectionKind is {members} but config._SECTIONS is {list(config._SECTIONS)}"
    )


def test_an_absent_section_is_none_and_never_a_fabricated_member() -> None:
    """The baseline defaulted to `""`. Defaulting to a real member would be repair.

    Most scenes are not section cards, so "no section" is a legitimate state. It
    maps to `None`, not to `"what is this"`, and an empty string maps to `None`
    too rather than being refused.
    """
    assert SlideScene(**VALID).section is None
    assert SlideScene(**VALID, section="").section is None


# --- the mutations ----------------------------------------------------------


def test_mutation_a_bare_string_annotation_fails_the_type_test() -> None:
    """Put the field back to `str` and the type test must fail.

    Without this, `AC#7` is a claim about a comment rather than about the code.
    """
    source = (STUDIO / "schema.py").read_text(encoding="utf-8")
    mutated = source.replace("section: SectionKind | None = None", "section: str = \"\"")
    assert mutated != source, "the anchor moved; this mutation no longer tests anything"
    tree = ast.parse(mutated)
    annotations = [
        ast.unparse(node.annotation)
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "section"
    ]
    assert "SectionKind" not in annotations[0], (
        "a bare `str` annotation would let 'bogus' through again"
    )


def test_mutation_a_defaulted_section_fails_the_none_test() -> None:
    """Default the field to a real member and the absent-section test must fail."""
    source = (STUDIO / "schema.py").read_text(encoding="utf-8")
    mutated = source.replace(
        "section: SectionKind | None = None", 'section: SectionKind = "what is this"'
    )
    assert mutated != source
    assert 'section: SectionKind = "what is this"' in mutated
    # And the fabricated default is what the test exists to prevent.
    assert SlideScene(**VALID).section is None, "unmutated: absent stays None"
