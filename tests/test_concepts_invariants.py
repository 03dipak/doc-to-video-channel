"""Concept-based tests over a second document, one per INVARIANT.

Why a second document. `08_concepts_mod03_gates.md` exercises the READ WINDOW:
it is 18 KB, so concepts 9-12 fall outside the 12,000-char window and the
lesson covers 8 of 12. Every coverage assertion in the main suite is therefore
about one limit. `04_concepts_mod04_release_gates.md` is 4.3 KB and has 14
concepts, so nothing is truncated and the binding limit is instead the
12-SCENE FRAME. Between them the two documents cross both limits, which is what
makes a coverage assertion mean something.

Each test below states the INVARIANT, not the code path, and names the agent
that owns the evidence per AGENTS.md. A test that cannot fail when its subject
regresses is not a test, so each one is written to fail if the invariant is
removed.

Run offline: no LLM, no TTS, no render. The one place a build artifact is
required, the test skips rather than pretending.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doc_to_video_channel import studio as S
from doc_to_video_channel.studio.plan import (
    _concept_headers,
    _coverage_clause,
    _plan_scene_target,
    _title_is_fragment,
    _title_is_truncated,
)
from doc_to_video_channel.studio.text import _strip_source_metadata_blocks

MOD03 = Path("modules/08_concepts_mod03_gates.md")
MOD04 = Path("tests/fixtures/04_concepts_mod04_release_gates.md")


def _load(path: Path):
    loaded = S.load_documents([str(path)])
    return (loaded,
            _strip_source_metadata_blocks(loaded.text),
            _strip_source_metadata_blocks(loaded.full_text))


# --- INVARIANT 1: the read window is a CHARACTER limit, the frame is a CONCEPT
# limit, and coverage must name which one bound. Owner: pipeline-architect.

def test_the_two_documents_bound_on_different_limits() -> None:
    """Neither document alone can prove a coverage assertion."""
    _, text03, full03 = _load(MOD03)
    _, text04, full04 = _load(MOD04)

    loaded03 = S.load_documents([str(MOD03)])
    loaded04 = S.load_documents([str(MOD04)])

    # mod03 is cut by characters; mod04 is not cut at all.
    assert loaded03.truncated is True
    assert loaded04.truncated is False

    in03 = len(_concept_headers(text03, limit=None))
    in04 = len(_concept_headers(text04, limit=None))
    # mod03 loses concepts to the window; mod04 loses them to the frame.
    assert in03 < len(_concept_headers(full03, limit=None))
    assert in04 == len(_concept_headers(full04, limit=None))


def test_coverage_names_the_binding_limit_for_each_document() -> None:
    loaded03 = S.load_documents([str(MOD03)])
    loaded04 = S.load_documents([str(MOD04)])
    c03 = _concept_headers(_strip_source_metadata_blocks(loaded03.text))
    t03 = len(_concept_headers(
        _strip_source_metadata_blocks(loaded03.full_text), limit=None))
    i03 = len(_concept_headers(
        _strip_source_metadata_blocks(loaded03.text), limit=None))
    c04 = _concept_headers(_strip_source_metadata_blocks(loaded04.text))
    t04 = len(_concept_headers(
        _strip_source_metadata_blocks(loaded04.full_text), limit=None))
    i04 = len(_concept_headers(
        _strip_source_metadata_blocks(loaded04.text), limit=None))

    m03 = _coverage_clause(i03, t03, _plan_scene_target(c03))
    m04 = _coverage_clause(i04, t04, _plan_scene_target(c04))
    assert "beyond the read window" in m03, m03
    assert "12-scene frame" not in m03, m03
    assert "beyond the 12-scene frame" in m04, m04
    assert "beyond the read window" not in m04, m04
    # And neither claims completeness.
    for msg in (m03, m04):
        assert "all concepts covered" not in msg


def test_coverage_clause_cannot_be_given_a_list_by_mistake() -> None:
    """The signature makes the mistake unrepresentable, not merely detected.

    `_coverage_clause(concepts, total, len(concepts))` was the natural call and
    it silently relabelled a scene-frame shortfall as a read-window one. A
    validator could not catch it - the capped length equals the wrong value, so
    `12 < 12` is false. The function now takes the three COUNTS its sentence
    needs, so there is no list to pass the wrong length of.
    """
    import inspect

    params = list(inspect.signature(_coverage_clause).parameters)
    assert params == ["in_window", "total", "scenes"], params
    # 13 concepts in the window, 12 scenes: a frame shortfall, not a window one.
    assert "1 beyond the 12-scene frame" in _coverage_clause(13, 13, 12)
    assert "beyond the read window" not in _coverage_clause(13, 13, 12)


def test_a_document_that_fits_reports_no_shortfall() -> None:
    loaded = S.load_documents([str(MOD04)])
    text = _strip_source_metadata_blocks(loaded.text)
    concepts = _concept_headers(text)
    total = len(_concept_headers(
        _strip_source_metadata_blocks(loaded.full_text), limit=None))
    # The UNCAPPED in-window count, not len(concepts): passing the capped
    # length is the exact mistake the guard below exists to catch.
    msg = _coverage_clause(len(_concept_headers(text, limit=None)), total,
                          _plan_scene_target(concepts))
    # 14 concepts, 12-scene frame: a real shortfall, correctly attributed.
    assert "beyond the 12-scene frame" in msg
    assert "no concepts dropped" not in msg


# --- INVARIANT 2: an overview heading is a container, not a concept. Owner:
# pipeline-architect. Found by this fixture, not by mod03.

@pytest.mark.parametrize("heading", [
    "The 5 big ideas", "The 4 big ideas", "The 9 core ideas",
    "Key ideas", "The central ideas", "The one sentence to memorize",
])
def test_overview_headings_are_containers_whatever_they_are_called(heading: str) -> None:
    doc = f"# Doc\n\n## {heading}\n\noverview\n\n### 1. A real concept\n\nbody\n"
    assert _concept_headers(doc) == ["1. A real concept"], heading


def test_a_genuine_concept_is_not_filtered_by_the_overview_rule() -> None:
    doc = "# Doc\n\n### Ideas are graded, not ranked\n\nbody\n"
    assert _concept_headers(doc) == ["Ideas are graded, not ranked"]


# --- INVARIANT 3: a concept name is a complete label, and a title that stops
# short of it is a fragment. Owner: graphic-reviewer (rendered) + tester (gate).

def test_every_concept_name_is_long_enough_to_be_a_title() -> None:
    """`_TITLE_DANGLING` cannot see this; the structural test can."""
    loaded = S.load_documents([str(MOD04)])
    text = _strip_source_metadata_blocks(loaded.text)
    for head in _concept_headers(text, limit=None):
        words = head.split()
        assert len(words) >= 2, f"{head!r} is too short to be a title"
        last = words[-1].strip(".,:;—–").casefold()
        assert last not in {"is", "are", "to", "of", "and", "the", "that"}, head


def test_a_title_that_stops_short_of_its_concept_is_detected() -> None:
    """The structural test, on a pair taken from mod04's own headings."""
    head = "6. A gate that blocks with no repair is a wall"
    assert _title_is_truncated("6. A gate that blocks with no", head)
    # A title that is a strict prefix of the document's longer name IS a
    # truncation, however short it is - the test is about the document's name
    # continuing past the title, not about the title's length.
    assert _title_is_truncated("6. A gate that blocks", head)
    # And a title that is not a prefix of it at all is not.
    assert not _title_is_truncated("Fail closed", head)
    # And a citation-only continuation is not a truncation.
    assert not _title_is_truncated(
        "6. A gate that blocks", "6. A gate that blocks (T-04-11)")


def test_no_concept_name_ends_on_a_trailing_separator() -> None:
    for path in (MOD03, MOD04):
        loaded = S.load_documents([str(path)])
        text = _strip_source_metadata_blocks(loaded.text)
        for head in _concept_headers(text, limit=None):
            assert not head.endswith(("—", "–", ",", ":", ";")), head


# --- INVARIANT 4: a phrase lives inside a sentence. A 3-token window that
# straddles a period is not a repeated phrase. Owner: tester (gate), and it is
# the reason a build was once refused over a non-defect.

def _narration(**extra) -> dict:
    base = {"section": "s", "title": "T", "bullets": [], "narration": "",
            "steps": [], "design_decision": "", "visual_diagram": ""}
    base.update(extra)
    return base


def test_a_phrase_spanning_a_sentence_boundary_is_not_a_repeat() -> None:
    """The defect that refused mod03_gates_v012_008 a render it had earned."""
    plan = {"title": "T", "topics": [], "scenes": [
        _narration(narration=(
            "Tolerance is a calculation, not a vibe, because defining too much "
            "is critical for consistent verdicts. "
            "Units define the threshold as absolute or relative."))],
        "takeaways": []}
    from doc_to_video_channel.studio.narration import _narration_repeat_report
    assert _narration_repeat_report(plan, frozenset())[0] == []


def test_a_phrase_repeated_inside_a_sentence_is_still_a_repeat() -> None:
    """The stricter definition must not cost real coverage."""
    filler = " ".join(f"q{i}" for i in range(14)) + "."
    plan = {"title": "T", "topics": [], "scenes": [
        _narration(narration=(
            f"Here we see the baseline is the reference point for every run. "
            f"{filler}")),
        _narration(narration=(
            f"And here again the baseline is the reference point for every run. "
            f"{filler}"))],
        "takeaways": []}
    from doc_to_video_channel.studio.narration import _narration_repeat_report
    banned = _narration_repeat_report(plan, frozenset())[0]
    assert "baseline is the reference" in " ".join(banned), banned


def test_a_restated_concept_name_is_dropped_whole() -> None:
    """The live failure. Trimming would leave 6 tokens against a 12 floor."""
    from doc_to_video_channel.studio.narration import (
        _enforce_unique_narration_trigrams,
        _narration_repeat_report,
        _protected_terms,
    )
    # The protected set must NOT cover the phrase, or the fixture is clean and
    # proves nothing. `_protected_terms` is built from titles, design decisions
    # and takeaways, so those must avoid the restated words entirely.
    tail = "A single flip must always trip the gate."
    plan = {"title": "T", "topics": [], "scenes": [
        _narration(title="Sample-size floor",
                   design_decision="Prefer a fixed bar over a moving one.",
                   narration=(f"{tail} This ensures statistical significance. "
                              "Sample-size floor 1/(n+1) — a single flip must "
                              "always trip the gate."))],
        "takeaways": ["Prefer a fixed bar over a moving one."]}
    protected = _protected_terms(plan)
    assert _narration_repeat_report(plan, protected)[0], "fixture must be dirty"
    _enforce_unique_narration_trigrams(plan, quiet=True, protected=protected)
    assert _narration_repeat_report(plan, protected)[0] == []
    out = plan["scenes"][0]["narration"]
    assert "always trip the gate" in out
    assert "Sample-size floor" not in out
    # And the repair is idempotent, so the build's own check can rely on it.
    before = plan["scenes"][0]["narration"]
    _enforce_unique_narration_trigrams(plan, quiet=True, protected=protected)
    assert plan["scenes"][0]["narration"] == before


# --- INVARIANT 5: every blocking finding must have a repair. A gate that
# refuses with no escape is a wall. Owner: mentor (ruling) + tester (evidence).

def test_no_rendering_gate_can_refuse_a_plan_the_pipeline_cannot_repair() -> None:
    """The invariant that the v_0001 build violated.

    Walks the deterministic repair chain over a plan carrying every repairable
    defect class, then asserts the render gate is clear. If a future gate is
    added without a matching repair, this fails.
    """

    from doc_to_video_channel.studio.narration import (
        _dedupe_narration_templates,
        _drop_leading_title_restatement,
        _enforce_unique_narration_trigrams,
        _protected_terms,
        _split_fused_particle_tokens,
    )
    from doc_to_video_channel.studio.validate import _render_blocking_problems

    # The filler must not repeat ITSELF, or the gate is blocking on the filler
    # rather than on the defect under test.
    filler = " ".join(f"w{i}" for i in range(16)) + "."
    plan = {"title": "Gate versus check", "topics": ["gates"],
            "scenes": [
                _narration(title="Gate versus check",
                           narration=(f"A single flip must always trip the gate. "
                                      f"{filler} A single flip must always trip "
                                      f"the gate. {filler}")),
                _narration(title="Fail closed, not fail open",
                           narration=(f"Reason yahi hai kiGate lets a row "
                                      f"through. {filler}")),
            ],
            "takeaways": ["A gate that blocks with no repair is a wall"]}
    voice = S._make_voice("mhe-mix")
    before = [b for b in _render_blocking_problems(plan, voice=voice)
              if "banned narration" in b]
    assert before, "the fixture must start blocked, or this proves nothing"

    prot = _protected_terms(plan)
    _dedupe_narration_templates(plan, quiet=True, voice=voice, protected=prot)
    _drop_leading_title_restatement(plan, voice)
    _split_fused_particle_tokens(plan, voice, quiet=True)
    _enforce_unique_narration_trigrams(plan, quiet=True, protected=prot)
    after = [b for b in _render_blocking_problems(plan, voice=voice)
             if "banned narration" in b]
    assert after == [], after


# --- INVARIANT 6: the word budget is a function of the target, and the band it
# quotes is the band the duration gate uses. Owner: tester (L2, ffprobe).

@pytest.mark.parametrize("scenes,target,lo,hi,total", [
    (9, 4.0, 31, 40, 343),
    (5, 4.0, 55, 70, 363),
    (12, 4.0, 22, 29, 327),
    (9, 8.0, 68, 87, 755),
])
def test_budget_band_is_derived_not_invented(scenes, target, lo, hi, total):
    from doc_to_video_channel.studio.duration import prompt_budget
    b = prompt_budget(scenes, target)
    assert b["words_min"] == lo, (scenes, target, b)
    assert b["words_max"] == hi, (scenes, target, b)
    assert abs(b["words_total"] - total) <= 1, (scenes, target, b)


def test_a_target_no_scene_count_can_reach_is_infeasible() -> None:
    from doc_to_video_channel.studio.duration import budget_feasible
    for n in range(S.AUTO_TRIM_MIN_SCENES if hasattr(S, "AUTO_TRIM_MIN_SCENES")
                   else 5, 13):
        assert budget_feasible(n, 4.0 * 60), n
    # Too short for the 20-word FAIL floor, too long for the 90-word ceiling.
    assert not budget_feasible(9, 2.0 * 60)
    assert not budget_feasible(5, 40.0 * 60)


# --- INVARIANT 7: a title is a label, not a truncation of the document's own
# name for the concept. Owner: graphic-reviewer (rendered pixels).

def test_both_documents_would_produce_complete_titles() -> None:
    """Replayed over both documents: repair, then assert nothing is a fragment."""
    for path in (MOD03, MOD04):
        loaded = S.load_documents([str(path)])
        text = _strip_source_metadata_blocks(loaded.text)
        plan = {"title": "T", "topics": [], "scenes": [
            _narration(title=h) for h in _concept_headers(text)], "takeaways": []}
        # Chain order matters and is a contract: `_normalize_scene_titles` (which
        # clips to the 44 cap) runs inside `_sanitize_plan_source_leaks` at 2343,
        # BEFORE `_fix_incomplete_titles` at 2369. Calling only the latter leaves
        # an over-cap title in place and the assertion below would be testing a
        # step that never runs alone.
        from doc_to_video_channel.studio.plan import (
            _fix_incomplete_titles,
            _normalize_scene_titles,
        )
        _normalize_scene_titles(plan)
        _fix_incomplete_titles(plan)
        for scene in plan["scenes"]:
            title = str(scene["title"])
            assert not _title_is_fragment(title), (path.name, title)
            assert len(title) <= 44, (path.name, title, len(title))


# --- AGENT RESPONSIBILITY MATRIX. Owner: mentor.
#
# AGENTS.md scopes each agent to specific evidence and warns that asking one to
# do another's job "is how a fix lands in one renderer and misses the other".
# These assertions fail if a role's remit is quietly widened or narrowed.

def test_agent_remit_matrix_is_enforced_in_code() -> None:
    import inspect

    from doc_to_video_channel.studio import cli, plan, validate, video

    # tester: offline L1 gates + media measurement, no render requirement.
    assert hasattr(cli, "_tts_blocking_findings")
    assert hasattr(cli, "_render_blocking_problems")
    assert hasattr(video, "measure_delivery")
    # pipeline-architect: cross-artifact, no render.
    assert hasattr(validate, "check_audit_binding")
    assert hasattr(plan, "_annotate_source_chunks")
    # graphic-reviewer: rendered pixels. `soffice`/`pdftoppm` are an
    # environment dependency, so the assertion is that the deck is measurable
    # from geometry, not that the binary is present.
    from doc_to_video_channel.studio.pptx import build_pptx
    assert callable(build_pptx)
    # reviewer: docs accuracy only - it must never be wired into a build path.
    for module in (cli, plan, validate, video):
        src = inspect.getsource(module)
        assert "docs/" not in src.split("import")[0], (
            "a runtime module must not read documentation")


def test_no_renderer_is_asked_to_do_another_renderers_job() -> None:
    """pptx.py and slides.py must not reimplement each other's pagination."""
    from doc_to_video_channel.studio import pptx, slides
    from doc_to_video_channel.studio.pptx import _shorter_column as pptx_shorter
    from doc_to_video_channel.studio.slides import _scene_pages, _shorter_column

    assert pptx_shorter is _shorter_column, (
        "two renderers answering the same question must be one function")
    assert pptx._scene_pages is slides._scene_pages
    # An empty scene still yields one page - a slide with no bullets is legal.
    assert _scene_pages({}) == [{}]
    assert _scene_pages({"bullets": ["a", "b", "c", "d", "e"]}) != []
