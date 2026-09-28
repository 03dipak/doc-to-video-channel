"""V7: the storyboard -> plan seam, and the gaps it refuses to paper over.

The seam's job is to hand the renderer a plan that is **valid** and to refuse, by
name, everything about the storyboard that is not yet good enough. A seam that
fills gaps is worse than no seam, because it makes an unsourced lesson render
cleanly.

Each test states the failure it was written to catch. The refusals are tested first
where a pass and a refusal could be confused.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from doc_to_video_channel.projector import (
    BULLET_LIMIT,
    CHAPTER_SECTIONS,
    _step_text,
    project,
    scene_budget,
)
from doc_to_video_channel.storyboard import Citation, load

ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = ROOT / "storyboards" / "uv-install.storyboard.json"


@pytest.fixture
def board() -> Any:
    loaded, gaps = load(BOARD_PATH)
    assert not gaps, f"the storyboard under test has gaps: {gaps}"
    return loaded


# --- the citation block must survive the load ---------------------------------


def test_citations_survive_the_load(board: Any) -> None:
    """THE DEFECT THIS SEAM FOUND. `load()` read `provenance`, kept four of its five
    keys, and **discarded `citations`**. So the one block that makes the lesson
    traceable never left the JSON, and the first projection anchored **0 of 8
    scenes** while reporting a content problem rather than an empty lookup.

    A trace check that fails closed for the wrong reason is worse than one that
    fails open: it sends you to edit content that is fine.
    """
    assert board.citations, "the provenance citations were dropped at load"
    for citation in board.citations:
        assert citation.verbatim.strip(), (
            f"a citation with no quote cannot anchor anything: {citation.claim!r}"
        )
        assert citation.url.strip(), f"a citation with no locator: {citation.claim!r}"


def test_a_storyboard_with_no_citations_is_a_blocking_gap(tmp_path: Path) -> None:
    """Wrong input first: the loader must refuse, not return an empty list quietly."""
    raw = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
    raw["provenance"]["citations"] = []
    target = tmp_path / "no-citations.json"
    target.write_text(json.dumps(raw), encoding="utf-8")
    _, gaps = load(target)
    kinds = {g.kind for g in gaps}
    assert "no_citations" in kinds, f"an uncited storyboard loaded clean: {gaps}"


def test_a_citation_without_a_verbatim_quote_is_a_blocking_gap(tmp_path: Path) -> None:
    raw = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
    raw["provenance"]["citations"][0].pop("verbatim")
    target = tmp_path / "no-quote.json"
    target.write_text(json.dumps(raw), encoding="utf-8")
    _, gaps = load(target)
    assert "citation_without_verbatim" in {g.kind for g in gaps}, (
        "a citation with no quote matches nothing, so it anchors nothing, and must "
        "not load as though it were evidence"
    )


# --- refusals: the seam must not invent ---------------------------------------


def test_the_seam_refuses_to_ship_a_plan_with_unanchored_scenes(board: Any) -> None:
    """THE HEADLINE RESULT, and it is a refusal. Measured on the real storyboard:
    1 of 8 scenes is anchored and 7 are not, because the storyboard ships 3
    citations that all cover installation while the session teaches 15 steps
    including project creation, dependencies, lock/sync and running code.

    The correct output is a plan that says so. The incorrect output is 8 scenes
    each carrying a plausible-looking reference nobody checked -- which is the
    channel's one non-negotiable.
    """
    result = project(board)
    assert not result.shippable, "a plan with unanchored scenes reported as shippable"
    assert result.unanchored, "the real storyboard is known to have unanchored scenes"
    assert len(result.unanchored) == 7
    assert "unanchored_scene" in {g.kind for g in result.gaps}


def test_an_anchored_scene_carries_the_citation_whose_quote_it_contains(
    board: Any,
) -> None:
    """Matching is on the verbatim quote, so the check is a fact about the text."""
    result = project(board)
    anchored = [s for s in result.plan["scenes"] if s["source_refs"]]
    assert len(anchored) == 1
    scene = anchored[0]

    # The scene holds BOTH of chapter one's first group, and only the first of them
    # is anchored. So the anchor is checked against the specific step whose text
    # carries the quote -- not against the scene, which also contains an unanchored
    # step, and not against "the first step", which is an assumption about grouping
    # that happened to be wrong when this test was first written.
    step = next(s for s in board.steps() if s.id == "install-uv")
    assert "install-uv" in scene["_step_ids"]
    quote = scene["_citations"][0]["verbatim"]
    assert quote in _step_text(step), (
        "the anchor must be a quote that literally appears in the step it supports"
    )
    assert scene["_step_ids"] != ["install-uv"], (
        "if this scene is ever one step wide, re-check that the quote still matches "
        "that step rather than assuming it does"
    )


def test_a_step_with_no_matching_citation_is_named_not_skipped(board: Any) -> None:
    result = project(board)
    assert all("/" in where for where in result.unanchored), (
        f"an unanchored scene must be locatable: {result.unanchored}"
    )


def test_the_final_clip_style_claim_gap_is_reported(board: Any) -> None:
    """The storyboard has no `takeaways`, and a lesson with no takeaway does not
    satisfy the channel contract. Nothing in the seam can write one."""
    result = project(board)
    assert "no_takeaways" in {g.kind for g in result.gaps}
    assert result.plan["takeaways"] == []


# --- the plan the renderer receives -------------------------------------------


def test_the_projected_plan_satisfies_the_renderer_schema(board: Any) -> None:
    """The contract the renderer actually enforces, checked by running it."""
    from doc_to_video_channel.studio.schema import LessonPlan

    plan = project(board).plan
    LessonPlan(**plan)


def test_every_projected_section_is_a_schema_member(board: Any) -> None:
    """`schema.canonical_section` is the gate, and it used to hold a third copy of
    the vocabulary. Adding the channel's chapters to `config._SECTIONS` alone
    changed nothing -- the schema still listed five members and refused all eight
    scenes. Now the runtime list derives from config, so this test fails the moment
    a chapter maps to something unadmitted."""
    from doc_to_video_channel.studio.schema import canonical_section

    for scene in project(board).plan["scenes"]:
        if scene.get("section"):
            assert canonical_section(scene["section"]) == scene["section"]


def test_bullets_respect_the_schema_cap_and_report_what_they_dropped(board: Any) -> None:
    """`schema.SlideScene.bullets` is `max_length=4`, and three steps contribute up
    to nine authored fields. A cap that silently drops five of nine teaches less
    than the storyboard says, so the drop count is reported as a gap."""
    from doc_to_video_channel.studio.schema import SlideScene

    result = project(board)
    for scene in result.plan["scenes"]:
        assert len(scene["bullets"]) <= BULLET_LIMIT
        SlideScene(**scene)
    dropped = [g for g in result.gaps if g.kind == "bullets_dropped"]
    assert dropped, "15 steps into 8 scenes must drop something, and it must be said"


def test_source_refs_are_strings_because_the_schema_says_so(board: Any) -> None:
    """`source_refs: list[str]`. A dict per ref is refused at validation, so the
    locator goes in the ref and the full citation rides alongside under
    `_citations` -- nothing traceable is lost to satisfy a type."""
    for scene in project(board).plan["scenes"]:
        for ref in scene["source_refs"]:
            assert isinstance(ref, str) and ref.strip()
        if scene["source_refs"]:
            assert scene["_citations"], "the full citation must survive beside the ref"


def test_the_narration_carries_no_invented_connectives(board: Any) -> None:
    """Steps are joined with a full stop, not with words.

    Measured: the first version used "First, " and " Then, ", and of the 7 narration
    repeats `guard_plan` reported, **2 were caused by those two strings** -- the join
    manufactured the repetition the gate looks for. A join that is meant to be
    contentless still forms trigrams.
    """
    for scene in project(board).plan["scenes"]:
        assert "First, " not in scene["narration"]
        assert " Then, " not in scene["narration"]


def test_the_opening_is_a_start_state_not_a_goal(board: Any) -> None:
    """Every chapter's `goal` is the state the chapter ENDS in, so the first
    version opened the lesson by announcing chapter one's outcome. The opening is
    the first sentence a viewer reads and it has to be where the learner is."""
    result = project(board)
    assert result.plan["opening"] == board.chapters[0].start_state.strip()
    for chapter in board.chapters:
        assert result.plan["opening"] != chapter.goal.strip()


# --- the scene budget, which is arithmetic and must add up -------------------


@pytest.mark.parametrize(
    "per_chapter",
    [
        [4, 3, 2, 2, 4],
        [1, 1, 1],
        [12],
        [1, 11],
        [5, 5, 5, 5, 5, 5],
    ],
)
def test_scene_budget_sums_to_the_scenes_built(per_chapter: list[int]) -> None:
    """A budget that is computed and then not honoured is a stored claim.

    15 steps against `AUTO_TRIM_MAX_SCENES = 12` will not fit one scene per step, so
    grouping is arithmetic. Every chapter keeps at least one scene, no chapter gets
    more scenes than it has steps, and the total is exactly the target.
    """
    total = sum(per_chapter)
    budget = scene_budget(total, per_chapter)
    assert sum(budget) == min(8, total)
    assert len(budget) == len(per_chapter)
    for scenes, steps in zip(budget, per_chapter, strict=True):
        assert 1 <= scenes <= steps


def test_every_step_lands_in_exactly_one_scene(board: Any) -> None:
    """Grouping reorders nothing and drops nothing."""
    result = project(board)
    placed = [sid for scene in result.plan["scenes"] for sid in scene["_step_ids"]]
    expected = [s.id for s in board.steps()]
    assert placed == expected, "the projection dropped or reordered steps"


def test_chapter_sections_cover_every_chapter(board: Any) -> None:
    assert set(CHAPTER_SECTIONS) == {c.id for c in board.chapters}, (
        f"chapters with no section label: "
        f"{sorted({c.id for c in board.chapters} - set(CHAPTER_SECTIONS))}"
    )


def test_a_chapter_with_no_section_mapping_is_reported() -> None:
    """Wrong input: an unmapped chapter gets `None`, not a borrowed label."""
    from doc_to_video_channel.projector import CHAPTER_SECTIONS as mapping
    from doc_to_video_channel.storyboard import Chapter, Storyboard

    unmapped = Chapter(
        id="not-in-the-map", title="T", start_state="s", goal="g",
        steps=(
            __import__("doc_to_video_channel.storyboard", fromlist=["Step"]).Step(
                id="s1", purpose="Do a thing.", precondition="p", command="true",
                expected_output_pattern="x", checkpoint="c", state_change="",
                common_failure="",
            ),
        ),
    )
    board = Storyboard(
        id="b", title="T", source_document="s.md", authored_by="a",
        authored_on="2026-09-28", environment_of_record="uv 0.12.2",
        citations=(Citation("c", "u", "v"),), chapters=(unmapped,),
    )
    result = project(board)
    assert "unmapped_chapter" in {g.kind for g in result.gaps}
    assert result.plan["scenes"][0]["section"] == ""
    assert mapping  # the mapping is the thing under test, not its absence
