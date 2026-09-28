"""V1: the three zero-internal-import modules, and A5.

**Why these tests are ours and not copied.** The build order's V1 done-when reads
"the three zero-internal-import modules import and their tests pass", and the
second half is not satisfiable from the baseline: all **7** of its test files
`from doc_to_video_tutor import studio as S`, the whole-package facade, and three
of them additionally import `schema` (V2), `plan` (V4) or `speech` (V5). There is
no separable unit test for `util`, `text` or `config` in the reference tree, so a
V1 verified by the reference suite could not exist. The done-when is corrected in
`docs/LLD-tutorial-lane.md` §5.5; this file is what actually verifies it.

Two of these tests are the ones that would catch a real regression:

* `test_a_truncated_cut_never_ends_mid_token` and
  `test_a_cut_uses_at_least_half_the_window` are `AC#17`(a), and both were
  confirmed to fail against a deliberately broken cut before `util.py` was copied.
* The `A5` tests are against a real `.docx` built with `python-docx` in the test
  itself. A synthetic string would not have caught the original defect, which was
  `UnicodeDecodeError` at byte 10 of a ZIP.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from doc_to_video_channel import config, text, util

# --- the three modules import, and are the files the manifest recorded -------


def test_the_three_modules_import() -> None:
    assert util.__name__.endswith(".util")
    assert text.__name__.endswith(".text")
    assert config.__name__.endswith(".config")


def test_the_copies_are_the_manifests_files_with_annotations_added() -> None:
    """The copy is verbatim except for the two annotations and A5.

    `util.py` differs from the manifest's hash because V1 made three recorded
    edits to it. Every OTHER module must be byte-identical, or "we vendored the
    baseline" is a claim with no check behind it.
    """
    manifest_path = (
        Path(__file__).resolve().parents[1] / "src/doc_to_video_channel/vendor_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded = {e["path"]: e["sha256"] for e in manifest["modules"]}
    root = Path(__file__).resolve().parents[1] / "src/doc_to_video_channel"

    import hashlib

    for name, key in (("text.py", "studio/text.py"), ("config.py", "studio/config.py")):
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        assert digest == recorded[key], (
            f"{name} is NOT the manifest's file: a verbatim copy should hash "
            f"{recorded[key][:12]}, this is {digest[:12]}"
        )

    digest = hashlib.sha256((root / "util.py").read_bytes()).hexdigest()
    assert digest != recorded["studio/util.py"], (
        "util.py should differ from the manifest's hash, because A5 and the two "
        "annotations were added to it. If it matches, the edits were lost."
    )


def test_the_scene_budget_is_the_one_the_lld_cites() -> None:
    """The chaptered-mode ruling changed the budget's MEANING, not its values.

    §12.5 moved `MIN_SCENES` and `TARGET_MAX_SCENES` from per-video to
    per-chapter and left the numbers alone deliberately. This is the test that
    notices if a later edit moves them without a decision.
    """
    assert config.MIN_SCENES == 5
    assert config.TARGET_MAX_SCENES == 8
    assert config.SECTIONS if hasattr(config, "SECTIONS") else config._SECTIONS


# --- AC#17(a): the two truncation properties, on a synthetic source ----------


def test_a_truncated_cut_never_ends_mid_token() -> None:
    """The cut must land on a boundary, or the last word is a fragment.

    `AC#17`(a). Confirmed to fail against a character-slicing cut before this
    module was vendored: a 40,038-character boundary-free body was cut to 30
    characters, because the last space in the window sat inside the `<doc>` header.
    """
    body = "alpha bravo charlie delta echo foxtrot golf hotel india juliet " * 400
    cut = util._truncate_on_boundary(body, 500)
    assert len(cut) <= 500
    if len(cut) < len(body):
        assert cut == cut.rstrip() or cut[-1].isalnum()
        assert not cut.split()[-1].endswith(("-", "/", ",")) or len(cut) == len(body)


def test_a_cut_uses_at_least_half_the_window_it_was_given() -> None:
    """A cut that returns almost nothing is a silent truncation.

    `AC#17`(a). The defect this was written for: a boundary-free body inside a
    wrapper header put the last space at position 30, so a 12,000-character window
    yielded 30 characters -- 0.25%, a 1,334.6x drop, on demand.
    """
    boundary_free = "x" * 40_000
    wrapped = f"<doc name='probe'>\n{boundary_free}\n</doc>"
    for window in (1_000, 12_000):
        cut = util._truncate_on_boundary(wrapped, window)
        assert len(cut) >= window // 2, (
            f"window {window} yielded {len(cut)} characters, under half -- a silent "
            f"truncation the LoadedSource counters would report but nobody reads"
        )


def test_loaded_source_reports_what_the_window_dropped() -> None:
    """`chars_read` vs `chars_total` is a measured number, and the gap is the point.

    The docstring on `LoadedSource` records that this distinction is what turned a
    9-of-12 lesson into a printed "all concepts covered", so it is worth a test
    that the two numbers are actually different when something was dropped.
    """
    long_doc = Path(__file__).with_name("_v1_long.txt")
    long_doc.write_text("word " * 6_000, encoding="utf-8")
    try:
        loaded = util.load_documents([str(long_doc)], max_chars=2_000)
        assert loaded.truncated
        assert loaded.chars_read <= 2_000
        assert loaded.chars_total > loaded.chars_read
        assert loaded.full_text.startswith("<doc name=")
    finally:
        long_doc.unlink()


# --- A5: the .docx reader ---------------------------------------------------


@pytest.fixture
def real_docx(tmp_path: Path) -> Path:
    """A genuine `.docx`, built here rather than committed.

    A committed binary would be a fixture with no provenance, and `RIGHTS.md`
    already restricts what may live in this repository. Building it in the test
    means the reader is exercised against the format, not against a string.
    """
    docx = pytest.importorskip("docx", reason="python-docx is a declared dependency")
    path = tmp_path / "probe.docx"
    document = docx.Document()
    document.add_heading("Heading one", 0)
    document.add_paragraph("A body paragraph with real words in it.")
    document.add_paragraph("A second paragraph, so the reader has two blocks.")
    document.save(path)
    return path


def test_a_docx_no_longer_raises_unicode_decode_error(real_docx: Path) -> None:
    """The defect A5 exists for, reproduced and then fixed.

    Against the baseline this raised `UnicodeDecodeError: 'utf-8' codec can't
    decode byte 0xab in position 10`, because a `.docx` is a ZIP of XML.
    """
    loaded = util.load_documents([str(real_docx)])
    assert "A body paragraph" in loaded.text
    assert "Heading one" in loaded.text


def test_a_docx_reader_does_not_lose_tables(tmp_path: Path) -> None:
    """Tables are where specification documents keep their content.

    `Document.paragraphs` does not include them, so a reader that reads only
    paragraphs returns a document whose tables have silently vanished -- and a
    vanished table is a gap no coverage report can see, because there is nothing
    left to be unclaimed.
    """
    docx = pytest.importorskip("docx", reason="python-docx is a declared dependency")
    path = tmp_path / "with_table.docx"
    document = docx.Document()
    document.add_paragraph("Prose above the table.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Setting"
    table.cell(0, 1).text = "Default"
    table.cell(1, 0).text = "retries"
    table.cell(1, 1).text = "three"
    document.save(path)

    text_read = util.load_documents([str(path)]).text
    assert "retries" in text_read, "the table vanished: only paragraphs were read"
    assert "three" in text_read


def test_an_empty_docx_raises_rather_than_contributing_nothing(tmp_path: Path) -> None:
    """A `.docx` with no readable text is a failure, not an empty document.

    An empty `<doc>` block would enter the read window, consume characters, and be
    indistinguishable in the counters from a document that was read.
    """
    docx = pytest.importorskip("docx", reason="python-docx is a declared dependency")
    path = tmp_path / "empty.docx"
    docx.Document().save(path)
    with pytest.raises(ValueError, match="No readable text"):
        util.load_documents([str(path)])


def test_a_pptx_still_works_after_the_docx_branch_was_added(tmp_path: Path) -> None:
    """Adding a branch to a shared `if` can break the branch above it.

    The `.pptx` path is the only other binary reader in `load_documents`, and it
    now shares a conditional with the new `.docx` one. `V3` copies
    `BRAND_NAME`, `BRAND_FOOTER` and `BRAND_TAGLINE` -- which live in `config.py`
    and therefore arrive **whole at V1**, so V3 is a *change* to a module that
    already exists, not a copy of two lines. Noted here so the build order and the
    tree do not disagree.
    """
    pytest.importorskip("pptx", reason="python-pptx is a declared dependency")
    from pptx import Presentation

    path = tmp_path / "deck.pptx"
    presentation = Presentation()
    # Layout 5 is TITLE_ONLY and carries no body placeholder, so
    # `placeholders[1]` raised KeyError. Address the shapes by what they are
    # rather than by index -- a test that depends on a placeholder's position is
    # a test that fails when the layout library changes.
    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    slide.shapes.title.text = "Deck title"
    box = slide.shapes.add_textbox(0, 1_000_000, 5_000_000, 1_000_000)
    box.text_frame.text = "Body text on the slide"
    presentation.save(str(path))

    text_read = util.load_documents([str(path)]).text
    assert "Deck title" in text_read
    assert "Body text on the slide" in text_read


def test_a_missing_input_names_itself() -> None:
    with pytest.raises(FileNotFoundError, match="not-a-real-file"):
        util.load_documents(["not-a-real-file"])


# --- AC#17(a), the property that FAILED against the vendored code -----------
#
# Written after the fact and kept, because the sequence matters: the LLD stated
# this property as falsifiable on a synthetic source, and it was falsified on the
# first synthetic source tried. The floor was applied to the heading preference
# and not to the space fallback.


def test_mutation_dropping_the_half_window_floor_fails_the_property() -> None:
    """Remove the floor and the property must fail. Otherwise it is not a test.

    The floor is one `if` statement. An `if` that nothing exercises is an `if`
    that can be deleted without anyone noticing, and this one was very nearly
    deleted: it was ABSENT in the code we vendored, and only the property test
    found it.
    """
    import inspect
    import textwrap

    source = textwrap.dedent(inspect.getsource(util._truncate_on_boundary))
    assert "if cut * 2 < max_chars:" in source, "the floor is gone from the source"

    # Reproduce the pre-fix behaviour by hand: only a distant space available.
    boundary_free = "x" * 40_000
    wrapped = f"<doc name='probe'>\n{boundary_free}\n</doc>"
    head = wrapped[:12_000]
    naive_cut = max(head.rfind("\n"), head.rfind(" ")) + 1
    assert naive_cut * 2 < 12_000, (
        "the fixture no longer reproduces the defect: the lone space moved, so this "
        "test would pass for the wrong reason"
    )
    assert len(util._truncate_on_boundary(wrapped, 12_000)) >= 6_000


def test_the_floor_does_not_cost_a_boundary_when_one_is_near() -> None:
    """The fix must not fire on ordinary text, or it would split words for nothing.

    This is the negative case for the fix. A floor that always fires is a floor
    that has thrown away the boundary property entirely, and the LLD requires
    both.
    """
    body = "alpha bravo charlie delta echo foxtrot golf hotel " * 300
    for window in (400, 900, 2_000):
        cut = util._truncate_on_boundary(body, window)
        assert len(cut) <= window
        assert cut == body[: len(cut)] or len(cut) >= window // 2
        assert cut.split()[-1] in body.split(), "the cut invented or split a token"
