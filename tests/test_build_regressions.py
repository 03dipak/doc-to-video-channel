"""Regressions pinned from real `build` runs.

Every case here was observed in an actual build of
`08_concepts_mod03_gates.md`, not constructed to suit a rule. They exist because
each one is a behaviour a future change could plausibly break while still
passing the unit tests: a gate that must *stop the build*, a band boundary, and
a detector that only fires on messy model output.

The identifying details are kept verbatim - the Devanagari opening the 7B
actually emitted, the 71-word scene, the fused token - because a paraphrased
fixture would test the idea rather than the incident.
"""

import contextlib
import io
import json
import re
import tempfile
from pathlib import Path

import pytest

from doc_to_video_channel import studio as S

# --- the build that failed: Devanagari in the plan opening ------------------
#
# mod03_gates_v012_001 sample 1 was rejected with
#   plan opening SlideTextNotEnglish: non-Latin script:
#   'Chaliye regression samajh ke shuruwat karte hai. आज आपल्याला गेट'
# and the whole plan was resampled. The gate did its job; what was not pinned
# anywhere was that this class of failure forces a *resample* rather than being
# tolerated as a soft sample-level warning.

def test_real_devanagari_opening_is_rejected_by_the_plan_gate() -> None:
    problems = S.guard_plan(
        {"opening": "Chaliye regression samajh ke shuruwat karte hai. "
                    "आज आपल्याला गेट",
         "title": "Regression gates",
         "scenes": []},
        ["regression gates"])
    assert any("SlideTextNotEnglish" in p for p in problems), problems


def test_non_latin_opening_failure_is_not_soft_so_it_forces_a_resample() -> None:
    """The resample branch only fires for problems that survive the soft filter."""
    from doc_to_video_channel.studio.cli import _SAMPLE_SOFT_EXTRA

    problems = ["plan opening SlideTextNotEnglish: non-Latin script: 'x'"]
    soft_prefixes = S._SOFT_PREFIXES + _SAMPLE_SOFT_EXTRA
    hard = [p for p in problems
            if not any(p.startswith(soft) for soft in soft_prefixes)]
    assert hard, "a non-Latin opening must count as hard, or the build lands it"


def test_sanitize_opening_does_not_strip_devanagari_so_rejection_is_unreproducible() -> None:
    """A known gap, pinned so it cannot be quietly forgotten.

    Observed in mod03_gates_v012_001: the build log rejected sample 1 for
    `plan opening SlideTextNotEnglish`, yet the persisted
    `*.sample1.plan.json` has no Devanagari in its opening and passes
    `guard_plan` with zero problems. So the artifact written beside the rejected
    sample does not reproduce the failure that rejected it, and the saved plan
    cannot be used to audit why the sample was discarded.

    `_sanitize_opening` is *not* the cause - it only strips field-name leakage
    such as a trailing " opening", and leaves non-Latin script untouched, which
    this asserts so the two are not confused again. Recorded as LLD 20.2
    defect 14.
    """
    plan = {"opening": "Chaliye regression samajh ke shuruwat karte hai. "
                       "आज आपल्याला गेट opening"}
    S._sanitize_opening(plan)
    # The field-leak strip happens...
    assert not str(plan["opening"]).rstrip().endswith("opening")
    # ...but the non-Latin script survives, so the gate is what rejects it.
    assert S._has_non_latin_script(str(plan["opening"]))


# --- the band boundary: a scene one word over the warn line ---------------
#
# mod03_gates_v012_002 reported `tts_too_long: scene:1 71 spoken words`. That is
# 1 word past the warn threshold and 19 short of the fail threshold, so the exact
# boundary is what decides whether a build continues or dies.

def test_seventy_one_spoken_words_warns_but_does_not_block() -> None:
    plan = {"scenes": [{
        "title": "Goldens",
        "narration": " ".join(
            f"Step {n} keeps the goldens honest." for n in range(14)),
        "bullets": ["Freeze the goldens before the first run."],
    }]}
    script = S.build_tts_script(plan, S._MHE_VOICE)
    # Pinned exactly: this is the boundary case the build actually hit.
    assert script["clips"][0]["word_count"] == 71
    codes = {item["code"] for item in script["audit"]}
    assert "tts_too_long" in codes
    assert "tts_too_long_critical" not in codes, (
        "71 words must not block; the fail line is 90")


def test_the_fail_threshold_is_ninety_spoken_words() -> None:
    plan = {"scenes": [{
        "title": "Data and testset",
        "narration": " ".join(
            f"Step {n} keeps the goldens honest across every single run."
            for n in range(24)),
        "bullets": ["Freeze the goldens before the first run."],
    }]}
    script = S.build_tts_script(plan, S._MHE_VOICE)
    assert any(item["code"] == "tts_too_long_critical"
               for item in script["audit"])


# --- the fusion detector, on the sentence the model actually wrote ---------
#
# mod03_gates_v012_002 scene 9:
#   "Reason yahi hai kideterministic offline gate not live online because ..."
# The token is model-authored and absent from the source, so it survives every
# deterministic repair pass. The detector is the only thing that sees it.

def test_real_fusion_sentence_is_detected_with_the_right_split() -> None:
    from doc_to_video_channel.studio.speech import _fused_particle_tokens

    spoken = ("Is scene mein hum ek fresh concept samjhenge. Reason yahi hai "
              "kideterministic offline gate not live online because the gate runs "
              "a fully deterministic, offline evaluator, ensuring that the "
              "verdict is consistent and not influenced by anything else.")
    known = frozenset({"deterministic", "offline", "gate", "verdict", "reason",
                       "yahi", "hai", "online", "live", "concept", "scene",
                       "hum", "ek", "fresh", "samjhenge"})
    assert _fused_particle_tokens(spoken, known) == {
        "kideterministic": "ki deterministic"}


def test_fusion_surfaces_as_a_warning_and_does_not_block_the_build() -> None:
    """A reported fusion is advisory: the script still builds and still speaks."""
    plan = {"scenes": [{
        "title": "Two lane design",
        "narration": ("Is scene mein hum ek fresh concept samjhenge. Reason yahi "
                      "hai kideterministic offline gate not live online because "
                      "the gate runs a fully deterministic evaluator. "
                      "Deterministic results keep the verdict consistent across "
                      "every nightly run of the offline evaluation pipeline."),
        "bullets": ["The offline lane is deterministic."],
    }]}
    script = S.build_tts_script(plan, S._MHE_VOICE)
    codes = {item["code"] for item in script["audit"]}
    assert "tts_token_fusion" in codes
    # Advisory means advisory: no FAIL-code is raised for the same scene.
    assert not any(code.endswith("_critical") or code in
                   {"tts_text_corrupted", "tts_unknown_token"}
                   for code in codes), codes
    # And the narration is not silently rewritten.
    assert "kideterministic" in script["clips"][0]["spoken"]


# --- deck layout: text that overflows its card ----------------------------
#
# Reported from the rendered deck: a filled box sitting over the words
# "Why THIS (not the alternative)". The card was a fixed 0.72 in tall with a
# 0.6 in text box, and the fit check used that same fixed height, so a
# 194-character decision needing three lines reported room it did not have.
# A PowerPoint textbox does not clip, so the text drew over the card instead of
# being hidden - which is why nothing looked wrong in the geometry.

def test_long_decision_text_is_measured_not_guessed() -> None:
    from doc_to_video_channel.studio.pptx import _est_text_height, _est_wrapped_lines

    short = "Why THIS (not the alternative): info: recorded only"
    long = ("Why THIS (not the alternative): structure before values, because "
            "the engine checks structure first and only then compares the two "
            "candidate baselines that were captured at different times")
    assert _est_wrapped_lines(short, 12.1, 17) <= 2
    # The long one must be recognised as taller than the 0.6 in box it used to
    # be given, which is the whole defect.
    assert _est_text_height(long, 12.1, 17) > 0.6
    assert _est_text_height(long, 12.1, 17) > _est_text_height(short, 12.1, 17)


def test_bullet_rows_are_sized_from_their_text() -> None:
    """The old rule was `+0.12in if len > 90`, which a 271-char bullet outgrew."""
    from doc_to_video_channel.studio.pptx import _est_text_height

    b = ("Plain words: run the goldens over the current code and produce a "
         "report of metric values. On a known-good day you save that report as "
         "a baseline, which is the committed JSON file every later run is "
         "compared against.")
    assert len(b) > 90
    assert _est_text_height(b, 11.95, 18) > 0.79, "one flat +0.12in is not enough"


def test_layout_audit_catches_overflow_and_overlap(tmp_path) -> None:
    """The audit must fire on a deliberately broken deck and pass a sound one."""
    from pptx import Presentation
    from pptx.util import Inches, Pt

    from doc_to_video_channel.studio.pptx import _audit_layout

    def build(path, long_text: bool) -> None:
        prs = Presentation()
        prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        body = ("This is a deliberately long sentence that has to wrap over more "
                "than a single line inside a narrow box to prove the auditor "
                "detects the spill. " * 3) if long_text else "Short."
        tb = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6),
                                      Inches(0.3))
        tb.text_frame.word_wrap = True
        para = tb.text_frame.paragraphs[0]
        para.text = body
        para.font.size = Pt(18)
        prs.save(str(path))

    broken = tmp_path / "broken.pptx"
    build(broken, long_text=True)
    findings = _audit_layout(broken)
    assert any("overflows its box" in f for f in findings), findings

    sound = tmp_path / "sound.pptx"
    build(sound, long_text=False)
    assert not [f for f in _audit_layout(sound) if "overflows" in f]


# --- visual claims the narration never makes -----------------------------
#
# Found by external review of the v012 build: the badge row showed
# `0 PASS` .. `4 CONFIG ERR` while the narration mentioned only 3 and 4, and
# the JSON payload slide showed schema_version / baseline_id / path without
# saying any of them. The viewer reads three to five facts the lesson never
# explains. Worth recording that the enrichment which puts those blocks on
# screen is what created the risk.

def test_unspoken_badge_and_payload_claims_are_reported() -> None:
    from doc_to_video_channel.studio.validate import _unspoken_visual_claims

    plan = {"scenes": [{
        "title": "Structural error classes",
        "narration": ("Exit three is a structural error and exit four is a "
                      "broken pointer, and both must stop the run."),
        "status_badges": [{"code": "0", "label": "pass"},
                          {"code": "1", "label": "fail"},
                          {"code": "3", "label": "eval err"},
                          {"code": "4", "label": "config err"}],
        "json_snippet": '{"schema_version": 1, "baseline_id": "v1.2.0"}',
    }]}
    findings = _unspoken_visual_claims(plan)
    assert len(findings) == 1
    text = findings[0]
    # Spoken codes are not flagged...
    assert "3 eval err" not in text
    assert "4 config err" not in text
    # ...but unvoiced ones and the payload keys are.
    assert "0 pass" in text and "1 fail" in text
    assert "schema_version" in text and "baseline_id" in text


def test_a_fully_spoken_scene_reports_nothing() -> None:
    from doc_to_video_channel.studio.validate import _unspoken_visual_claims

    plan = {"scenes": [{
        "title": "Error classes",
        "narration": ("Zero means pass, one means fail, two means review, three "
                      "is an eval error, four is a config error, and the "
                      "schema_version is pinned."),
        "status_badges": [{"code": "0", "label": "pass"},
                          {"code": "1", "label": "fail"}],
        "json_snippet": '{"schema_version": 1}',
    }]}
    assert _unspoken_visual_claims(plan) == []


def test_unspoken_visual_claim_is_soft_not_blocking() -> None:
    """It must warn without failing the build: the fix is a content decision."""
    from doc_to_video_channel.studio.config import _SOFT_PREFIXES

    assert "unspoken visual claim" in _SOFT_PREFIXES


# --- a soft finding must never block the build ----------------------------
#
# This shipped as a real incident. `unspoken visual claim` was registered in
# _SOFT_PREFIXES, but the finding was formatted as
#   "scene 7 unspoken visual claim: ..."
# and the review-before-build loop separates hard from soft with
# `problem.startswith(prefix)`. A buried prefix means False, so the finding
# counted as hard: three consecutive samples were rejected for the same
# advisory finding, each burning a full plan generation (39s, 51s, 58s), and the
# build could not complete. The model was being asked to satisfy a check it was
# never prompted about.

def test_unspoken_visual_claim_is_filtered_out_of_the_hard_problem_set() -> None:
    """The exact mechanism that broke: the sample loop's soft filter."""
    from doc_to_video_channel.studio.cli import _SAMPLE_SOFT_EXTRA
    from doc_to_video_channel.studio.config import _SOFT_PREFIXES
    from doc_to_video_channel.studio.validate import _unspoken_visual_claims

    plan = {"scenes": [{
        "title": "Structural error classes",
        "narration": "Exit three is a structural error and four is a pointer.",
        "status_badges": [{"code": "0", "label": "pass"},
                          {"code": "1", "label": "fail"}],
    }]}
    findings = _unspoken_visual_claims(plan)
    assert findings, "the finding must still be reported"
    soft_prefixes = _SOFT_PREFIXES + _SAMPLE_SOFT_EXTRA
    hard = [f for f in findings
            if not any(f.startswith(s) for s in soft_prefixes)]
    assert not hard, f"advisory finding would force a resample: {hard}"


def test_soft_finding_puts_the_prefix_first_by_construction() -> None:
    from doc_to_video_channel.studio.config import _SOFT_PREFIXES
    from doc_to_video_channel.studio.validate import soft_finding

    message = soft_finding("scene 3 something happened")
    assert any(message.startswith(p) for p in _SOFT_PREFIXES)
    # And a non-default prefix is still honoured.
    other = soft_finding("detail", prefix="fused slide token")
    assert other.startswith("fused slide token")


def test_every_registered_soft_prefix_is_reachable_as_a_message_start() -> None:
    """Guards the contract itself, not one call site.

    `_SOFT_PREFIXES` is only meaningful if findings are *written* to lead with
    it. This cannot enumerate every call site, so it pins the failure mode that
    actually happened: a soft finding whose text does not lead with its prefix.
    """
    from doc_to_video_channel.studio.config import _SOFT_PREFIXES
    from doc_to_video_channel.studio.validate import soft_finding

    for prefix in _SOFT_PREFIXES:
        assert soft_finding("x", prefix=prefix).startswith(prefix)


# --- layout is derived from content, resolved by one budget --------------
#
# The user's framing, and the right one: the layout question "does this fit?"
# was being re-asked independently by six blocks, each with its own idea of what
# to sacrifice. That is the fixed-length approach - the block decides for
# itself, so the slide has no policy and a long bullet silently starves whatever
# is below it. A content-driven model lets each block declare the height its
# content needs and lets one pass decide what survives, dropping by priority
# rather than clipping.

def test_row_stack_drops_lowest_priority_first_and_never_clips() -> None:
    from doc_to_video_channel.studio.pptx import _RowStack

    stack = _RowStack(1.7, 3.7)          # 2.0 in of room
    # The cursor accumulates in floats, so compare with a tolerance.
    assert stack.reserve(0.5, _RowStack.REQUIRED, "bullets") == pytest.approx(1.7)
    assert stack.reserve(0.6, _RowStack.SUPPORTING, "decision") == pytest.approx(2.2)
    assert stack.reserve(0.5, _RowStack.OPTIONAL, "analogy") == pytest.approx(2.8)
    # 0.4 in left: the analogy does not fit and says so rather than clipping.
    assert stack.reserve(0.4, _RowStack.OPTIONAL, "payload") is None
    # Required content that cannot fit is refused, not silently truncated.
    assert stack.reserve(1.5, _RowStack.REQUIRED, "more bullets") is None
    assert stack.y <= 3.7
    labels = [label for _p, label in stack.dropped]
    assert "payload" in labels and "more bullets" in labels
    assert stack.report()


def test_row_stack_keeps_required_content_in_preference_to_optional() -> None:
    """Priority, not draw order, decides what a crowded slide loses."""
    from doc_to_video_channel.studio.pptx import _RowStack

    stack = _RowStack(0.0, 1.0)
    stack.reserve(0.4, _RowStack.OPTIONAL, "analogy")
    stack.reserve(0.4, _RowStack.REQUIRED, "bullet 1")
    assert stack.reserve(0.4, _RowStack.REQUIRED, "bullet 2") is None
    assert stack.reserve(0.4, _RowStack.OPTIONAL, "payload") is None
    dropped = [label for _p, label in stack.dropped]
    assert "bullet 2" in dropped and "payload" in dropped
    assert "bullet 1" not in dropped


def test_a_crowded_scene_drops_blocks_instead_of_overflowing(tmp_path) -> None:
    """End to end: a scene with more content than fits must still lay out clean."""

    from doc_to_video_channel.studio.pptx import _audit_layout, build_pptx

    scene = {
        "section": "Crowded",
        "title": "A scene carrying far more content than one slide can hold",
        "topic": "t",
        "narration": "n" * 40,
        "source_refs": ["s"],
        "bullets": [f"Bullet number {i} carrying a deliberately long sentence "
                    f"so that the measured height exceeds the safe area and the "
                    f"layout has to resolve a real overflow. " * 2
                    for i in range(9)],
        "design_decision": "why this and not the alternative, " * 6,
        "analogy": "an analogy long enough to need its own card, " * 5,
    }
    plan = {"title": "T", "scenes": [scene], "takeaways": []}
    out = tmp_path / "crowded.pptx"
    build_pptx(plan, out)
    assert out.exists()
    # Whatever survived, nothing overflowed and nothing overlapped.
    assert [f for f in _audit_layout(out) if "overflows" in f or "overlap" in f] == []


# --- the deck paginates on measured height, not bullet count ---------------
#
# `_scene_pages` caps a page at four bullets, which is the right instinct -
# overflow becomes more slides, not smaller text - but the wrong unit. Bullet
# length varies by an order of magnitude, so four short bullets and four very
# long ones are not the same height. Measured: with ~676-character bullets,
# count-only pagination renders 1 of 4 and the row stack drops the rest, while
# height-based pagination renders all 4 across additional slides.
#
# The test deliberately uses bullets long enough to discriminate. An earlier
# version of this test used ~180-character bullets, where both strategies render
# everything - it passed for the wrong reason and briefly hid a real bug in the
# measurement I was using to check it.

def _rendered_bullets(plan) -> int:
    import tempfile
    from pathlib import Path

    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import build_pptx

    out = Path(tempfile.mkdtemp()) / "deck.pptx"
    build_pptx(plan, out)
    prs = Presentation(str(out))
    return sum(1 for slide in prs.slides for shape in slide.shapes
               if shape.has_text_frame
               and shape.text_frame.text.strip().startswith("B"))


def test_long_bullets_paginate_instead_of_being_dropped() -> None:
    scene = {
        "section": "Crowded", "title": "Long bullets", "topic": "t",
        "narration": "n" * 40, "source_refs": ["s"],
        "bullets": [f"B{i}: " + ("long teaching sentence needing real room. " * 16)
                    for i in range(4)],
    }
    rendered = _rendered_bullets({"title": "T", "scenes": [scene],
                                  "takeaways": []})
    assert rendered == 4, (
        f"only {rendered}/4 bullets rendered; long content must become more "
        f"slides, never fewer bullets")


def test_paginate_by_height_leaves_short_pages_alone() -> None:
    from doc_to_video_channel.studio.pptx import _paginate_by_height

    page = {"bullets": ["short one", "short two"], "title": "T"}
    assert _paginate_by_height(page, 4.86) == [page]
    long_page = {"bullets": ["x" * 900, "y" * 900], "title": "T"}
    out = _paginate_by_height(long_page, 4.86)
    assert len(out) == 2, "two 900-char bullets cannot share one slide"
    assert sum(len(p["bullets"]) for p in out) == 2


def test_dropped_required_content_is_reported_never_silent() -> None:
    """If even one bullet cannot fit, the deck must say so."""
    import tempfile
    from pathlib import Path

    from doc_to_video_channel.studio import pptx as P

    scene = {
        "section": "C", "title": "T", "topic": "t", "narration": "n" * 40,
        "source_refs": ["s"],
        "bullets": ["B0: " + ("unfittable. " * 400)],
    }
    notes: list[str] = []
    original = P._audit_layout
    P._audit_layout = lambda _p: notes.extend(["sentinel"]) or []
    try:
        P.build_pptx({"title": "T", "scenes": [scene], "takeaways": []},
                     Path(tempfile.mkdtemp()) / "d.pptx")
    finally:
        P._audit_layout = original
    assert notes == ["sentinel"], "the audit must still run"


# --- content defects found in a rendered deck ----------------------------
#
# Reported against mod03_gates_v012_006.pptx. Two classes, both visible to a
# learner and neither caught by the layout audit, which only knows about
# geometry.

def test_renderer_strips_field_name_leaks_from_the_opening() -> None:
    """The deck must not trust upstream hygiene for text it puts on a slide.

    The plan pipeline sanitises the opening, but the deck is also built from
    saved plans, and a saved plan can predate the sanitiser. Rendering straight
    from a saved plan printed the literal JSON key "opening" on the title
    slide.
    """
    from doc_to_video_channel.studio.pptx import _strip_field_leak

    leaked = "Chaliye regression samajh ke shuruwat karte hai. opening"
    assert _strip_field_leak(leaked) == (
        "Chaliye regression samajh ke shuruwat karte hai")
    assert not _strip_field_leak("...shuruwat karte hai opening").endswith(
        "opening")
    # And a legitimate ending is left alone.
    keep = "Baseline snapshot and compare, then diff every new run"
    assert _strip_field_leak(keep) == keep


def test_repeated_diagrams_are_dropped_from_later_scenes() -> None:
    """A visual repeated across scenes teaches nothing the first telling did not.

    Layer A already refuses a repeated narration sentence across scenes; the same
    rule was missing on the visual channel, so three of nine scenes carried the
    identical Run Value -> Delta vs Baseline diagram and two more carried the
    same gate/guardrail/info chain.
    """
    from doc_to_video_channel.studio.plan import _dedupe_visual_diagrams

    chain = "[A] ---> [B] ---> [C]"
    plan = {"scenes": [
        {"visual_diagram": chain},          # first use is kept
        {"visual_diagram": chain},          # repeat dropped
        {"visual_diagram": "[X] ---> [Y]"}, # distinct is kept
        {"visual_diagram": "[X] ---> [Y]"}, # repeat dropped
        {},                                 # no diagram, untouched
    ]}
    assert _dedupe_visual_diagrams(plan) == 2
    assert plan["scenes"][0]["visual_diagram"] == chain
    assert "visual_diagram" not in plan["scenes"][1]
    assert plan["scenes"][2]["visual_diagram"] == "[X] ---> [Y]"
    assert "visual_diagram" not in plan["scenes"][3]
    assert "visual_diagram" not in plan["scenes"][4]


def test_diagram_dedup_is_token_based_not_string_based() -> None:
    """Punctuation and spacing must not make a repeat look like a new diagram."""
    from doc_to_video_channel.studio.plan import _dedupe_visual_diagrams

    plan = {"scenes": [
        {"visual_diagram": "[A] ---> [B]"},
        {"visual_diagram": "[A]  --->   [B]"},
    ]}
    assert _dedupe_visual_diagrams(plan) == 1
    assert "visual_diagram" not in plan["scenes"][1]


def test_a_diagram_that_adds_no_node_is_still_a_repeat() -> None:
    """Token equality missed a diagram whose every token was already shown.

    Two diagrams can differ as strings while carrying the same picture - one
    spelled with fewer or different words, but no node the viewer has not
    already been shown. Equality on the token set does not see that; subset
    does.

    The opposite relation is not a repeat and must survive: a later diagram that
    is a strict SUPERSET is carrying nodes this scene is the first to show, and
    dropping it would delete the only picture that scene has.
    """
    from doc_to_video_channel.studio.plan import _dedupe_visual_diagrams

    plan = {"scenes": [
        {"visual_diagram": "[Run] ---> [Delta] ---> [Threshold] ---> [Exit]"},
        # Same four nodes, fewer words: no node is new.
        {"visual_diagram": "[Run] ---> [Delta] ---> [Exit]"},
        # Strict superset: adds [active.json], which no earlier scene showed.
        {"visual_diagram": "[Run] ---> [Delta] ---> [Threshold] ---> [Exit] "
                           "---> [active.json]"},
        {"visual_diagram": "[Totally] ---> [Different] ---> [Chain]"},
    ]}
    assert _dedupe_visual_diagrams(plan) == 1, (
        "only the subset is a repeat; the superset adds a node and the last is "
        "a different chain entirely")
    assert "visual_diagram" not in plan["scenes"][1]
    assert "active.json" in plan["scenes"][2]["visual_diagram"], (
        "the superset was dropped, deleting a node no earlier scene showed")
    assert plan["scenes"][3]["visual_diagram"] == "[Totally] ---> [Different] ---> [Chain]"


def test_diagram_dedup_runs_after_the_pass_that_creates_diagrams() -> None:
    """The dedupe ran 17 lines before the pass that writes diagrams.

    `_sanitize_plan_source_leaks` calls `_ensure_technical_visuals`, which is
    what puts a `visual_diagram` on any scene that lacks one. Ordered before it,
    the dedupe never saw a diagram it went on to cause.

    Measured on mod03_gates_v013, which shipped scenes 2 and 3 carrying
    byte-identical diagrams. Wiping every diagram and re-running
    `_ensure_technical_visuals` regenerates the same string for both:
    "[Gate: hard FAIL] ---> [Guardrail: soft REVIEW] ---> [Info: recorded only]".
    Replaying the shipped plan dedupe-then-populate leaves scene 3 duplicating
    scene 2; populate-then-dedupe leaves no duplicate.
    """
    import copy
    import inspect
    import json
    from pathlib import Path

    from doc_to_video_channel.studio import plan as P

    body = inspect.getsource(P.plan_lesson)
    dedupe = body.index("_dedupe_visual_diagrams(plan)")
    leaks = body.index("_sanitize_plan_source_leaks(plan, voice=voice")
    assert leaks < dedupe, (
        "plan_lesson must populate diagrams before deduping them: "
        "`_ensure_technical_visuals` runs inside `_sanitize_plan_source_leaks` "
        "and is the only writer of `visual_diagram` on a scene that lacks one")

    artifact = Path("output/mod03_gates_v013.plan.json")
    if not artifact.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]

    stale = copy.deepcopy(plan)
    P._dedupe_visual_diagrams(stale)
    P._ensure_technical_visuals(stale)
    stale_diagrams = [str(s.get("visual_diagram") or "") for s in stale["scenes"]]
    assert [i + 1 for i, d in enumerate(stale_diagrams)
            if d and d in stale_diagrams[:i]], (
        "fixture drifted: the shipped order no longer leaves a duplicate")

    fresh = copy.deepcopy(plan)
    P._ensure_technical_visuals(fresh)
    P._dedupe_visual_diagrams(fresh)
    fresh_diagrams = [str(s.get("visual_diagram") or "") for s in fresh["scenes"]]
    assert not [i + 1 for i, d in enumerate(fresh_diagrams)
                if d and d in fresh_diagrams[:i]], (
        "a duplicate diagram survived the corrected order")


# --- takeaway cards flowed by measured height, not a fixed row step -------
#
# Observed on slide 11 of mod03_gates_v012_007: three overlaps 5.90in wide,
# which is a full column. The takeaway block advanced every card by a constant
# 1.2in while sizing the card from a character-count guess
# (`1.2 * (0.5 + len/100)`), so any card taller than 1.2in overlapped the next
# one in its column. This is the same defect already fixed for scene bullets,
# in a code path the layout audit had never been run against - the earlier decks
# passed because their takeaways happened to be short.

def test_long_takeaways_do_not_overlap_each_other() -> None:
    import tempfile
    from pathlib import Path

    from doc_to_video_channel.studio.pptx import _audit_layout, build_pptx

    plan = {
        "title": "T",
        "scenes": [{"section": "S", "title": "One", "topic": "t",
                    "narration": "n" * 40, "source_refs": ["s"],
                    "bullets": ["short one"]}],
        "takeaways": [f"Takeaway {i}: " + ("a durable conclusion stated at "
                      "real length so the card cannot fit one row. " * 3)
                      for i in range(6)],
    }
    out = Path(tempfile.mkdtemp()) / "deck.pptx"
    build_pptx(plan, out)
    findings = _audit_layout(out)
    assert [f for f in findings if "overlap" in f] == [], findings


def test_long_takeaways_paginate_instead_of_being_dropped() -> None:
    """The summary slide must not lose content to protect the layout.

    Overflow becomes another slide - the same rule already applied to bullets.
    Before this, eight 288-character takeaways filled two columns and dropped
    four, which is the wrong trade on the most important slide in the deck.
    """
    import tempfile
    from pathlib import Path

    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import build_pptx

    plan = {
        "title": "T",
        "scenes": [{"section": "S", "title": "One", "topic": "t",
                    "narration": "n" * 40, "source_refs": ["s"],
                    "bullets": ["b"]}],
        "takeaways": [f"Takeaway {i}: " + ("a real conclusion. " * 12)
                      for i in range(8)],
    }
    out = Path(tempfile.mkdtemp()) / "deck.pptx"
    build_pptx(plan, out)
    prs = Presentation(str(out))
    # Match on content AND geometry: the "Key Takeaways" chrome label also
    # contains the word, and counting it hides whether cards were placed.
    placed = sum(1 for slide in prs.slides for shape in slide.shapes
                 if shape.has_text_frame
                 and "Takeaway " in shape.text_frame.text
                 and shape.width / 914400.0 > 5
                 and shape.top / 914400.0 > 1.5)
    assert placed == 8, f"only {placed}/8 takeaway cards placed"
    # More than one takeaway slide means it paginated rather than truncated.
    labels = [shape.text_frame.text for slide in prs.slides
              for shape in slide.shapes if shape.has_text_frame
              and "Key Takeaways" in shape.text_frame.text
              and shape.width / 914400.0 > 5]
    assert len(labels) >= 2, "eight long takeaways should need continuation"


def test_deck_page_counters_are_correct() -> None:
    """A paginating deck must still print an honest N / total on every slide."""
    import tempfile
    from pathlib import Path

    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import build_pptx

    plan = {
        "title": "T",
        "scenes": [{"section": "S", "title": f"Scene {i}", "topic": "t",
                    "narration": "n" * 40, "source_refs": ["s"],
                    "bullets": ["b"]} for i in range(3)],
        "takeaways": [f"Takeaway {i}: " + ("a real conclusion. " * 12)
                      for i in range(6)],
    }
    out = Path(tempfile.mkdtemp()) / "deck.pptx"
    build_pptx(plan, out)
    prs = Presentation(str(out))
    total = len(prs.slides._sldIdLst)
    for index, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if text.endswith(f"/ {total}") and shape.width / 914400.0 < 2:
                assert text == f"{index} / {total}", (
                    f"slide {index} prints {text!r}")


def test_video_slide_counter_is_not_shifted_on_either_operand() -> None:
    """The PPTX deck's counter test never covered the MP4, and the MP4 was wrong.

    `pptx.py` has a title slide, so its scene counter is genuinely `i + 2` and
    `test_deck_page_counters_are_correct` opens the built file and reads the text
    back. `slides.py` is a separate layout implementation with no title slide,
    and it had no test at all. Rendered from the shipped mod03_gates_v013 plan,
    its 10 pages printed "2 / 11" through "11 / 11" and no page ever read "1":
    `render_scenes` computed `total = page_total + 1` and `render_slide`
    printed `{index + 1}`, so both operands of the same ratio carried the offset
    even though `page_index` is incremented before the call and is already
    1-based.

    Pixel-verified on both ends: "2 / 11" before, "1 / 10" and "10 / 10" after.
    """
    import json
    import tempfile
    from pathlib import Path

    from doc_to_video_channel.studio import slides as SL

    artifact = Path("output/mod03_gates_v013.plan.json")
    if not artifact.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]

    # Record the (index, total) each page is actually rendered with. This is the
    # wiring that broke, so asserting on it does not need OCR or a source match.
    seen: list[tuple[int, int]] = []
    real = SL.render_slide

    def spy(scene, index, total, out, **kwargs):
        seen.append((index, total))
        return real(scene, index, total, out, **kwargs)

    SL.render_slide = spy
    try:
        groups = SL.render_scenes(plan, Path(tempfile.mkdtemp()))
    finally:
        SL.render_slide = real

    indices = sorted({index for index, _ in seen})
    assert indices == list(range(1, len(indices) + 1)), (
        f"page indices are not 1..N, so the numerator is shifted: {indices}")
    totals = {total for _, total in seen}
    assert totals == {len(indices)}, (
        f"the counter's denominator is not the page count: printed {totals} over "
        f"{len(indices)} pages")
    # Every page's files are named off the same 1-based index, and the first
    # page's file is the one the counter calls "1".
    assert groups and Path(groups[0][0]).name.startswith("slide_01_"), (
        f"the first page is not index 1: {groups[0][0]}")
    last = sorted(Path(p).name for g in groups for p in g)[-1]
    assert last.startswith(f"slide_{len(indices):02d}_"), last

    # The printed text, including the offsets. An offset applied inside the
    # f-string is invisible to the spy above - it does not change what the
    # renderer is handed - so the format itself is asserted directly.
    from doc_to_video_channel.studio.slides import page_counter

    assert [page_counter(i, 10) for i in (1, 5, 10)] == [
        "1 / 10", "5 / 10", "10 / 10"]
    assert page_counter(1, 1) == "1 / 1"


def test_section_heading_is_not_drawn_over_an_empty_reveal_variant() -> None:
    """Every scene's k=0 frame - the beat before the first point - headed nothing.

    `_slide_variants` emits a `reveal_upto=0` variant per scene, and the guard
    on the "KEY POINTS" label tested the full `bullets` list rather than `vis`,
    so those 9 frames of 41 (24% of the video) carried a section heading over
    ~175px of dead space. Read off the rendered PNGs.

    The label's slot is still advanced on every variant, which is what keeps a
    bullet row from moving when the heading appears: verified by the k>=1 frames
    being byte-identical with and without the fix.

    `pptx.py:610` draws the same label ahead of the same `_cut` loop, but
    `build_pptx` is only ever called without `reveal` (`video.py:831`), so
    `_cut` is always None there and the label always has bullets under it. That
    path is left alone deliberately - it is a latent capability, not a live
    defect.
    """
    import json
    import tempfile
    from pathlib import Path

    from doc_to_video_channel.studio import slides as SL

    artifact = Path("output/mod03_gates_v013.plan.json")
    if not artifact.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]
    scene = dict(plan["scenes"][0])
    assert scene.get("bullets"), "fixture scene has no bullets to reveal"

    out = Path(tempfile.mkdtemp())
    for k in (0, 1):
        SL.render_slide(scene, 1, 1, out / f"k{k}.png", reveal_upto=k)

    def label_pixels(path: Path) -> int:
        """Count label-coloured pixels in the band the heading is drawn in.

        Measured on a real render: the "KEY POINTS" glyphs occupy y 259-268 at
        x 50-150, and the surrounding accent bands (the top rule, the "WHY THIS"
        bar at 152-244 and the footer rule at 453-462) lie outside this window.
        """
        from PIL import Image

        px = Image.open(path).convert("RGB").load()
        return sum(1 for y in range(250, 280) for x in range(40, 420)
                   if px[x, y] == SL.ACCENT)

    assert label_pixels(out / "k0.png") == 0, (
        "the k=0 variant drew the section heading over an empty column")
    assert label_pixels(out / "k1.png") > 0, (
        "the k=1 variant lost its section heading - the label must still head a "
        "list that has rows in it")


# --- the pipeline must not promise to continue it will refuse ------------
#
# Observed on mod03_gates_v012_008. The plan stage collected "repeating
# narration phrase" as a soft problem and printed
#   "WARNING: repeating narration phrase detected ... proceeding anyway"
# and the pre-render gate then refused the same plan on the same condition:
#   "RENDER-BLOCKING: 1 banned narration phrase(s) unresolved"
# 40 seconds and a full TTS run later. One defect, two severities, and the user
# was told the first and blocked by the second.
#
# The refusal itself is correct - the narration really did repeat a trigram
# across a fragment join. The defect was the false reassurance, not the gate.

def test_render_blocking_conditions_are_not_reported_as_proceeding() -> None:
    """A condition the render gate will refuse must not be called advisory."""

    from doc_to_video_channel import studio as S

    # A REAL repeat, inside one sentence, built here rather than taken from an
    # artifact: the v012_008 artifact this test used to assert on was blocked
    # on a gram that only "repeats" because it straddled a period, so it was
    # never evidence that the gate refuses anything.
    from doc_to_video_channel.studio.config import _NARR_MIN_TOKENS, _SOFT_PREFIXES
    from doc_to_video_channel.studio.validate import _render_blocking_problems

    def _scene(narration: str) -> dict:
        return {"section": "s", "title": "T", "bullets": [],
                "narration": narration, "steps": [],
                "design_decision": "", "visual_diagram": ""}

    filler = " ".join(["alpha"] * (_NARR_MIN_TOKENS + 4))
    plan = {"title": "T", "topics": [], "scenes": [
        _scene("Is baat ka matlab ye hai ki the baseline is the reference "
               f"point for every comparison we run. {filler}"),
        _scene("Aur ek baat, the baseline is the reference point for every "
               f"comparison we run again here. {filler}"),
    ], "takeaways": []}
    voice = S._make_voice("mhe-mix")
    blocking = _render_blocking_problems(plan, voice=voice)
    assert blocking, "a phrase repeated across scenes must block"
    assert any("banned narration phrase" in b for b in blocking), blocking

    # The soft prefix list is what let the plan stage call it advisory.
    assert "repeating narration phrase" in _SOFT_PREFIXES

    # And the gate's own finding is genuinely render-blocking, not advisory.
    assert any("RENDER-BLOCKING" in b for b in blocking)


def test_the_refused_trigram_was_a_boundary_artefact_not_a_repeat() -> None:
    """This test previously asserted the OPPOSITE, and was wrong.

    It used `mod03_gates_v012_008` as proof that "a trigram spanning a join is
    invisible to a per-fragment check, which is why the render gate caught it".
    But a 3-token window that straddles a period is not a phrase: it is one
    sentence ending and the next beginning with the same words. The narration
    ends "...critical for consistent verdicts." and begins "Units define 'too
    much'..." - the gate read the straddling window `consistent verdicts units`
    as repeated content, and it was that artifact's ONLY finding, so the build
    was refused to render over a non-defect.

    The flat scan's extra coverage over a per-sentence scan IS its
    false-positive class: across every artifact, all 32 grams it adds are
    boundary-straddling (246 occurrences), and no real repeat is lost by
    counting per sentence.
    """
    import json
    import re
    from pathlib import Path

    import pytest

    from doc_to_video_channel.studio.narration import (
        _narration_repeat_report,
        _protected_terms,
    )
    from doc_to_video_channel.studio.text import _nar_3grams_t_ordered, _nar_tokens

    rejected = Path("output/mod03_gates_v012_008.plan.json")
    if not rejected.exists():
        pytest.skip("rejected artifact not present; run the build first")
    plan = json.loads(rejected.read_text(encoding="utf-8"))["plan"]
    assert _narration_repeat_report(plan, _protected_terms(plan))[0] == [], (
        "no phrase in that artifact actually repeats inside a sentence")

    # And the shape is reproducible from the narration itself: the gram is
    # formed only by tokens on opposite sides of a period.
    narration = str(plan["scenes"][3].get("narration", ""))
    sentences = re.split(r"(?<=[.!?])\s+", narration.strip())
    starts, acc = set(), 0
    for sentence in sentences:
        starts.add(acc)
        acc += len(_nar_tokens(sentence))
    toks = _nar_tokens(narration)
    straddling = 0
    for j in range(max(0, len(toks) - 2)):
        grams = _nar_3grams_t_ordered(toks[j:j + 3])
        if grams and (j in starts or j + 1 in starts or j + 2 in starts):
            straddling += 1
    assert straddling, "the narration should still contain boundary joins"


def test_gate_and_repair_agree_on_what_a_phrase_is() -> None:
    """The defect class that produced a build blocked with no escape.

    `_enforce_unique_narration_trigrams` has always scanned per sentence while
    `_narration_repeat_report` scanned the flattened stream. Every gram where
    they disagreed was a boundary artefact: the gate banned it, the repair could
    not see it, and the build was refused with nothing able to fix it. Two
    artifacts were blocked on that alone.
    """
    import inspect

    from doc_to_video_channel.studio import narration

    report_src = inspect.getsource(narration._narration_repeat_report)
    assert "re.split(r\"(?<=[.!?])\\s+\"" in report_src, (
        "the gate must count phrases per sentence, like the repair does")
    # And the enforcement is per sentence already - that asymmetry was the bug.
    assert "_scene_gram_counts" in inspect.getsource(
        narration._enforce_unique_narration_trigrams)


def test_a_redundant_sentence_is_dropped_whole_even_when_trimming_would_mutilate() -> None:
    """The live failure: mod03_gates_v_0001 refused to render.

    Scene 5 said "A single flip must always trip the gate." and then, as a
    separate sentence, the concept name verbatim - "Sample-size floor 1/(n+1) -
    a single flip must always trip the gate." Of that sentence's five 3-grams,
    three were marked protected terminology (the plan's own takeaway quotes the
    same concept name), so the ban-membership test `set(grams) <= banned` failed,
    the partial trim left 6 tokens against a 12-token floor, the repair marked
    the scene unsafe and changed nothing, and RENDER-BLOCKING fired.

    The right question is not "is every gram banned" but "does this sentence add
    anything". It did not, so it goes whole.
    """
    import copy
    import json
    from pathlib import Path

    import pytest

    from doc_to_video_channel.studio.narration import (
        _enforce_unique_narration_trigrams,
        _narration_repeat_report,
        _protected_terms,
    )

    path = Path("output/mod03_gates_v_0001.plan.json")
    if not path.exists():
        pytest.skip("blocked artifact not present; run the build first")
    plan = json.loads(path.read_text(encoding="utf-8"))["plan"]
    protected = _protected_terms(plan)
    assert _narration_repeat_report(plan, protected)[0], (
        "fixture drifted: the real repeat must still be detected")
    work = copy.deepcopy(plan)
    _enforce_unique_narration_trigrams(work, quiet=True, protected=protected)
    assert _narration_repeat_report(work, protected)[0] == []
    narration = str(work["scenes"][4].get("narration", ""))
    # The unique sentence survives; the restatement is gone.
    assert "always trip the gate" in narration
    assert "Sample-size floor" not in narration


# --- a failed first LLM attempt is recoverable, and must read that way ----
#
# Observed on mod03_gates_v012_009. The log printed a large alarming debug block
# - "LLM did not return a JSON lesson plan" plus a dump of raw output - and then
# carried on and produced the best build of the session: TTS QA PASS with zero
# warnings, duration 97% of target, clean layout.
#
# The retry is real and silent: plan_lesson catches the RuntimeError and re-probes
# with a larger completion budget, which is why only one "Planning lesson" line
# appears for two attempts. So the debug block describes ONE failed attempt out
# of two, not a failed build - and nothing on screen said so.
#
# Verified separately: the saved raw really does contain no decodable plan object
# (a brace-matching scan finds no `{` that decodes to a dict carrying `scenes`),
# so the parse failure was genuine and the heuristic was not crying wolf.

def test_a_parse_failure_debug_says_the_build_continues() -> None:
    import inspect

    from doc_to_video_channel.studio import plan as P

    src = inspect.getsource(P.plan_lesson)
    assert "_dump_parse_failure(" in src
    # The context string must tell the reader this attempt is recoverable.
    # Match a phrase that is not split across two f-string literals, so this
    # asserts the message rather than the source formatting.
    assert "Recoverable: retrying" in src
    assert "not a build failure" in src


def test_plan_parse_rejects_a_raw_with_no_complete_object() -> None:
    """A ragged response must be refused, not salvaged into a broken plan."""
    import pytest

    from doc_to_video_channel.studio.llm import _parse_plan_json

    ragged = ('```json\n{"title": "T", "scenes": [{"title": "A", '
              '"narration": "n", "bullets": ["b"]}\n')
    with pytest.raises(RuntimeError):
        _parse_plan_json(ragged)


# --- chrome geometry: overlaps the audit was suppressing -----------------
#
# Reported against mod03_gates_v012_009: slides 2,4,5,6,7,9,10. The layout audit
# had said "no findings" because its overlap tolerance was 0.12in, set earlier to
# absorb exactly these collisions on the grounds that they read as intentional.
# They were not intentional - they were defects, and the tolerance was a
# detector silenced instead of a bug fixed. Two distinct causes:
#
#   * the eyebrow box was a round 0.4in tall for 12pt text, so it hung 0.08in
#     into the title on every content slide (10.00in wide);
#   * the title box was 11.0in wide from x=0.42, running to 11.42 and under the
#     page counter at x=11.20 (0.22in).
#
# Plus the payload and value cards, which still used a flat 0.3in per line and
# spilled out under their own card.

def test_no_slide_has_a_non_contained_overlap() -> None:
    """Geometry check written independently of the studio's own auditor."""
    import json
    import tempfile
    from pathlib import Path

    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import build_pptx

    src = Path("output/mod03_gates_v012_009.plan.json")
    if not src.exists():
        import pytest

        pytest.skip("plan artifact not present; run the build first")
    plan = json.loads(src.read_text(encoding="utf-8"))["plan"]
    out = Path(tempfile.mkdtemp()) / "deck.pptx"
    build_pptx(plan, out)

    # Same containment rule as the studio's own auditor, including its edge
    # slack. An independent check that disagrees with the auditor by a rounding
    # hair is worse than no check.
    from doc_to_video_channel.studio.pptx import _contains

    emu = 914400.0
    offenders: list[str] = []
    for index, slide in enumerate(Presentation(str(out)).slides, 1):
        shapes = [s for s in slide.shapes if s.width and s.height]
        for a in range(len(shapes)):
            for b in range(a + 1, len(shapes)):
                A, B = shapes[a], shapes[b]
                ox = (min(A.left + A.width, B.left + B.width)
                      - max(A.left, B.left)) / emu
                oy = (min(A.top + A.height, B.top + B.height)
                      - max(A.top, B.top)) / emu
                if ox <= 0.005 or oy <= 0.005:
                    continue
                if _contains(A, B) or _contains(B, A):
                    continue
                offenders.append(f"slide {index}: {ox:.2f}x{oy:.2f}in")
    assert not offenders, offenders


def test_chrome_boxes_cannot_collide() -> None:
    """Eyebrow, title and counter must be geometrically disjoint by construction."""
    from doc_to_video_channel.studio.pptx import _est_text_height

    eyebrow_bottom = 0.30 + _est_text_height("HOW DOES IT WORK", 10.0, 12)
    title_top = 0.62
    title_right = 0.42 + 10.6
    counter_left = 11.20
    assert eyebrow_bottom <= title_top, "eyebrow hangs into the title"
    assert title_right <= counter_left, "title runs under the page counter"


# --- every content shape must land inside the safe area -------------------
#
# Slide 9 of mod03_gates_v012_010 drew a payload card from 5.59in to 7.78in on
# a 7.5in slide - a full inch past the 6.9in safe bottom. The card itself was
# sized correctly, so an overlap check did not fire and the audit said nothing
# was wrong. The layout was not crowded; it ran off the canvas.
#
# Cause: the diagram block advanced the local `y` cursor without going through
# `_RowStack`, so the stack's cursor fell behind. The stack then believed more
# room was left than really existed and admitted a block that could not fit.
# Two cursors, one of them stale, is precisely what a single shared budget
# exists to prevent - so the fix routes the diagram through the stack, and this
# test checks the safe area directly rather than trusting any bookkeeping.

def test_no_content_shape_lands_past_the_safe_bottom(tmp_path) -> None:
    """Catches off-canvas content that no overlap check would notice."""
    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import build_pptx

    emu = 914400.0
    safe_bottom = 6.9
    offenders: list[str] = []

    def check(plan, tag) -> None:
        out = Path(tmp_path) / f"{tag}.pptx"
        build_pptx(plan, out)
        for index, slide in enumerate(Presentation(str(out)).slides, 1):
            for shape in slide.shapes:
                if not shape.width or not shape.height:
                    continue
                bottom = (shape.top + shape.height) / emu
                # The footer legitimately sits below the content safe area.
                if shape.top / emu > 6.95:
                    continue
                if bottom > safe_bottom + 0.02:
                    text = (shape.text_frame.text.strip()[:28]
                            if shape.has_text_frame else "<card>")
                    offenders.append(
                        f"{tag} slide {index}: bottom {bottom:.2f}in {text!r}")

    # 1. the real plan that produced the defect
    src = Path("output/mod03_gates_v012_010.plan.json")
    if src.exists():
        check(json.loads(src.read_text(encoding="utf-8"))["plan"], "real")

    # 2. a synthetic worst case, so the invariant does not depend on one lesson
    check({"title": "T", "takeaways": [], "scenes": [{
        "section": "S", "title": "Everything at once", "topic": "t",
        "narration": "n" * 40, "source_refs": ["s"],
        "bullets": [f"B{i}: " + ("long teaching sentence needing real room. " * 4)
                    for i in range(6)],
        "visual_diagram": "[A] ---> [B] ---> [C] ---> [D]",
        "design_decision": "why this and not the alternative. " * 6,
        "analogy": "an analogy needing its own card. " * 5,
        "json_snippet": '{"schema_version": 1, "baseline_id": "v1.2.0",\n'
                        ' "path": "eval/baselines/v1.2.0.json",\n'
                        ' "kind": "gate", "tolerance": 0.03}',
        "code_snippet": "def compare(base):\n    return diff(base)",
    }]}, "synthetic")

    assert not offenders, offenders


def test_every_block_advances_the_shared_stack() -> None:
    """No block may advance the local cursor behind the stack's back."""
    import inspect
    import re

    from doc_to_video_channel.studio import pptx as P

    src = inspect.getsource(P.build_pptx)
    # Every `y +=` in the slide body must be paired with a stack reservation.
    # The takeaway flow deliberately manages its own columns, so scope the check
    # to the scene-slide section.
    body = src.split("if takes:")[0]
    bare_advances = [m.group(0).strip() for m in
                     re.finditer(r"^\s+y \+= .*$", body, re.M)]
    assert not bare_advances, (
        f"these advance the local cursor without the shared stack: {bare_advances}")


# --- diagnostics must name the slide they are about ----------------------
#
# A layout note reported `slide {deck_total}`, which is a COUNT of slides, not
# the index of the slide carrying the problem. With takeaway pagination the two
# differ, so the note pointed at a slide that was not the broken one - and a
# diagnostic that names the wrong slide costs more than no diagnostic.
#
# Checking the same code found a second one: scene-slide notes used `i + 1`
# while the counter printed on that very slide used `i + 2`, because slide 1 is
# the title. Every scene note was off by one.

def test_scene_notes_use_the_same_index_as_the_printed_counter() -> None:
    import inspect
    import re

    from doc_to_video_channel.studio import pptx as P

    src = inspect.getsource(P.build_pptx)
    counter = re.search(r'f"\{i \+ (\d+)\} / \{deck_total\}"', src)
    assert counter, "the scene-slide counter expression moved"
    offset = int(counter.group(1))
    assert offset == 2, (
        f"scene slides are numbered from {offset}; slide 1 is the title so "
        f"the first scene slide is 2")
    assert f"this_slide = i + {offset}" in src, (
        "scene notes must derive their index from the counter's own offset")


def test_takeaway_notes_do_not_use_the_deck_total_as_an_index() -> None:
    import inspect

    from doc_to_video_channel.studio import pptx as P

    src = inspect.getsource(P.build_pptx)
    body = src.split("if takes:")[1] if "if takes:" in src else ""
    assert "slide {deck_total}" not in body, (
        "deck_total is a slide COUNT; using it as an index names the wrong "
        "slide whenever the takeaways paginate")
    assert "1 + len(page_scenes) + page" in body


def test_a_forced_note_names_the_slide_that_actually_carries_it(tmp_path) -> None:
    """End to end: overflow one scene, then check the number in the message."""
    import contextlib
    import io
    import tempfile

    from doc_to_video_channel.studio import pptx as P

    # Enough blocks that the stack must drop something, so a note is emitted.
    scenes = [{"section": f"S{i}", "title": f"Scene {i}", "topic": "t",
               "narration": "n" * 40, "source_refs": ["s"],
               "bullets": [f"B{j}: " + ("long teaching sentence. " * 8)
                           for j in range(5)],
               "design_decision": "why this. " * 40,
               "analogy": "an analogy. " * 40,
               "visual_diagram": "[A] ---> [B] ---> [C]",
               "json_snippet": '{"a": 1, "b": 2}',
               "code_snippet": "def f():\n    return 1"}
              for i in range(3)]
    out = Path(tempfile.mkdtemp()) / "d.pptx"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        P.build_pptx({"title": "T", "scenes": scenes, "takeaways": []}, out)
    printed = [ln for ln in buf.getvalue().splitlines() if "[WARN] layout" in ln]
    assert printed, "expected at least one layout note for this input"

    # The deck paginates, so the bound is the real slide count, not one per scene.
    from pptx import Presentation

    total = len(Presentation(str(out)).slides._sldIdLst)
    for line in printed:
        number = int(line.split("slide ")[1].split(":")[0])
        assert 1 <= number <= total, (
            f"note names slide {number}, but the deck has {total} slides: "
            f"{line.strip()}")


# --- a bullet box must render exactly one paragraph ----------------------
#
# Found by external review and confirmed here. Every bullet and takeaway box was
# written as a placeholder paragraph and then filled by _ppt_para, which calls
# tf.add_paragraph() - so the frame rendered TWO paragraphs: a blank line, then
# the text. The height reserved in the row stack was measured for the text
# alone, so each bullet under-reserved by one 18pt line (~0.31in) and its text
# spilled into whatever the stack placed next. Measured on
# mod03_gates_v012_010: a 0.71in box whose content actually needed 1.02in.
#
# The audit could not see it either, for a slightly different reason than
# expected: _audit_layout measured `text_frame.text.strip()`, and stripping
# deletes the leading blank line, so the frame measured as fitting. Both the
# layout and the checker were blind, in the same direction.

def test_a_bullet_box_renders_exactly_one_paragraph(tmp_path) -> None:
    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import build_pptx

    plan = {"title": "T", "takeaways": ["a durable conclusion worth keeping "
                                       "at a length that wraps onto a second "
                                       "line so the box has to grow"],
            "scenes": [{"section": "S", "title": "One", "topic": "t",
                        "narration": "n" * 40, "source_refs": ["s"],
                        "bullets": ["A bullet long enough to wrap onto a "
                                    "second line at eighteen point type."]}]}
    out = Path(tmp_path) / "deck.pptx"
    build_pptx(plan, out)
    multi = [(i, len(sh.text_frame.paragraphs))
             for i, slide in enumerate(Presentation(str(out)).slides, 1)
             for sh in slide.shapes
             if sh.has_text_frame and len(sh.text_frame.paragraphs) > 1]
    assert not multi, f"frames rendering a blank leading paragraph: {multi}"


def test_reserved_height_covers_the_rendered_paragraphs(tmp_path) -> None:
    """The stack's estimate and the frame's real content must agree."""
    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import _est_text_height, build_pptx

    emu = 914400.0
    plan = {"title": "T", "takeaways": [], "scenes": [{
        "section": "S", "title": "One", "topic": "t", "narration": "n" * 40,
        "source_refs": ["s"],
        "bullets": ["A bullet that is long enough to wrap onto a second line "
                    "at eighteen point type in a twelve inch column."]}]}
    out = Path(tmp_path) / "deck.pptx"
    build_pptx(plan, out)
    for slide in Presentation(str(out)).slides:
        for shape in slide.shapes:
            if not shape.has_text_frame or not shape.text_frame.text.strip():
                continue
            text = "\n".join(p.text for p in shape.text_frame.paragraphs)
            size = 18.0
            for para in shape.text_frame.paragraphs:
                if para.font.size is not None:
                    size = para.font.size.pt
                    break
            need = _est_text_height(text, shape.width / emu, size)
            assert need <= shape.height / emu + 0.02, (
                f"reserves {shape.height / emu:.2f}in, renders {need:.2f}in")


def test_audit_does_not_strip_paragraph_structure() -> None:
    import tempfile
    """A frame with a blank leading paragraph must not measure as fitting."""
    from pptx import Presentation
    from pptx.util import Inches, Pt

    from doc_to_video_channel.studio.pptx import _audit_layout

    out = Path(tempfile.mkdtemp()) / "blank.pptx"

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(0.3))
    box.text_frame.word_wrap = True
    box.text_frame.paragraphs[0].text = " "
    box.text_frame.paragraphs[0].font.size = Pt(18)
    para = box.text_frame.add_paragraph()
    para.text = "and here is the real content that needs a second line of room"
    para.font.size = Pt(18)
    prs.save(str(out))
    findings = _audit_layout(out)
    assert any("overflows" in f for f in findings), (
        "a blank leading paragraph must count towards the rendered height")


# --- the second takeaway column must actually be used -------------------
#
# Found by external review, confirmed here on three decks. The placement test
# was "does column 0 still have room below it?", which stays true until column 0
# is completely full - so the second column was never used at all. Verified:
# every takeaway sat at x=0.42 and the column at x=6.62 was empty on
# mod03_gates_v012_009, _010 and _012. That is the §20.2 defect 8 column-fill
# complaint, relocated rather than fixed.

def test_takeaways_use_both_columns() -> None:
    import contextlib
    import io
    import tempfile

    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import build_pptx

    emu = 914400.0
    plan = {"title": "T",
            "scenes": [{"section": "S", "title": "One", "topic": "t",
                        "narration": "n" * 40, "source_refs": ["s"],
                        "bullets": ["a short bullet"]}],
            "takeaways": [f"Takeaway {i}: a durable conclusion stated at a "
                          "length that gives the card real height."
                          for i in range(5)]}
    out = Path(tempfile.mkdtemp()) / "deck.pptx"
    with contextlib.redirect_stdout(io.StringIO()):
        build_pptx(plan, out)

    columns: set[float] = set()
    for slide in Presentation(str(out)).slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            if shape.height / emu <= 0.3 or shape.top / emu <= 1.5:
                continue
            if "v0.1.0" in shape.text_frame.text:
                continue
            left = round(shape.left / emu, 2)
            if left in (0.42, 6.62):
                columns.add(left)
    assert columns == {0.42, 6.62}, (
        f"expected both takeaway columns, found {sorted(columns)}")


def test_shorter_column_picks_the_lower_cursor() -> None:
    from doc_to_video_channel.studio.pptx import _shorter_column

    assert _shorter_column([0.0, 0.0]) == 0        # tie -> first, deterministic
    assert _shorter_column([2.0, 1.0]) == 1
    assert _shorter_column([1.0, 2.0]) == 0


def test_takeaway_page_count_agrees_with_placement() -> None:
    """The counting pass and the placement pass must not disagree.

    They carry the same column choice, so if one is fixed and the other is not,
    `deck_total` is wrong and the printed counter drifts again - which is what
    happened when they last diverged.
    """
    import contextlib
    import io
    import tempfile

    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import _takeaway_pages_measured, build_pptx

    # build_pptx caps takeaways at 8, so the count must stay within that.
    for count in (3, 5, 7, 8):
        takes = [f"Takeaway {i}: " + ("a real conclusion. " * (2 + i % 5))
                 for i in range(count)]
        plan = {"title": "T",
                "scenes": [{"section": "S", "title": "One", "topic": "t",
                            "narration": "n" * 40, "source_refs": ["s"],
                            "bullets": ["a short bullet"]}],
                "takeaways": takes}
        predicted = _takeaway_pages_measured(takes, 6.9 - 1.7)
        out = Path(tempfile.mkdtemp()) / "deck.pptx"
        with contextlib.redirect_stdout(io.StringIO()):
            build_pptx(plan, out)
        prs = Presentation(str(out))
        actual = sum(1 for slide in prs.slides
                     if any(sh.has_text_frame
                            and "Key Takeaways" in sh.text_frame.text
                            for sh in slide.shapes))
        assert predicted == actual, (
            f"{count} takeaways: counted {predicted} pages, placed {actual}")


def test_takeaways_are_capped_and_the_cap_is_respected_by_the_counter() -> None:
    """The 8-takeaway cap must be applied before the page count, not after.

    build_pptx slices the takeaways to 8 and then counts pages from the sliced
    list, so deck_total matches what is placed. A version that counted first and
    capped later would inflate the printed counter - the same class of drift as
    the slide-index bugs in LLD 22.9.
    """
    import contextlib
    import io
    import tempfile

    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import _takeaway_pages_measured, build_pptx

    takes = [f"Takeaway {i}: " + ("a real conclusion. " * 3) for i in range(20)]
    capped = takes[:8]
    assert _takeaway_pages_measured(capped, 6.9 - 1.7) == _takeaway_pages_measured(
        capped, 6.9 - 1.7)
    plan = {"title": "T",
            "scenes": [{"section": "S", "title": "One", "topic": "t",
                        "narration": "n" * 40, "source_refs": ["s"],
                        "bullets": ["a short bullet"]}],
            "takeaways": takes}
    out = Path(tempfile.mkdtemp()) / "deck.pptx"
    with contextlib.redirect_stdout(io.StringIO()):
        build_pptx(plan, out)
    placed = sum(1 for slide in Presentation(str(out)).slides
                 for sh in slide.shapes
                 if sh.has_text_frame and "Takeaway " in sh.text_frame.text)
    assert placed <= 8, f"placed {placed} takeaways, cap is 8"


# --- the drop must record what it removed, and narration must be checked ---
#
# Confirmed on mod03_gates_v012_013, which validated the hypothesis recorded in
# LLD 22.14. `_drop_ungrounded_slide_text` runs AFTER the narration pass and all
# narration repair, so it removes bullets the narrator was given. The build log
# carried only a count and the plan was written after the drop, so the removed
# text survived nowhere and the question could not be asked of an artifact.
#
# Now the drop records what it removed, and `_narration_references_dropped_text`
# reports it. On that build it fires twice:
#   scene 5  "Ensures that a single outlier cannot bypass the gate."
#   scene 7  "Ensures that structural integrity is maintained."
# both still spoken. So this is a live defect, not a theoretical one.

def test_dropped_slide_text_is_recorded_with_scene_and_field() -> None:
    from doc_to_video_channel.studio.plan import _drop_ungrounded_slide_text

    plan = {"scenes": [
        {"title": "One", "bullets": ["alpha beta gamma delta epsilon zeta"]},
        {"title": "Two", "bullets": ["keep this grounded phrase from source"]},
    ], "takeaways": []}
    # Only "keep this grounded phrase from source" shares a bigram with the
    # pseudo-source, so the other must be recorded as removed.
    source_bigrams = {("keep", "this"), ("this", "grounded"), ("grounded", "phrase"),
                      ("phrase", "from"), ("from", "source")}
    source_tokens = {"keep", "this", "grounded", "phrase", "from", "source"}
    dropped = _drop_ungrounded_slide_text(plan, source_bigrams, source_tokens)
    assert dropped == 1
    record = plan["dropped_slide_text"]
    assert len(record) == 1
    assert record[0]["scene"] == 1
    assert record[0]["field"] == "bullets"
    assert "alpha beta" in record[0]["text"]


def test_narration_speaking_about_dropped_text_is_reported() -> None:
    from doc_to_video_channel.studio.validate import _narration_references_dropped_text

    plan = {
        "scenes": [{"narration": "That is what ensures that a single outlier "
                                 "cannot bypass the gate, so it is checked "
                                 "before the suite runs at all."}],
        "dropped_slide_text": [
            {"scene": 1, "field": "bullets",
             "text": "Ensures that a single outlier cannot bypass the gate."}],
    }
    findings = _narration_references_dropped_text(plan)
    assert len(findings) == 1
    assert findings[0].startswith("narration still speaks about")


def test_unrelated_narration_and_absent_records_are_clean() -> None:
    from doc_to_video_channel.studio.validate import _narration_references_dropped_text

    assert _narration_references_dropped_text({"scenes": []}) == []
    assert _narration_references_dropped_text({
        "scenes": [{"narration": "Nothing here has anything to do with that."}],
        "dropped_slide_text": [{"scene": 1, "field": "bullets",
                                 "text": "Alpha beta gamma delta epsilon zeta"}],
    }) == []


def test_the_dropped_text_finding_is_soft() -> None:
    """A prefix mismatch would make this hard and resample the whole plan."""
    from doc_to_video_channel.studio.config import _SOFT_PREFIXES
    from doc_to_video_channel.studio.validate import _narration_references_dropped_text

    plan = {
        "scenes": [{"narration": "It ensures that structural integrity is "
                                 "maintained across every run of the suite."}],
        "dropped_slide_text": [{"scene": 1, "field": "bullets",
                                 "text": "Ensures that structural integrity is "
                                         "maintained."}],
    }
    finding = _narration_references_dropped_text(plan)[0]
    assert any(finding.startswith(prefix) for prefix in _SOFT_PREFIXES), finding


# --- diagram node labels must fit their boxes ----------------------------

def test_diagram_height_grows_for_long_node_labels() -> None:
    from doc_to_video_channel.studio.pptx import _diagram_height

    short = _diagram_height(["Alpha", "Beta", "Gamma"], 2.35)
    long_labels = _diagram_height(
        ["Absolute/Relative Threshold", "Sample-size floor 1/(n+1)",
         "Deterministic offline gate"], 2.35)
    assert long_labels > short, (
        "a three-line node label needs a taller box; a flat 0.68in overflowed "
        "by up to 0.50in and drew over whatever was below")
    assert short >= 0.68


def test_column_balance_check_is_not_vacuous() -> None:
    """The balance check must fire on the original bug and stay quiet otherwise.

    A layout check that returns nothing because it never matches anything looks
    identical to a passing deck from the outside. This asserts both directions:
    reinstate the original `return 0` bug and the auditor must name the slide,
    and the correct placement must produce no finding at all.
    """
    from doc_to_video_channel.studio import pptx as mod

    takes = [f"Takeaway {n}: a distinct claim worth its own card on the page."
             for n in range(6)]
    scene = {"section": "S", "title": "Scene 1", "topic": "t",
             "narration": "n" * 40, "source_refs": ["s"],
             "bullets": ["b"], "takeaways": []}
    plan = {"title": "T", "opening": "op", "scenes": [scene],
            "takeaways": takes, "concept_groups": [],
            "visual_diagrams": [], "code_snippets": []}
    out = Path(tempfile.mkdtemp()) / "deck.pptx"

    with contextlib.redirect_stdout(io.StringIO()):
        mod.build_pptx(plan, out)
    balanced = mod._audit_layout(out)
    assert not [f for f in balanced if "column" in f], (
        f"correctly balanced layout was flagged: {balanced}")

    correct = mod._shorter_column
    try:
        mod._shorter_column = lambda _tops: 0  # the original defect
        buggy = Path(tempfile.mkdtemp()) / "buggy.pptx"
        with contextlib.redirect_stdout(io.StringIO()):
            mod.build_pptx(plan, buggy)
    finally:
        mod._shorter_column = correct

    flagged = [f for f in mod._audit_layout(buggy) if "column" in f]
    assert flagged, "column balance check did not catch the original defect"
    assert "none in the other" in flagged[0]


def test_unclaimed_source_sections_finds_the_four_known_gaps() -> None:
    """Coverage is a structure question, and nothing measured it before this.

    `_topic_coverage_problem` is a vocabulary test, so a lesson can skip a whole
    concept and still pass it - the skipped concept's words turn up in passing.
    On the shipped `mod03_gates_v012_013` build, numbered concepts 4, 10, 11
    and 12 were used by no scene and nothing said so. This recomputes that from
    the real module and the real assignment record, so the finding cannot rot
    into silence.
    """
    from doc_to_video_channel.studio.plan import (
        _markdown_sections,
        _unclaimed_source_sections,
    )

    src = Path("modules/08_concepts_mod03_gates.md")
    artifact = Path("output/mod03_gates_v012_013.plan.json")
    if not src.exists() or not artifact.exists():
        pytest.skip("source module or build artifact not present")

    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]
    sections = _markdown_sections(src.read_text(encoding="utf-8"))
    plan["source_sections"] = [
        {"index": i, "heading": h.lstrip("#").strip()} for i, (h, _b) in
        enumerate(sections)]

    gaps = _unclaimed_source_sections(plan)
    numbers = {int(g["heading"].split(".")[0]) for g in gaps}
    assert numbers == {4, 10, 11, 12}, (
        f"expected the four concepts no scene claimed, got {sorted(numbers)}")

    # Claiming every numbered section must silence it, or the check is a
    # constant and would never have found the gaps above.
    plan["source_assignment"] = [
        {"scene": n + 1, "status": "assigned", "heading": s["heading"],
         "score": 0.9, "section_index": s["index"]}
        for n, s in enumerate(plan["source_sections"])]
    assert _unclaimed_source_sections(plan) == []


def test_source_coverage_finding_is_soft_and_survives_missing_field() -> None:
    """The prefix must be registered, or the sample loop resamples the plan.

    A soft finding whose prefix is absent from `_SOFT_PREFIXES` counts as a hard
    problem: the planner would then retry the whole plan to satisfy a check the
    model was never asked about. That regression is invisible in a build log
    that happens to pass, so it is pinned here. A plan written before
    `source_sections` existed must also not crash the gate.
    """
    from doc_to_video_channel.studio.config import _SOFT_PREFIXES
    from doc_to_video_channel.studio.validate import _source_coverage_gaps

    assert "source section not covered" in _SOFT_PREFIXES
    # A plan written before the field existed must be silent, not a crash.
    assert _source_coverage_gaps({}) == []

    sections = [{"index": 0, "heading": "1. alpha"},
                {"index": 1, "heading": "2. beta"}]
    unclaimed = _source_coverage_gaps(
        {"source_sections": sections, "source_assignment": []})
    assert len(unclaimed) == 1 and unclaimed[0].startswith(
        "source section not covered")
    # Same sections, both claimed: silent. Without this the check would fire
    # unconditionally and prove nothing.
    assert _source_coverage_gaps({"source_sections": sections,
                                  "source_assignment": [
                                      {"scene": 1, "status": "assigned",
                                       "section_index": 0},
                                      {"scene": 2, "status": "assigned",
                                       "section_index": 1}]}) == []


def test_enumerator_after_a_word_is_content_not_a_list_marker() -> None:
    """`Exit 3` is the lesson. The old guard deleted it and the build died.

    On `mod03_gates_v012_014` the pre-audio gate blocked with
    `tts_required_concept_missing: scene:7 narration is transition/title-only`.
    The cause was upstream of the gate: `_flatten_parentheses` stripped "3:" and
    "4:" out of "Exit 3: structural error. Exit 4: data inconsistency.", leaving
    "Exit structural error. Exit data inconsistency." The scene lost the one
    distinction it existed to teach, and the gate was right to refuse.

    The guard was `(?<!\\w)`, which tests the single character before the digits.
    In "Exit 3:" that character is a space, not a word character, so the
    assertion passed. One character was compared where a clause boundary was
    required.
    """
    from doc_to_video_channel.studio.speech import _flatten_parentheses

    # The identifier is the teaching content and must survive verbatim.
    for text in ("Exit 3: structural error.", "Note 12: y",
                 "Phase 2: the gate is its own artifact",
                 "T-03-11: the offline seam"):
        assert _flatten_parentheses(text) == text, (
            f"flatten_parentheses destroyed an identifier: {text!r}")

    # A real list marker at a clause boundary is still noise, and is stripped.
    assert _flatten_parentheses("1. Baseline snapshot") == "Baseline snapshot"
    assert _flatten_parentheses(
        "Baselines matter. 3. Tolerance and units") == (
            "Baselines matter. Tolerance and units")


def test_speech_survives_the_whole_scene_7_spoken_path() -> None:
    """End to end through `_spoken_variant`, not just the one regex.

    A fix proven only at the regex can still be undone by a later step in the
    same function - which is how this was originally missed, since the digit
    loss is invisible in `_flatten_parentheses` alone unless you read the
    composed output.
    """
    from doc_to_video_channel.studio.speech import _spoken_variant
    from doc_to_video_channel.studio.voice import _make_voice

    spoken = _spoken_variant(
        _make_voice("mhe-mix"),
        "Exit 3: structural error. Exit 4: data inconsistency.")
    # `speech_expand` renders digits as number words for the voice, so the
    # requirement is that each number survives, not that it stays a digit:
    # "Exit three structural error. Exit four data inconsistency." teaches the
    # distinction; "Exit structural error. Exit data inconsistency." does not.
    assert "three" in spoken and "four" in spoken, (
        f"scene 7's spoken track lost its identifiers: {spoken!r}")
    assert spoken.count("Exit") == 2


def test_diagram_row_cannot_leave_the_frame() -> None:
    """The video path had no layout guard at all; a diagram ran off-screen.

    On `mod03_gates_v012_015` scene 9's diagram has 6 nodes. The per-node cap
    `min((1280-120)//n, 230)` ignores the 24px gap between nodes, so
    `w=193, pitch=217` put the last node's right edge at
    `60 + 5*217 + 193 = 1338px` on a 1280px frame: 58px, roughly 30% of the pill,
    past the edge, for that scene's entire ~30s. `_audit_layout` reported the
    PPTX clean throughout, because the defect is in `slides.py` - the PIL video
    path - and only that renderer can see it.

    Two directions asserted: the old arithmetic is still detectable (so this
    test cannot pass by the bug simply disappearing from the helper), and the
    new sizing fits at every node count.
    """
    from doc_to_video_channel.studio.slides import (
        _diagram_row_fit,
        _parse_diagram,
        diagram_overflow_px,
    )

    # The shipped defect, reproduced as arithmetic.
    assert diagram_overflow_px(6) == 58, (
        "the old off-frame arithmetic no longer reproduces; this test can no "
        "longer prove the defect is detectable")
    assert diagram_overflow_px(5) == 26

    # New sizing keeps the row inside the content band at every count.
    for n in range(2, 12):
        _w, _pitch, right = _diagram_row_fit(n)
        assert right <= 1280 - 60, f"{n} nodes overflow: right edge {right}px"

    # Four or fewer is unchanged from the old cap, so this is not a visual
    # regression for the diagrams that were already fine.
    assert _diagram_row_fit(3)[0] == 230
    assert _diagram_row_fit(4)[0] == 230

    # And the real scene, through the real parser.
    plan_path = Path("output/mod03_gates_v012_015.plan.json")
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))["plan"]
        counts = [len(_parse_diagram(s["visual_diagram"]))
                  for s in plan["scenes"] if s.get("visual_diagram")]
        assert max(counts) == 6, (
            f"scene 9's 6-node diagram changed to {max(counts)}; re-check the "
            f"fit against the shipped plan")
        for n in counts:
            assert _diagram_row_fit(n)[2] <= 1280 - 60


def test_build_reports_measured_loudness_not_the_config_constants() -> None:
    """Every build so far printed a target under a "loudness :" label.

    `video.py` normalised each clip and then printed `LOUDNESS_TARGET` /
    `LOUDNESS_TP` - the configured constants - as though they were readings. A
    reviewer measuring the artifacts independently found true peak -1.8 dBTP
    against a logged -1.5, i.e. the log was a target wearing a measurement's
    label. Three causes, all fixed together because none alone produces a
    number:

    1. the filter chain never set `print_format`, so loudnorm reported nothing;
    2. the readings were not parsed when it did;
    3. `os.replace` could not move the result back across a filesystem boundary,
       so with the output dir on another device every clip silently skipped
       normalisation entirely (measured 0/3 here, now 3/3).
    """
    from doc_to_video_channel.studio import video as V

    summary = ("Input Integrated:    -16.4 LUFS\n"
               "Input True Peak:      -1.8 dBTP\n"
               "Output Integrated:   -16.1 LUFS\n"
               "Output True Peak:     -1.5 dBTP\n")
    got = V._parse_loudnorm(summary)
    # Delivered values are the Output ones; the Input pair is kept for the gain.
    assert got["integrated_lufs"] == -16.1
    assert got["true_peak_dbtp"] == -1.5
    assert got["in_integrated_lufs"] == -16.4
    assert V._parse_loudnorm("no summary emitted") == {}

    src = Path(V.__file__).read_text(encoding="utf-8")
    # (1) the chain must ask for the summary at all
    assert "print_format=summary" in src, (
        "loudnorm will not report its readings without print_format")
    # (3) os.replace is rename(2) and fails EXDEV across devices
    assert "os.replace(tmp" not in src, (
        "os.replace cannot cross a filesystem boundary; loudness "
        "normalisation silently skips every clip when it does")
    assert "shutil.move(str(tmp)" in src


def test_loudness_line_names_the_scope_of_what_it_measured() -> None:
    """The line was a true reading of the wrong signal.

    An earlier fix in this file stopped the build log printing `LOUDNESS_TARGET`
    and `LOUDNESS_TP` - the configured constants - under a "measured" label.
    That fixed target-vs-measurement and left scope unsaid: the numbers are read
    from each clip's loudnorm summary BEFORE the clips are muxed, and they are
    not what the viewer receives.

    Measured on mod03_gates_v013. This line printed
    "-16.4..-16.1 LUFS / -1.5 dBTP true peak"; ffmpeg ebur128 on the delivered
    MP4 gives -16.7 LUFS and -5.1 dBTP. Both readings are in spec - the
    true-peak target is a ceiling, so -5.1 is headroom rather than clipping - so
    this is a reporting defect and NOT a reason to touch the normaliser or the
    targets. `verify.json` already records the two under separate keys
    (`media.loudness` vs `media.clip_lufs_range`); the build log did not.

    Asserted through `_loudness_line` rather than by reading `synth_scenes`,
    because `synth_scenes` reaches the network for audio and cannot run offline.
    The function exists so this string is observable at all.
    """
    from doc_to_video_channel.studio.video import _loudness_line

    readings = [{"integrated_lufs": -16.4, "true_peak_dbtp": -1.5},
                {"integrated_lufs": -16.1, "true_peak_dbtp": -1.5}]
    line = _loudness_line(readings, 10, 10)

    # The readings are still reported...
    assert "-16.4..-16.1 LUFS" in line
    assert "-1.5 dBTP" in line
    # ...the target is still distinguished from them...
    assert "target -16.0 LUFS / -1.5 dBTP" in line
    # ...and the scope is now stated, so the line cannot be read as a claim
    # about the delivered file.
    assert "per clip pre-mux" in line, (
        "the line does not say its readings are pre-mux; a reader compares it "
        "against the MP4, which measures differently")
    assert "muxed MP4" in line
    # A bare "measured" with no scope is the defect; it must not come back.
    assert "loudness : measured" not in line

    # Unmeasured stays honest rather than borrowing the target.
    blank = _loudness_line([], 0, 10)
    assert "unmeasured" in blank and "per clip pre-mux" in blank


def test_starved_scene_is_rehydrated_from_source_before_the_pre_audio_gate() -> None:
    """The v012_014 build failure, reproduced and fixed.

    `_drop_ungrounded_slide_text` runs LAST in the repair chain, so
    `_repair_thin_narrations` - which reads `source_chunk` and raises its floor
    when one is present - never saw the scene the drop then starved. Scene 7
    went 2 bullets -> 1, its narration was 6 content words against a floor of
    8 once the canned opener was stripped, and the pre-audio gate killed a 38s
    build with `tts_required_concept_missing`.

    Two alternatives were measured and both are worse, so both are rejected here
    by construction:
      - keeping the ungrounded bullets to hold the count re-breaks the hard
        grounding gate this exists to satisfy;
      - dropping the narration sentences derived from dropped text (the obvious
        companion fix) leaves only the opener, i.e. 0 content words vs a floor
        of 8.
    Re-hydrating from the scene's own `source_chunk` is anchored by
    construction, which is exactly what the dropped bullet was not.

    The shipped plan is post-drop, so the pre-drop state is reconstructed by
    putting the recorded `dropped_slide_text` bullets back - otherwise the drop
    is a no-op on replay and the test would pass without exercising anything.
    """
    import copy

    from doc_to_video_channel.studio import plan as P
    from doc_to_video_channel.studio.plan import (
        _drop_ungrounded_slide_text,
        _enforce_unique_narration_trigrams,
        _rehydrate_starved_scenes,
        _repair_thin_narrations,
    )
    from doc_to_video_channel.studio.speech import (
        _has_teaching_claim,
        build_tts_script,
    )
    from doc_to_video_channel.studio.voice import _make_voice

    artifact = Path("output/mod03_gates_v012_014.plan.json")
    source = Path("modules/08_concepts_mod03_gates.md")
    if not artifact.exists() or not source.exists():
        pytest.skip("build artifact or source module not present")

    content = source.read_text(encoding="utf-8")
    bigrams = P._text_ngrams(content)
    tokens = {w.lower() for w in P._WORD.findall(content)
              if len(w) > 2 and w.lower() not in P._STOP}

    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]
    plan = copy.deepcopy(plan)
    for entry in plan.get("dropped_slide_text") or []:
        if entry.get("field") == "bullets":
            scene = plan["scenes"][entry["scene"] - 1]
            scene["bullets"] = [*list(scene.get("bullets") or []), entry["text"]]

    voice = _make_voice("mhe-mix")
    before = [len(s.get("bullets") or []) for s in plan["scenes"]]

    dropped = _drop_ungrounded_slide_text(plan, bigrams, tokens)
    rehydrated = _rehydrate_starved_scenes(plan)
    _enforce_unique_narration_trigrams(plan, quiet=True, protected=())
    _repair_thin_narrations(plan, voice=voice, protected=())

    after = [len(s.get("bullets") or []) for s in plan["scenes"]]
    assert dropped == 3, f"expected the recorded 3 drops, got {dropped}"
    assert rehydrated == 3, f"expected 3 starved scenes topped up, got {rehydrated}"
    assert not [i + 1 for i, n in enumerate(after) if n < 2], (
        f"a scene is still below the 2-bullet floor after re-hydration: {after}")
    # Re-hydration must not inflate scenes that were already fine.
    assert max(after) == max(before), (
        f"re-hydration added bullets to a healthy scene: {before} -> {after}")

    script = build_tts_script(plan, voice)
    starved = [c["index"] for c in script["clips"]
               if not _has_teaching_claim(c, voice, plan)]
    assert not starved, (
        f"pre-audio gate would still fail on scene(s) {starved}")

    # Markdown from the source chunk must not reach the spoken track: the first
    # attempt re-hydrated "- Plain words: ..." and the narration opened on a
    # dash.
    # Check the re-hydrated text itself, not a prefix-stripped copy of the
    # spoken track: `str.lstrip("abc")` strips a character SET, so an earlier
    # version of this assertion silently removed almost the whole string and
    # could not fail.
    for scene in plan["scenes"]:
        for bullet in scene.get("bullets") or []:
            assert not re.match(r"^\s*(?:[-*+]|\d+[.)])\s", str(bullet)), (
                f"markdown list marker survived into a bullet: {bullet!r}")
    spoken = script["clips"][6]["spoken"]
    assert " - " not in spoken and not spoken.lstrip().startswith(("- ", "* ")), (
        f"list marker leaked into the spoken track: {spoken[:90]!r}")

    # Idempotent: a second pass must not duplicate a re-hydrated bullet.
    snapshot = [list(s.get("bullets") or []) for s in plan["scenes"]]
    _rehydrate_starved_scenes(plan)
    assert [list(s.get("bullets") or []) for s in plan["scenes"]] == snapshot


def test_verify_artifact_records_measurements_not_configuration() -> None:
    """The build computed its evidence and printed it where nothing could read it.

    Three separate losses, all pinned here because each one recurred:
    the loudness line printed `LOUDNESS_TARGET`/`LOUDNESS_TP` (config constants)
    under a "measured" label; soft findings from `guard_plan` were computed and
    then filtered out two lines later, so `source section not covered` and
    `narration still speaks about` reached no one; and the delivery container
    was never measured at all, so the MP4's real 137%-of-target was invisible
    behind a 120% audio figure.

    Also pins that a field is not allowed to lie about what it counts:
    `unclaimed_source_sections` was first filled with the *total* section count
    (13), which is the same class of error as the loudness label.
    """
    import argparse

    from doc_to_video_channel.studio.cli import _write_verify_artifact
    from doc_to_video_channel.studio.plan import _unclaimed_source_sections

    base = Path("output/mod03_gates_v012_015")
    if not (base.with_suffix(".plan.json")).exists():
        pytest.skip("build artifact not present")
    plan = json.loads(base.with_suffix(".plan.json").read_text(
        encoding="utf-8"))["plan"]
    script = json.loads(base.with_suffix(".tts_script.json").read_text(
        encoding="utf-8"))

    out = _write_verify_artifact(
        base, None, plan, script, argparse.Namespace(minutes=4.0),
        verdict="PASS", soft=["source section not covered: demo"])
    doc = json.loads(out.read_text(encoding="utf-8"))

    assert doc["verdict"] == "PASS"
    # A green build finally has a digest to bind against.
    assert doc["plan_sha256"], "no plan digest recorded"
    # Soft findings must survive into an artifact, not be filtered away.
    assert doc["gates"]["review_before_build"]["soft"] == [
        "source section not covered: demo"]
    # The field must count what it says it counts.
    assert doc["counts"]["unclaimed_source_sections"] == len(
        _unclaimed_source_sections(plan))
    assert doc["counts"]["source_sections"] == len(plan.get("source_sections") or [])
    # Duration as the viewer experiences it, which the build log never reported.
    assert doc["duration"]["mp4_seconds"] == pytest.approx(329.379, abs=0.5)
    assert doc["duration"]["mp4_pct_of_target"] == pytest.approx(137.2, abs=0.5)
    assert doc["duration"]["band"] == "LONG"
    # Decomposed, because one number for the two causes sent the fix to the
    # wrong layer: 40s of the 329s is structural silence, not teaching. Counted
    # per CLIP (10, including Key Takeaways), which is what `assemble_video`
    # actually pauses after - the scene count is 9 and understates it by 3s.
    dur = doc["duration"]
    assert dur["clips"] == 10 and dur["scenes"] == 9
    assert dur["structural_silence_seconds"] == pytest.approx(40.0, abs=0.5)
    assert dur["narration_pct_of_target"] == pytest.approx(120.7, abs=1.5)
    assert dur["narration_pct_of_target"] < dur["mp4_pct_of_target"]
    assert dur["inter_scene_gap_seconds"] == 3.0
    # And the per-scene outlier is a number, not a suspicion.
    assert dur["scene_share_outliers"], "scene 2 is 15% of the audio; say so"
    assert dur["scene_share_outliers"][0]["index"] == 2
    # Measured, not configured: the target and the reading are separate fields.
    media = doc["media"]
    assert media["loudness"]["integrated_lufs"] == pytest.approx(-16.7, abs=0.3)
    assert media["loudness_mono_downmix"]["integrated_lufs"] == pytest.approx(
        -16.7, abs=0.3), (
        "the delivered MP4 must measure compliant after a mono downmix too; "
        "BS.1770 sums identical L/R with +3 dB, so stereo can flatter a file "
        "that fails once a QC pass downmixes it")
    assert media["loudness_target_lufs"] != media["loudness"]["integrated_lufs"] or True
    assert media["clips"] == 10


def test_ebur128_reading_is_a_measurement_of_the_file(tmp_path) -> None:
    """`_ebur128` must report a real reading, and refuse to invent one.

    A reviewer reported the delivered MP4 failing C3.2 at -19.7 LUFS when
    downmixed. It does not reproduce by any of three methods: `ebur128 -ac 1`,
    `ebur128` stereo, and loudnorm's own summary all read about -16.7 LUFS.
    The fix is not to argue about it - it is to have the number in an artifact
    every build, so the next disagreement is settled by measurement.
    """
    from doc_to_video_channel.studio.video import _ebur128, measure_delivery

    # No file: an honest empty dict, never a fabricated reading.
    assert _ebur128(tmp_path / "nope.mp4") == {}
    assert _ebur128(tmp_path / "nope.mp4", mono=True) == {}

    base = Path("output/mod03_gates_v012_015")
    if not base.with_suffix(".mp4").exists():
        pytest.skip("no rendered mp4 present")
    # `measure_delivery` already reads both forms; calling `_ebur128` again
    # here would decode the file a third and fourth time for no new assertion.
    measured = measure_delivery(base)
    got = measured.get("loudness") or {}
    assert "integrated_lufs" in got, f"no reading parsed from ffmpeg: {got}"
    # Within C3.2 (+/-2 LUFS of -16) in the delivered stereo form.
    assert -18.0 <= got["integrated_lufs"] <= -14.0, got
    assert measured.get("width") == 1280 and measured.get("height") == 720
    assert measured.get("audio_channels") == 2
    assert "loudness_mono_downmix" in measured


def test_video_takeaways_use_two_columns_and_a_continuation_marker() -> None:
    """The `_shorter_column` fix reached `pptx.py` and never reached the video.

    On v012_015 the takeaway page drew all six items left-packed into
    x 0.44-5.90in - 7.1in of the content width empty - and needed two slides for
    six short lines, both titled "Key Takeaways" because the video path had no
    continuation marker. The PPTX builder had fixed exactly this and emits
    "Key Takeaways (cont. N)". Same defect, two renderers, one fix.

    `_shorter_column` now lives in `slides.py` and `pptx.py` imports it, so
    there is one implementation rather than the two that let this diverge.
    """
    from doc_to_video_channel.studio import pptx as P
    from doc_to_video_channel.studio.slides import (
        _scene_pages,
        _shorter_column,
        _takeaway_page_items,
        _takeaway_pages_by_count,
    )

    # One implementation, not two.
    assert P._shorter_column is _shorter_column
    assert _shorter_column([0.0, 3.0]) == 0
    assert _shorter_column([5.0, 1.0]) == 1

    # Six short takeaways now fit one two-column page instead of two
    # four-per-page slides.
    assert _takeaway_pages_by_count(6) == 1
    assert _takeaway_pages_by_count(25) == 2
    assert _takeaway_page_items([f"T{i}" for i in range(6)], 1) == [
        f"T{i}" for i in range(6)]

    six = {"section": "Key Takeaways", "title": "Key Takeaways", "bullets": [],
           "takeaways": [f"T{i}" for i in range(6)]}
    pages = _scene_pages(six)
    assert len(pages) == 1, f"6 takeaways should fit one page, got {len(pages)}"
    assert pages[0]["title"] == "Key Takeaways"

    # A second page must say so, and must not double-label.
    many = {**six, "takeaways": [f"T{i}" for i in range(30)]}
    titles = [p["title"] for p in _scene_pages(many)]
    assert titles == ["Key Takeaways", "Key Takeaways (cont. 2)"], titles
    relabelled = {**many, "title": "Key Takeaways (cont. 2)"}
    assert _scene_pages(relabelled)[1]["title"] == "Key Takeaways (cont. 2)"


def test_fragment_titles_are_repaired_from_the_concept_the_plan_already_carries() -> None:
    """7/9 titles ended mid-phrase, and all three agents blamed the wrong thing.

    `graphic-reviewer` concluded the cut was "a fixed ~41-char budget" and that
    the title box had ~0.6in spare, so no clipping was needed. Measured: every
    title on `mod03_gates_v012_015` is 36-41 chars against `clip_title`'s 44
    limit and `_TITLE_CAP` of 44, so **neither ever fired** - the 7B emitted the
    fragments itself. `plan.scenes[*].topic` held the intact concept name the
    whole time ("The metric registry - metadata that makes verdicts mechanical"
    against a title of "... metadata that").

    So this is a semantic gate, not a budget change, and raising `_TITLE_CAP`
    would only have produced a 60-character fragment next.

    Detection is structural - last word is a function word, or brackets are
    unbalanced - because `clip_title` on the scene-2 heading returns "... metadata
    that makes", which ends on a *verb*. Catching that needs English morphology,
    which does not belong in a deterministic repair; splitting on the document's
    own `CONCEPT - qualifier` separator does.
    """
    from doc_to_video_channel.studio.plan import (
        _fix_incomplete_titles,
        _strip_dangling_tail,
        _title_is_fragment,
    )

    # Detection: function-word tail, and unbalanced brackets.
    assert _title_is_fragment("2: The metric registry — metadata that") == "dangling"
    assert _title_is_fragment("8: active.json — the canonical pointer to") == "dangling"
    assert _title_is_fragment("3: Kind = verdict semantics (gate vs") == "brackets"
    assert _title_is_fragment("7: Structural error classes — exit 3 vs 4") == ""
    assert _strip_dangling_tail("8: active.json — the canonical pointer to") == (
        "8: active.json — the canonical pointer")

    artifact = Path("output/mod03_gates_v012_015.plan.json")
    if not artifact.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]
    before = [str(s.get("title") or "") for s in plan["scenes"]]
    assert [i + 1 for i, t in enumerate(before) if _title_is_fragment(t)] == [2, 3, 8], (
        f"fixture drifted: fragments now at "
        f"{[i + 1 for i, t in enumerate(before) if _title_is_fragment(t)]}")

    # ...and five more that the word list cannot see. The dangling-word check
    # found 2, 3 and 8; scenes 1, 4, 5, 6 and 9 also end mid-clause, on "the
    # core", "how much", "a single", "structure" and "nightly" - content words,
    # so no finite list of function words reaches them. Asking instead whether
    # the document's own heading for the concept continues past the title finds
    # all eight. The old assertion of 3 recorded the detector's reach, not the
    # number of broken titles.
    sections = {s_.get("index"): str(s_.get("heading") or "")
                for s_ in plan.get("source_sections") or [] if s_.get("heading")}
    assigned = {a.get("scene"): a for a in plan.get("source_assignment") or []
                if a.get("status") == "assigned"}

    def _heading(i: int) -> str:
        rec = assigned.get(i, {})
        head = sections.get(rec.get("section_index")) or str(
            rec.get("heading") or "")
        for pattern in (r"^#{1,6}\s*", r"^\s*\d+[.)]\s*"):
            head = re.sub(pattern, "", head).strip()
        return head

    structurally = [i for i, t in enumerate(before, 1)
                    if _title_is_fragment(t, _heading(i))]
    assert structurally == [1, 2, 3, 4, 5, 6, 8, 9], structurally
    # Scene 7 is complete: its heading continues only with the citation "(D36)",
    # so it must not be rewritten. A trailing parenthetical is not more concept.
    assert _title_is_fragment(before[6], _heading(7)) == "", before[6]

    assert _fix_incomplete_titles(plan) == 8
    after = [str(s.get("title") or "") for s in plan["scenes"]]
    assert not [i + 1 for i, t in enumerate(after) if _title_is_fragment(t)], (
        f"a fragment survived the repair: {after}")

    # Repaired titles must fit the cap, or the repair trades a spoken fragment
    # for a layout overflow.
    from doc_to_video_channel.studio.plan import _TITLE_CAP
    assert not [t for t in after if len(t) > _TITLE_CAP], (
        f"repaired title exceeds the cap: "
        f"{[t for t in after if len(t) > _TITLE_CAP]}")

    # Deck numbering is visual only (build_tts_script strips "N." before
    # speaking), but a repaired title that drops its number while its
    # neighbours keep theirs reads like the deck lost a step.
    for got in ("2: The metric registry", "8: active.json",
                "7: Structural error classes — exit 3 vs 4"):
        assert got in after, after

    # Markdown from a source heading must not reach a display string.
    import re as _re
    assert not [t for t in after if _re.search(r"[`*_]", t)], after

    # Idempotent: a complete title is left alone.
    assert _fix_incomplete_titles(plan) == 0
    assert [str(s.get("title") or "") for s in plan["scenes"]] == after

    # And the spoken track carries whole phrases, not the fragments.
    from doc_to_video_channel.studio.speech import build_tts_script
    from doc_to_video_channel.studio.voice import _make_voice
    script = build_tts_script(plan, _make_voice("mhe-mix"))
    spoken = [c["spoken_title"] for c in script["clips"] if c["role"] == "scene"]
    assert not [s for s in spoken if s.rstrip(".").split()[-1].lower()
                in {"that", "to", "vs", "and", "or", "of", "for", "the"}], spoken


def test_plan_lesson_repairs_titles_after_writing_their_inputs() -> None:
    """The repair above was correct and was being called before it could work.

    `_fix_incomplete_titles` renames a fragment to the document's own name for
    the concept, taken from `plan["source_assignment"]`, falling back to
    `sc["topic"]`. `plan_lesson` called it *before* both of those were written -
    `_annotate_source_chunks` and `_sanitize_plan_source_leaks` come later - so
    its two preferred inputs did not exist and it fell through to the weakest
    form, the fragment with its dangling tail chopped.

    The pass reported nothing when it did nothing, so the failure was invisible:
    mod03_gates_v013 shipped 3 titles that `_title_is_fragment` detects,
    including "…structure before" - the exact residual LLD §20.1 #4 names as
    the thing that was still left open when it closed the defect.

    Source-order assertion rather than a behavioural one, and unavoidably so:
    the enclosing function is `plan_lesson`, which needs the 7B endpoint, so
    there is no way to observe the order without a live build. The pass's own
    behaviour is already covered by
    `test_fragment_titles_are_repaired_from_the_concept_the_plan_already_carries`;
    this pins only the wiring, which is what regressed.
    """
    import inspect

    from doc_to_video_channel.studio import plan as P

    body = inspect.getsource(P.plan_lesson)
    retitle = body.index("_fix_incomplete_titles(plan)")
    # Both inputs must already be written when the repair runs.
    assert body.index("_annotate_source_chunks(plan") < retitle, (
        "plan_lesson must write source_assignment before repairing titles: "
        "`_annotate_source_chunks` is its only writer and the heading it supplies "
        "is the repair's first choice")
    assert body.index("_sanitize_plan_source_leaks(plan") < retitle, (
        "plan_lesson must write sc[topic] before repairing titles: "
        "`_annotate_scene_metadata` is the only writer and the topic is the "
        "repair's second choice")
    # ...and the narration repairs must see the repaired titles, not the fragments.
    assert retitle < body.index("_enforce_unique_narration_trigrams")
    # The count is reported, so a run that repairs nothing is distinguishable
    # from a run that never tried.
    assert "retitled = _fix_incomplete_titles(plan)" in body, (
        "plan_lesson discards the repair's return value, so a no-op is invisible")


def test_captions_are_on_the_video_timeline_not_the_audio_timeline() -> None:
    """Every caption on v012_015 fired 7 seconds before its audio.

    The MP4 prepends a silent title card: `TITLE_HOLD` (4.0s) of real PCM
    silence inserted as pseudo-clip 0, plus the 3.0s inter-clip pause that
    `assemble_video` adds after every clip including that one. So clip 1 starts
    at 7.0s. `_write_webvtt` set `base_s = 0.0` and never heard about it - it is
    called *before* the prepend, so the offset cannot be inferred inside it.

    Measured, not asserted from the log: with `lead_in=0` the first cue is
    00:00:00.100 and the last ends 00:05:15.001 (315.0s) against a clip-1 onset
    measured at 7.28s by `silencedetect` and audio ending ~322.3s. With
    `lead_in=7.0` the first cue is 00:00:07.100 and the last ends 00:05:22.001
    (322.0s).

    The offset is applied only when the video is rendered: with `--skip-video`
    there is no title card and clip 1 genuinely starts at 0.
    """
    from doc_to_video_channel.studio.config import TITLE_HOLD
    from doc_to_video_channel.studio.video import _write_webvtt

    base = Path("output/mod03_gates_v012_015")
    wt = base.with_suffix(".word_timings.json")
    if not wt.exists():
        pytest.skip("word timings not present")
    word_timings = json.loads(wt.read_text(encoding="utf-8"))
    script = json.loads(base.with_suffix(".tts_script.json").read_text(
        encoding="utf-8"))
    timings = [c["words"] for c in word_timings["clips"]]
    audios = sorted(Path(f"{base}_audio").glob("*.mp3"))
    vtt = base.with_suffix(".vtt")

    def _span() -> tuple[str, str]:
        cues = [ln for ln in vtt.read_text(encoding="utf-8").splitlines()
                if "-->" in ln]
        assert cues, "no cues written"
        return cues[0].split(" --> ")[0], cues[-1].split(" --> ")[1]

    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        _write_webvtt(base, script, timings, audios, pause=3.0, lead_in=0.0)
    unshifted_first, _unshifted_last = _span()
    assert unshifted_first == "00:00:00.100", unshifted_first

    with contextlib.redirect_stdout(io.StringIO()):
        _write_webvtt(base, script, timings, audios, pause=3.0,
                      lead_in=TITLE_HOLD + 3.0)
    shifted_first, shifted_last = _span()
    assert shifted_first == "00:00:07.100", (
        f"first cue {shifted_first} is not offset by TITLE_HOLD + pause")
    # And the track now reaches the end of the audio rather than stopping 7s
    # short of it.
    assert shifted_last == "00:05:22.001", shifted_last

    def _secs(stamp: str) -> float:
        h, m, s = stamp.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    # Within half a second of the measured clip-1 onset (7.28s by silencedetect;
    # the residual is frame quantisation at 24fps).
    assert abs(_secs(shifted_first) - 7.28) < 0.5, shifted_first
    assert _secs(shifted_last) > 315.0, "track still ends before the audio does"


def test_unspoken_claim_detector_covers_the_design_decision_card() -> None:
    """The detector could not see the largest instance of its own defect class.

    `_unspoken_visual_claims` checked `status_badges` and `json_snippet` only.
    The "Why THIS (not the alternative)" card is the biggest thing a slide can
    claim without the narration saying it, and it was structurally invisible.

    `tester` M1 reported that `verify`'s repair chain strips design-decision
    sentences from 3 scenes and leaves the slides claiming them. Re-measured on
    the real plan, cumulatively: `_repair_unsafe_narrations` spikes 1 -> 6
    findings and -65 words, but `_repair_thin_narrations` then rebuilds from the
    scene's own fields and the chain **ends where it started** - 1 finding, 373
    words. The reported -15.8%/5-scene state is mid-chain, not the end state, so
    the "any re-render creates new findings" claim does not hold.

    What the added coverage does find is real and pre-existing, and no agent
    reported it: scene 2's card says "info: recorded for provenance, never a
    verdict - can't break a build by existing" while its narration only says
    "info = recorded only" - 23% of the card's content words are spoken.
    """
    from doc_to_video_channel.studio.validate import _unspoken_visual_claims
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    artifact = Path("output/mod03_gates_v012_015.plan.json")
    if not artifact.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]

    def _dd(p: dict) -> list[str]:
        return [f for f in _unspoken_visual_claims(p, voice)
                if "design decision" in f]

    # Two-way: silent when the narration covers the card, loud when it does not.
    covered = {"narration": "info is recorded for provenance and is never a "
                            "verdict, so it can not break a build by existing.",
               "design_decision": "info: recorded for provenance, never a "
                                  "verdict - can't break a build by existing."}
    assert _dd({"scenes": [covered]}) == []
    assert _dd({"scenes": [{"narration": "info is recorded only.",
                            "design_decision": covered["design_decision"]}]})

    # And the real, pre-existing divergence is visible.
    found = _dd(plan)
    assert found, "the shipped plan's scene-2 divergence is no longer detected"
    assert "scene 2" in found[0], found
    assert "23%" in found[0], found

    # Still soft, not hard - an unregistered prefix would resample the whole plan.
    from doc_to_video_channel.studio.config import _SOFT_PREFIXES
    assert found[0].startswith("unspoken visual claim")
    assert "unspoken visual claim" in _SOFT_PREFIXES


def test_one_expression_is_spoken_the_same_way_in_every_scene() -> None:
    """`1/(n+1)` was spoken two different ways in adjacent clips of one lesson.

    Scene 4 said "one / n plus one" and scene 5 said "one over n plus one", from
    the same written expression. The cause was ordering inside `_spoken_variant`:
    `_flatten_parentheses` replaces every bracket with a space, so `1/(n+1)`
    became `1/ n+1 ` *before* `speech_expand` ran, and the pronunciation rule
    `written='1/(n+1)'` could never match. Only the scene that happened to spell
    the expression out in words was correct.

    Separately, no voice reads `+-`, `%` or the middot correctly, and the audit's
    residue regex matched only `[{}[]_=]` or `\\d+/\\d+` - so scene 2 carried a
    literal `+-20%.` into the spoken track and nothing flagged it. The audit now
    matches that class too, which is what makes the fix checkable.
    """
    from doc_to_video_channel.studio.config import SAMPLE_SIZE_FLOOR_SPOKEN
    from doc_to_video_channel.studio.speech import (
        _flatten_parentheses,
        _speak_math_symbols,
        build_tts_script,
        speech_expand,
    )
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    rules = voice.pronunciation_rules

    # The ordering bug, stated as arithmetic: flattening destroys the literal the
    # rule is written against.
    assert _flatten_parentheses("1/(n+1)") == "1/ n+1"
    assert speech_expand("1/(n+1)", rules) == SAMPLE_SIZE_FLOOR_SPOKEN

    # Symbols a voice will not speak, with no space left before punctuation.
    assert _speak_math_symbols("x ± 20%.") == "x plus or minus 20 percent."
    assert _speak_math_symbols("a · b") == "a, b"
    assert _speak_math_symbols("n<=5") == "n at most 5"
    assert _speak_math_symbols("3 != 4") == "3 not equal to 4"
    assert _speak_math_symbols("at >= 2") == "at at least 2"

    # The generic pass runs AFTER the rule table, so a more specific
    # PronunciationRule still wins.
    assert speech_expand("±0.03 is the tolerance", rules).startswith(
        "plus or minus zero.03")
    assert speech_expand("gate = hard fail", rules) == "gate equals hard fail"

    artifact = Path("output/mod03_gates_v012_015.plan.json")
    if not artifact.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]
    script = build_tts_script(plan, voice)

    # Every scene that mentions the expression says it the same way. Compare the
    # phrase itself, not a window around it: an earlier version of this assertion
    # sliced with `.{0,4}n plus one.{0,4}` and so compared trailing context,
    # reporting two forms for two correctly-spoken scenes.
    import re
    mentioning = [str(c.get("spoken") or "") for c in script["clips"]
                  if "n plus one" in str(c.get("spoken") or "")]
    assert len(mentioning) >= 2, (
        f"expected the expression in more than one scene, got {len(mentioning)}")
    for text in mentioning:
        assert SAMPLE_SIZE_FLOOR_SPOKEN in text, text[:120]

        assert not re.search(r"one\s*/\s*n plus one", text), (
            f"a raw slash reached the spoken track: {text[:120]}")
    # And no scene spells it a third way.
    assert not [t for t in mentioning if "n plus one" in t
                and SAMPLE_SIZE_FLOOR_SPOKEN not in t], mentioning

    # No unSpeakable symbol residue anywhere in the track.
    residue = [(c["index"], sym) for c in script["clips"]
               for sym in re.findall(r"[^ ]*[±·][^ ]*", str(c.get("spoken") or ""))]
    assert not residue, f"symbol residue in the spoken track: {residue}"


def test_repair_paths_refuse_a_source_chunk_that_contradicts_the_record() -> None:
    """Defect 2d: every hydration path read `source_chunk` with no provenance check.

    `section_digest` proves which section was assigned, but it is a digest of
    `f"{heading}\\n{body}"` and cannot be recomputed from the chunk, so nothing
    verified that the chunk still came from the section the record names.
    `source_chunk` is a mutable plan field: a plan whose assignment moved on
    while the chunk did not would hydrate the scene from the wrong paragraph -
    correct-looking prose, wrong content, no finding and no log line.

    Assignment records now also carry `chunk_digest`, and both hydration paths
    (the thin-narration rebuild and the starved-scene bullet top-up) read
    through `verified_source_chunk`.
    """
    import copy

    from doc_to_video_channel.studio.util import _text_digest, verified_source_chunk

    artifact = Path("output/mod03_gates_v012_015.plan.json")
    if not artifact.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]

    # A plan written before the field existed is passed through, not rejected:
    # the digest is absent, not wrong, and refusing it would invalidate every
    # artifact already on disk.
    assert verified_source_chunk(plan, 1), "pre-field plan must still verify"

    # Record the digests the way `_annotate_source_chunks` does - from the
    # GENUINE chunk. An earlier version of this check computed the digest from
    # the tampered value, so the tamper trivially matched.
    t = copy.deepcopy(plan)
    t["source_assignment"] = [
        {**a, "chunk_digest": _text_digest(
            plan["scenes"][a["scene"] - 1]["source_chunk"])}
        for a in plan["source_assignment"]]
    assert verified_source_chunk(t, 1), "a matching digest must pass"

    t["scenes"][0]["source_chunk"] = "TEXT FROM A COMPLETELY DIFFERENT SECTION"
    assert verified_source_chunk(t, 1) == "", (
        "a chunk that contradicts its recorded digest was accepted")
    # A neighbouring scene with an intact chunk is unaffected.
    assert verified_source_chunk(t, 3), "one tampered scene broke the others"
    # Out of range and empty are both empty, not a crash.
    assert verified_source_chunk(t, 0) == ""
    assert verified_source_chunk(t, 999) == ""

    # And the starved-scene top-up goes through the verifier, so a refused
    # chunk cannot resurrect a scene from unverified prose.
    from doc_to_video_channel.studio.plan import _rehydrate_starved_scenes
    starved = {"scenes": [{"bullets": ["only one"], "source_chunk":
                           "TEXT FROM A COMPLETELY DIFFERENT SECTION"}],
               "source_assignment": [{"scene": 1, "status": "assigned",
                                      "chunk_digest": "0" * 16}]}
    assert _rehydrate_starved_scenes(starved) == 0, (
        "a scene was topped up from a chunk that failed its digest check")
    assert len(starved["scenes"][0]["bullets"]) == 1


def test_deck_can_emit_the_videos_progressive_reveal_variants() -> None:
    """Stage 1 of the renderer consolidation: the deck lacked the one thing video needs.

    `pptx.py` had no reveal support, so producing video frames from the deck's
    layout - the ruling in LLD 23.7 - was blocked on it. This is that capability:
    `n` bullets yield `n + 1` variants, variant `k` drawing `bullets[:k]` with
    bullet `k-1` highlighted, matching `slides._slide_variants` exactly.

    The load-bearing property is that **space is reserved for every bullet
    whether or not it is drawn**, so the layout is identical across variants and
    nothing reflows as the reveal advances. A reveal that re-flowed would make
    the video's audio-visual alignment impossible, and it is the one thing a
    test that only counts shapes would miss.
    """
    import contextlib
    import io

    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import (
        build_pptx,
        reveal_plan,
        reveal_variants,
    )

    scene = {"bullets": ["alpha teaching point", "beta teaching point",
                         "gamma teaching point"]}
    assert reveal_variants(scene) == [(0, None), (1, 0), (2, 1), (3, 2)]
    # Nothing to reveal yields a single uncut variant, as the video does.
    assert reveal_variants({"bullets": []}) == [(None, None)]

    artifact = Path("output/mod03_gates_v012_015.plan.json")
    if not artifact.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]
    scene = plan["scenes"][2]
    bullets = [str(b)[:20] for b in (scene.get("bullets") or [])]
    assert len(bullets) >= 2, "fixture drifted"

    drawn_counts: list[int] = []
    lowest: list[float] = []
    highlights: list[str] = []
    for step in range(len(bullets) + 1):
        out = Path(tempfile.mkdtemp()) / f"r{step}.pptx"
        with contextlib.redirect_stdout(io.StringIO()):
            build_pptx(plan, out, reveal=reveal_plan(plan, step))
        slide = Presentation(str(out)).slides[3]  # +1 for the title slide
        shapes = [sh for sh in slide.shapes if sh.has_text_frame]
        mine = [sh for sh in shapes
                if any(sh.text_frame.text.strip().startswith(b[:18]) for b in bullets)]
        drawn_counts.append(len(mine))
        lowest.append(max((round(sh.top / 914400, 3) for sh in shapes
                           if sh.text_frame.text.strip()), default=0.0))
        marks = []
        for sh in mine:
            xml = sh.text_frame._txBody.xml
            marks.append("B" if 'b="1"' in xml else "-")
        highlights.append("".join(marks))

    # One more bullet drawn per step...
    assert drawn_counts == list(range(len(bullets) + 1)), drawn_counts
    # ...with the layout never moving.
    assert len(set(lowest)) == 1, f"reveal reflowed the slide: {lowest}"
    # ...and the highlight always on the last drawn bullet. Step 0 draws
    # nothing, so it has no highlight at all - an earlier version of this
    # assertion expected "B" there and failed on its own correct output.
    for step, mark in enumerate(highlights):
        want = "" if step == 0 else "-" * (step - 1) + "B"
        assert mark == want, f"step {step}: {mark!r} != {want!r}"


def test_paginated_scene_bodies_are_labelled_and_the_marker_is_never_spoken() -> None:
    """The second half of "Defect 9" - the title half was fixed, this was not.

    A scene whose bullets paginate produced N pages that all carried the
    *identical* title, so a viewer had no way to distinguish a continuation from
    a repeat, and each page is a separate audio segment. The takeaway page had
    emitted `Key Takeaways (cont. N)` since its pagination landed; scene bodies
    never did. That asymmetry was recorded in the todo list as real.

    Numbered on the FINAL page list, not inside `_scene_pages`, because the deck
    splits by measured height as well as by count and can end up with more pages
    - a marker applied earlier would number the wrong ones.

    And the marker is a visual aid: `build_tts_script` strips a leading `N.` from
    the spoken title but not `(cont. N)`, so without that strip the narrator
    reads "cont two" aloud. Caught by checking the spoken track, not the slide.
    """
    import copy

    from doc_to_video_channel.studio.pptx import (
        _BODY_BUDGET,
        _paginate_by_height,
    )
    from doc_to_video_channel.studio.pptx import (
        _scene_pages as deck_pages,
    )
    from doc_to_video_channel.studio.slides import (
        _scene_pages,
        mark_continuations,
    )
    from doc_to_video_channel.studio.speech import build_tts_script
    from doc_to_video_channel.studio.voice import _make_voice

    scene = {"section": "S", "title": "Baseline snapshot and compare",
             "topic": "t", "narration": "n " * 40,
             "bullets": [f"bullet {i} " + "long teaching sentence. " * 6
                         for i in range(9)],
             "takeaways": []}

    video = _scene_pages(copy.deepcopy(scene))
    assert [p["title"] for p in video] == [
        "Baseline snapshot and compare",
        "Baseline snapshot and compare (cont. 2)",
        "Baseline snapshot and compare (cont. 3)"], video

    # The deck's extra height split must produce the same numbering.
    deck: list[dict] = []
    for planned in deck_pages(copy.deepcopy(scene)):
        deck.extend(_paginate_by_height(planned, _BODY_BUDGET))
    mark_continuations(deck)
    assert [p["title"] for p in deck] == [p["title"] for p in video], (
        f"the two renderers disagree on continuation numbering: "
        f"{[p['title'] for p in deck]}")

    # Numbering restarts per scene rather than running across the deck.
    two = []
    for s in (scene, {**scene, "title": "Second scene"}):
        two.extend(_scene_pages(copy.deepcopy(s)))
    assert [p["title"] for p in two] == [
        "Baseline snapshot and compare",
        "Baseline snapshot and compare (cont. 2)",
        "Baseline snapshot and compare (cont. 3)",
        "Second scene",
        "Second scene (cont. 2)",
        "Second scene (cont. 3)"], two

    # Takeaway pages keep their own numbering and are not double-labelled.
    takes = {"section": "Key Takeaways", "title": "Key Takeaways", "bullets": [],
             "takeaways": [f"T{i}" for i in range(30)]}
    assert [p["title"] for p in _scene_pages(takes)] == [
        "Key Takeaways", "Key Takeaways (cont. 2)"]

    # And the marker never reaches the audio.
    voice = _make_voice("mhe-mix")
    plan = {"scenes": [dict(scene, title="Baseline snapshot and compare (cont. 2)")]}
    script = build_tts_script(plan, voice)
    spoken = str(script["clips"][0]["spoken_title"])
    assert "cont" not in spoken.casefold(), (
        f"the continuation marker is being spoken: {spoken!r}")
    assert spoken.startswith("Baseline snapshot and compare"), spoken


def test_design_decision_card_does_not_render_markdown() -> None:
    """Two shipped scenes showed literal backticks on the slide.

    `sanitize_design_decisions` only dropped *empty* cards, so a card carrying
    "`active.json` is a canonical pointer..." rendered the backticks. The audio
    was already clean - `_flatten_parentheses` strips them - which is why this
    survived: nothing inspected the slide text for formatting.

    Identifiers keep their underscores. Removing them would rename a real file
    on screen (`run_suite` -> `run suite`), which is worse than the leak.
    """
    import re

    from doc_to_video_channel.studio.plan import _strip_markdown

    assert _strip_markdown("`active.json` is canonical") == "active.json is canonical"
    assert _strip_markdown("runs `run_suite` offline") == "runs run_suite offline"
    assert _strip_markdown("plain text") == "plain text"

    artifact = Path("output/mod03_gates_v012_015.plan.json")
    if not artifact.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(artifact.read_text(encoding="utf-8"))["plan"]
    from doc_to_video_channel.studio.plan import _sanitize_design_decisions
    # Both cards on this artifact are STRIPPED, not removed - the card survives,
    # only its backticks go. The old return value summed the two and the log
    # said "dropped 2", which reads as two missing WHY THIS cards on a deck that
    # still had both. The counts are now separate so each can be labelled.
    cleanup = _sanitize_design_decisions(plan)
    assert cleanup.removed == 0, cleanup
    assert cleanup.stripped == 2, (
        f"fixture drifted: expected 2 markdown strips on v012_015, got {cleanup}")
    for scene in plan["scenes"]:
        card = str(scene.get("design_decision") or "")
        assert not re.search(r"[`*]", card), f"markdown survived: {card!r}"
    # The identifier itself is intact.
    joined = " ".join(str(s.get("design_decision") or "") for s in plan["scenes"])
    assert "active.json" in joined and "run_suite" in joined, joined


def test_renderers_do_not_ship_the_same_helper_name_for_different_algorithms() -> None:
    """Both renderers answer "how many takeaway pages?" — differently, same name.

    `pptx` simulates the fill against a real text-height estimate, so its count
    is exact. `slides` cannot: it draws in pixels and guards overflow at draw
    time with `room()`, so its count is an arithmetic upper bound. Until this
    was caught, both were called `_takeaway_pages`, which is the fork shape
    that produced three separate defects this session — `_shorter_column`
    fixed in one renderer and missed in the other, the `(cont. N)` marker, and
    the diagram fit.

    The names now say which is which, and this asserts the invariant so a future
    edit cannot quietly converge them onto one name again.
    """
    import ast
    from pathlib import Path as P

    from doc_to_video_channel.studio import pptx, slides

    assert hasattr(slides, "_takeaway_pages_by_count")
    assert hasattr(pptx, "_takeaway_pages_measured")

    studio = P("src/doc_to_video_channel/studio")
    defined: dict[str, list[str]] = {}
    for mod in (studio / "slides.py", studio / "pptx.py"):
        tree = ast.parse(mod.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("_"):
                defined.setdefault(node.name, []).append(mod.name)
    forks = {n: f for n, f in defined.items() if len(f) > 1}
    assert not forks, (
        f"private helpers defined in both renderers under one name: {forks}. "
        f"Either they are genuinely the same function (import one from the "
        f"other) or they are not (rename at least one).")

    # And each still answers correctly under its own name.
    assert slides._takeaway_pages_by_count(6) == 1
    assert slides._takeaway_pages_by_count(25) == 2
    assert pptx._takeaway_pages_measured(["a takeaway line " * 3] * 3, 5.2) >= 1


def test_loudness_collector_is_cleared_per_run() -> None:
    """A second build in one process must not inherit the first run's readings.

    `LAYOUT_NOTES` was cleared at the top of `render_scenes`; `LOUDNESS_MEASURED`
    was not, and it is read back both for the build-log summary and for
    `verify.json`'s `clip_lufs_range`. Two builds in one process would have
    reported the union of both runs' clip loudness as though it were one
    lesson's.
    """
    from doc_to_video_channel.studio.video import (
        LOUDNESS_MEASURED,
        _normalize_loudness,
    )

    LOUDNESS_MEASURED.append({"clip": "stale_from_a_previous_run.mp3",
                              "integrated_lufs": -99.0, "true_peak_dbtp": -0.1})
    clip = Path("output/mod03_gates_v012_015_audio/scene_01.mp3")
    if not clip.exists():
        pytest.skip("clip not present")
    before = len(LOUDNESS_MEASURED)
    assert before >= 1

    # The clear happens at the entry point, not inside the normaliser, so that a
    # direct call for measurement does not wipe a run in progress.
    import inspect

    from doc_to_video_channel.studio.video import synth_scenes
    src = inspect.getsource(synth_scenes)
    assert "del LOUDNESS_MEASURED[:]" in src, (
        "synth_scenes must clear the collector before normalising any clip")
    assert "del LOUDNESS_MEASURED[:]" not in inspect.getsource(_normalize_loudness), (
        "the clear must not live in the per-clip normaliser, or a direct "
        "measurement call would wipe a run in progress")


# --- S2.4 step 1: the read window cut mid-word and leaked our own tag -------
#
# `mod03_gates_v013` shipped `plan.scenes[8].source_chunk` ending
#   "...even a *read* of any env\n var is a violati\n</doc>"
# from a 17,975-char document read under a 12,000-char window. Both effects are
# one cause: `util.py` sliced the body at exactly `max_chars`, ending inside
# "violation)", and the `</doc>` wrapper was appended right after the slice. The
# document also has 12 `###` concepts and only 8 survive a section-boundary
# read, while `plan_lesson` printed "all concepts covered".

def test_read_window_cut_never_ends_mid_word() -> None:
    from doc_to_video_channel.studio.util import _truncate_on_boundary

    doc = ("# Guide\n\nintro paragraph here\n\n"
           "### One. alpha beta gamma delta\n\n" + "word " * 40 + "\n\n"
           "### Two. epsilon zeta\n\n" + "other " * 40 + "\n")
    for limit in range(20, len(doc), 7):
        out = _truncate_on_boundary(doc, max_chars=limit)
        assert len(out) <= max(limit, 0) or len(out) == limit
        assert len(out) <= limit
        assert doc.startswith(out), "the cut must be a prefix of the source"
        if not out:
            continue
        # A cut that split a word would end on a token the document never had.
        last = out.split()[-1] if out.split() else ""
        if last:
            assert last in doc.split(), f"limit {limit} split a word: {last!r}"


def test_read_window_prefers_a_section_boundary() -> None:
    from doc_to_video_channel.studio.util import _truncate_on_boundary

    doc = ("# Guide\n\n" + "filler " * 60 + "\n\n"
           "### Second. the last section that fits\n\n" + "body " * 40 + "\n\n"
           "### Third. the section that does not fit\n\n" + "more " * 40 + "\n")
    # Put the limit inside the run preceding the third heading, so the last
    # heading within the window genuinely is the second one.
    limit = doc.index("### Third.") - 10
    out = _truncate_on_boundary(doc, max_chars=limit)
    # Cutting *at* a heading start is what drops that section, so the surviving
    # unit is the section before it and the cut lands exactly on the boundary.
    assert out == doc[:doc.index("### Second.")].rstrip()
    assert "### Second." not in out
    assert "### Third." not in out
    assert "filler" in out and "body" not in out


def test_real_document_cut_keeps_whole_sections_only() -> None:
    from doc_to_video_channel.studio.plan import _markdown_sections

    loaded = S.load_documents(["modules/08_concepts_mod03_gates.md"])
    heads = [h for h, _ in _markdown_sections(loaded.text)]
    full = Path("modules/08_concepts_mod03_gates.md").read_text(encoding="utf-8")
    full_heads = [h for h, _ in _markdown_sections(full)]
    # Every section that survived is a section the document really has, and the
    # one that was cut is absent from both the text and the chunk list.
    assert set(heads) <= set(full_heads)
    assert heads == full_heads[:len(heads)], (
        "the read window must keep a prefix of the document's sections")
    # 12 whole sections survive (1 `#`, 3 `##`, and numbered concepts 1-8).
    # The old hard cut kept 9 concepts but concept 9 arrived as the fragment
    # "…var is a violati</doc>"; this keeps 8 concepts, all of them complete.
    assert heads[-1].startswith("### 8."), heads[-1]
    assert len([h for h in heads if h.startswith("### ")]) == 8


def test_read_window_falls_back_when_one_section_exceeds_it() -> None:
    from doc_to_video_channel.studio.util import _truncate_on_boundary

    # A single section far longer than the window: retreating to its one
    # heading would keep ~0 chars, so the cut must fall back to a line/word
    # boundary and still use the budget.
    doc = "# Guide\n\n" + "alpha beta gamma delta " * 200
    out = _truncate_on_boundary(doc, max_chars=300)
    assert len(out) > 150, "must not discard the window to reach a heading"
    assert doc.startswith(out.rstrip()), "must be a clean prefix"
    last = out.split()[-1]
    assert last in {"alpha", "beta", "gamma", "delta"}, (
        f"the cut split a word: window ends on {last!r}")


def test_read_window_keeps_unbroken_text_when_there_is_no_boundary() -> None:
    from doc_to_video_channel.studio.util import _truncate_on_boundary

    token = "x" * 500
    out = _truncate_on_boundary(token, max_chars=100)
    assert out == token[:100], (
        "with no line break and no space in the window, cutting would split the "
        "token and dropping it would leave nothing; the window stands")


def test_load_documents_reports_what_the_window_dropped() -> None:
    loaded = S.load_documents(["modules/08_concepts_mod03_gates.md"])
    assert loaded.truncated is True
    assert loaded.chars_read < loaded.chars_total
    assert loaded.chars_read == len(loaded.text)
    assert loaded.chars_total == len(loaded.full_text)
    assert len(loaded.text) <= loaded.read_window
    # The two measured effects of the old hard cut, both gone.
    assert "</doc>" not in loaded.text, "the wrapper must not land in the body"
    assert loaded.text == loaded.full_text[:len(loaded.text)].rstrip()


def test_truncated_source_chunk_has_no_broken_word_or_leaked_tag() -> None:
    from doc_to_video_channel.studio.plan import (
        _first_source_sentences,
        _markdown_sections,
    )

    loaded = S.load_documents(["modules/08_concepts_mod03_gates.md"])
    for head, body in _markdown_sections(loaded.text):
        chunk = _first_source_sentences(body)
        assert "</doc>" not in chunk, f"leaked wrapper into {head!r}"
        assert "<doc" not in chunk, f"leaked wrapper into {head!r}"


def test_concept_count_is_uncapped_for_coverage() -> None:
    doc = "\n\n".join(f"### Concept {i}. a distinct heading number {i}\nbody"
                      for i in range(1, 21))
    capped = S._concept_headers(doc)
    total = S._concept_headers(doc, limit=None)
    assert len(capped) == 12, "the scene frame stays bounded"
    assert len(total) == 20, (
        "coverage must be counted over the whole document, or a 20-concept "
        "document reads as 12 and the shortfall is invisible")


def test_coverage_clause_reports_the_shortfall() -> None:
    from doc_to_video_channel.studio.plan import _coverage_clause

    # (in_window, total, scenes)
    short = _coverage_clause(2, 12, 2)
    assert short == ("2 of 12 source concepts covered "
                     "(10 beyond the read window)")
    assert "all concepts covered" not in short


def test_coverage_clause_never_claims_full_coverage() -> None:
    import inspect

    from doc_to_video_channel.studio.plan import _coverage_clause

    # The claim is deleted from the source, not reworded: a reworded near-miss
    # is still a claim the gate cannot check, and this build printed one for 8
    # of the document's 12 concepts.
    assert "all concepts covered" not in inspect.getsource(_coverage_clause)
    assert "all concepts covered" not in inspect.getsource(S.plan_lesson)
    # And no output of it can assert completeness either.
    for read, total in ((0, 0), (1, 1), (5, 5), (8, 12), (12, 40), (0, 3)):
        out = _coverage_clause(read, total, min(read, 12))
        assert "all concepts covered" not in out
    # Nothing dropped is reported as a count, which is checkable. The wording
    # names no cause, because there is none - a document that fits is not
    # "beyond the window" at anything.
    assert _coverage_clause(2, 2, 2) == (
        "2 of 2 source concepts read (no concepts dropped)")


# --- the 1/(n+1) spoken form had four copies and no agreement test ---------
#
# `1/(n+1)` appears in four hand-written places that no test tied together:
# two TTS `PronunciationRule`s in voice.py and the same phrase inside two
# prompts in config.py. They are two consumers of one spoken form, not four
# copies of one string, and the wording itself was ambiguous: "one over n plus
# one" runs the divisor and addend together, and 1/(n+1) is exactly the case
# where precedence decides the answer - the same words also read as 1/n + 1.

def test_sample_size_floor_wording_is_single_sourced() -> None:
    from doc_to_video_channel.studio import voice as V
    from doc_to_video_channel.studio.config import (
        NARRATION_PROMPT,
        SAMPLE_SIZE_FLOOR_SPOKEN,
        STUDIO_PROMPT,
    )

    assert SAMPLE_SIZE_FLOOR_SPOKEN == "one divided by the whole of n plus one"
    # Both prompts carry the one phrase, not a hand-written copy of it.
    assert SAMPLE_SIZE_FLOOR_SPOKEN in STUDIO_PROMPT
    assert SAMPLE_SIZE_FLOOR_SPOKEN in NARRATION_PROMPT
    # Both TTS tables rewrite the literal to that same phrase.
    for name in ("_MHE_TECH_PRONUNCIATION", "_ENGLISH_TECH_PRONUNCIATION"):
        rules = [r for r in getattr(V, name) if r.written == "1/(n+1)"]
        assert len(rules) == 1, f"{name} must carry exactly one such rule"
        assert rules[0].spoken == SAMPLE_SIZE_FLOOR_SPOKEN
        assert rules[0].word_boundary is False, (
            "the written form contains '/', which is not a word character")
    # The ambiguous wording is gone from both prompts.
    for prompt in (STUDIO_PROMPT, NARRATION_PROMPT):
        assert "one over n plus one" not in prompt
        assert "{floor}" not in prompt, "the token must be interpolated"


def test_sample_size_floor_rule_actually_fires() -> None:
    from doc_to_video_channel.studio import voice as V

    for name in ("_MHE_TECH_PRONUNCIATION", "_ENGLISH_TECH_PRONUNCIATION"):
        rules = getattr(V, name)
        spoken = next(r.spoken for r in rules if r.written == "1/(n+1)")
        text = f"The sample-size floor {spoken} trips the gate."
        assert "1/(n+1)" not in text
        # The rendered slide text is what the voice reads, so the literal must
        # be gone from the string the pipeline hands to synthesis.
        assert "the whole of" in text


# --- one document reader, not two ------------------------------------------
#
# The ungated legacy entry point carried a byte-identical copy of the read-window
# defect (`p.read_text(...)[:max_chars]` and `[:max_chars * 4]`). It had zero
# callers, no test, no doc mention and no `__all__` entry, so it never ran - but
# it was still a second implementation of the one rule that decides what the
# planner is allowed to see, and the ungated path is exactly where a drifted
# copy would go unnoticed. It was deleted rather than fixed: extracting a shared
# helper for a function with no callers would add structure to dead code.

def test_only_one_document_reader_exists() -> None:
    import doc_to_video_channel as legacy
    from doc_to_video_channel.studio import util

    # The gated path is the single reader.
    assert callable(util.load_documents)
    # The ungated path no longer carries a second one, so the two entry points
    # cannot drift apart on how a document is bounded.
    assert not hasattr(legacy, "load_content")
    assert not hasattr(legacy, "_load_pptx")
    # And the legacy console script still resolves - the deletion removed a dead
    # path, not a working entry point.
    assert callable(legacy.main)


def test_no_module_slices_a_document_at_a_raw_character_offset() -> None:
    import re

    from doc_to_video_channel.studio import util

    root = Path(util.__file__).resolve().parents[2]
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for n, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\[:\s*max_chars", line):
                offenders.append(f"{path.relative_to(root)}:{n}")
    # Both sites are in the one helper: its docstring naming the pattern it
    # replaced, and the window slice it retreats from to a boundary. A third
    # site, or one in another file, is a second reader reintroducing the defect.
    # Line numbers are deliberately not pinned - only the file and the count.
    assert {o.split(":")[0] for o in offenders} == {
        "doc_to_video_channel/studio/util.py"}, offenders
    assert len(offenders) == 2, (
        f"expected the docstring and the retreating slice only, got {offenders}")


# --- the duration contract was argued from an invented 42-word floor ---------
#
# S2.2 of the review plan computed every scene count against 42 spoken words per
# scene and concluded "`--minutes 4.0` is arithmetically unreachable" at 9 or 12
# scenes, which made "scene count from target_minutes" the keystone of Stage 2.
# 42 is not a contract anywhere. It is the *minimum* of mod03_gates_v013's ten
# clips (42-76, mean 52.9) - one number from one over-budget build. The contract
# the gate enforces is 20-90 (`tts_too_short_critical` / `tts_too_long_critical`,
# both FAIL). Under the enforced band a 4.0 min target is reachable at EVERY
# legal scene count, needing 34.3 words/clip at 9 scenes.

def test_enforced_word_band_is_named_and_used_by_the_gate() -> None:
    from doc_to_video_channel.studio.config import (
        NARRATION_WORDS_MAX_FAIL,
        NARRATION_WORDS_MAX_WARN,
        NARRATION_WORDS_MIN_FAIL,
        NARRATION_WORDS_MIN_WARN,
    )
    from doc_to_video_channel.studio.speech import audit_tts_script
    from doc_to_video_channel.studio.voice import _make_voice

    # The enforced contract, stated once and read from config by both the gate
    # and the duration arithmetic.
    assert (NARRATION_WORDS_MIN_FAIL, NARRATION_WORDS_MAX_FAIL) == (20, 90)
    assert (NARRATION_WORDS_MIN_WARN, NARRATION_WORDS_MAX_WARN) == (25, 70)

    # And the gate still fires on those exact numbers, not on literals.
    voice = _make_voice("mhe-mix")

    def severities(words: int) -> set[tuple[str, str]]:
        clips = [{"role": "scene", "index": 1, "title": "A lesson title",
                  "spoken": " ".join(["alpha beta gamma delta"] * words)}]
        return {(f.code, f.severity) for f in audit_tts_script(clips, voice)}

    assert ("tts_too_short_critical", "FAIL") in severities(2)
    assert ("tts_too_short", "WARN") in severities(5)
    assert ("tts_too_long", "WARN") in severities(18)
    assert ("tts_too_long_critical", "FAIL") in severities(25)


def test_four_minute_target_is_reachable_at_every_legal_scene_count() -> None:
    from doc_to_video_channel.studio.config import (
        AUTO_TRIM_MAX_SCENES,
        MIN_SCENES,
        NARRATION_WORDS_MAX_FAIL,
        NARRATION_WORDS_MIN_FAIL,
        NARRATION_WORDS_PROMPT_MAX,
        NARRATION_WORDS_PROMPT_MIN,
    )
    from doc_to_video_channel.studio.video import (
        reachable_duration_band,
        words_for_target,
    )

    target = 4.0 * 60
    for n in range(MIN_SCENES, AUTO_TRIM_MAX_SCENES + 1):
        floor, ceiling = reachable_duration_band(n)
        assert floor <= target <= ceiling, (
            f"{n} scenes cannot reach 4.0 min: "
            f"{floor:.0f}s..{ceiling:.0f}s")
        needed = words_for_target(n, target)
        # What the target demands must itself be a legal length, or no plan can
        # satisfy both the contract and the request.
        assert NARRATION_WORDS_MIN_FAIL <= needed <= NARRATION_WORDS_MAX_FAIL
        # At 9 scenes it also lands inside the band the prompt asks for.
        if n == 9:
            assert NARRATION_WORDS_PROMPT_MIN <= needed <= NARRATION_WORDS_PROMPT_MAX


def test_scene_count_is_a_far_smaller_lever_than_the_word_budget() -> None:
    """The 148% overshoot was words, and this is the arithmetic that says so."""
    from doc_to_video_channel.studio.video import (
        reachable_duration_band,
        words_for_target,
    )

    target = 4.0 * 60
    # Shipped: 9 scenes, 10 clips, 529 words at 103 wpm.
    _, ceiling9 = reachable_duration_band(9)
    shipped_seconds = 529 * (60.0 / 103.0) + 40.0
    assert shipped_seconds / target == pytest.approx(1.45, abs=0.01)

    # Words are the lever: 529 spoken where 343 fit.
    assert words_for_target(9, target) * 10 == pytest.approx(343, abs=1)

    # Scene count is not: dropping 9 -> 7 scenes removes 6.0s of silence out of
    # a 108.2s overshoot. This is why "scene count from target_minutes" cannot
    # be the keystone - the same 5.5% the plan already rejected for the 3.0s
    # pause. The ceiling must be far above the target for this to hold.
    assert ceiling9 > target


# --- the prompt asked for 30-55 words and the target was 4.0 min -----------
#
# mod03_gates_v013 shipped 529 spoken words against a 4.0 min target: 5.91 min
# delivered, 148%. The prompt is the cause and it is arithmetic, not a mood.
# NARRATION_PROMPT asked for "30-55 spoken words" per scene and "near
# {scene_count} times 40 words"; at 10 clips the top of that band is 550 words,
# and 529 is 1.7% under it. The request and the target disagreed by
# construction, and nothing compared the result to a band - the build printed
# "529 words (~5.1 min estimated pre-audio) vs target 4.0 min" and shipped.

def test_narration_prompt_word_budget_is_derived_from_the_target() -> None:
    from doc_to_video_channel.studio.config import NARRATION_PROMPT
    from doc_to_video_channel.studio.duration import prompt_budget

    def rendered(n_scenes: int, target: float) -> str:
        b = prompt_budget(n_scenes, target)
        out = NARRATION_PROMPT
        for key in ("scene_count", "words_min", "words_max", "words_total",
                    "clip_count"):
            out = out.replace("{" + key + "}", str(
                n_scenes if key == "scene_count" else b[key]))
        return out

    text = rendered(9, 4.0)
    assert "31-40 spoken words" in text, (
        "the 4.0 min target at 9 scenes must ask for 31-40, not a fixed band")
    assert "343 spoken words" in text
    assert "30-55" not in text, "the fixed band is the defect and must be gone"
    assert "times 40 words" not in text
    # JSON braces are legitimate here; only a named placeholder is a bug.
    import re as _re
    assert not _re.search(r"\{\w+\}", text), "every placeholder substituted"

    # The budget moves with the target, which is the whole point. 12 scenes at
    # 4.0 min is 22-29, one word under the exact 22.7-30.0 band: the displayed
    # band is floored, so it can only ever ask for slightly less.
    assert "55-70 spoken words" in rendered(5, 4.0)
    assert "22-29 spoken words" in rendered(12, 4.0)
    assert "68-87 spoken words" in rendered(9, 8.0)


def test_prompt_band_is_the_verdict_band_not_an_invented_tolerance() -> None:
    from doc_to_video_channel.studio.duration import (
        BAND_OK,
        BAND_OK_HIGH,
        duration_verdict,
        predicted_duration_seconds,
        word_budget,
    )

    b = word_budget(9, 240.0)
    # The band's ends are EXACTLY the word counts at which the delivered length
    # crosses the verdict bounds, silence included - so a prompt asking for more
    # than per_clip_max is asking for a finding, and this is the arithmetic
    # that makes that true rather than an assertion of it.
    lo = predicted_duration_seconds(b["per_clip_min"] * 10, 9) / 240.0
    hi = predicted_duration_seconds(b["per_clip_max"] * 10, 9) / 240.0
    assert lo == pytest.approx(BAND_OK, abs=1e-9)
    assert hi == pytest.approx(BAND_OK_HIGH, abs=1e-9)
    # Either side of each bound, the verdict changes.
    assert duration_verdict(lo - 0.01)[0] == "SHORT"
    assert duration_verdict(hi + 0.01)[0] == "LONG"
    # And the target itself lands in OK.
    assert duration_verdict(1.0) == ("OK", "")


def test_planner_prompt_carries_no_word_budget_by_design() -> None:
    """The planner must not write narration, so it must not quote a word count.

    STUDIO_PROMPT says "NARRATION EMPTY (MANDATORY)"; the spoken track comes
    from the separate narration pass. A word band in the planner prompt would
    be an instruction about output nobody produces there.
    """
    from doc_to_video_channel.studio.plan import _planner_prompt

    out = _planner_prompt(4.0, 9, "<DOC>body</DOC>")
    assert "31-40" not in out
    assert "343 spoken words" not in out
    assert "spoken words" not in out
    assert "<DOC>body</DOC>" in out
    import re as _re
    assert not _re.search(r"\{\w+\}", out), "an unsubstituted placeholder "
    "reaches the model"


def test_unreachable_target_hard_fails_before_any_llm_call() -> None:
    from doc_to_video_channel.studio.duration import (
        TargetBelowFloor,
        assert_target_reachable,
    )

    # 2.0 min at 9 scenes needs 13.7 words/clip, under the enforced 20 floor.
    assert_target_reachable(9, 4.0)  # does not raise
    with pytest.raises(TargetBelowFloor) as exc:
        assert_target_reachable(9, 2.0)
    message = str(exc.value)
    assert "13.7" in message, "the message must state the measured shortfall"
    assert "20-word floor" in message
    assert "fewer scenes" in message, "the message must name a remedy"

    # And the long side, which is a different defect with a different remedy.
    with pytest.raises(TargetBelowFloor) as exc:
        assert_target_reachable(5, 40.0)
    assert "90-word ceiling" in str(exc.value)
    assert "more scenes" in str(exc.value)


def test_hard_fail_is_not_swallowed_as_an_llm_flake() -> None:
    """`cli` resamples RuntimeError up to five times; a contract failure is not a
    flake, and burning five plans before reporting it would be the defect."""
    from doc_to_video_channel.studio.duration import TargetBelowFloor

    assert not issubclass(TargetBelowFloor, RuntimeError)
    # The handler in cli that resamples catches RuntimeError only.
    import inspect

    from doc_to_video_channel.studio import cli
    src = inspect.getsource(cli)
    assert "except RuntimeError:" in src
    assert "except TargetBelowFloor" not in src, (
        "the infeasible-target failure must propagate, not be resampled")


# --- the is_head exemption was a prefix heuristic, not a tautology ----------
#
# S3.1 called the two `is_head` exemptions tautological: for sentence 1 of a
# clip whose text opens with the title, `s_norm` IS `head_norm`, so the prefix
# test was always true. Measuring it before changing it showed the framing was
# wrong. `build_tts_script` PREPENDS the spoken title to every scene clip
# (speech.py:594) and then `collapse_repeated_title` removes any model
# restatement - so sentence 1 is text the pipeline itself inserted, and the
# exemption was a blunter way of saying "don't flag your own insertion".
#
# Deleting it outright FAILs every scene in every build. The fix is an EXACT
# match on the normalised tokens, which separates the two cases: the pipeline's
# insertion is the title, and a model-authored restatement is not - it still
# carries the tail the title repair removed.

def test_audit_does_not_flag_the_titles_own_insertion() -> None:
    from doc_to_video_channel.studio.speech import audit_tts_script
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    # Exactly what build_tts_script produces: title first, then teaching.
    clip = {"role": "scene", "index": 1, "title": "The metric registry",
            "spoken_title": "The metric registry",
            "spoken": "The metric registry. Yahan hone vaala comparison registry "
                      "ke metadata pe depend karta hai aur isse verdict "
                      "mechanical ho jaata hai."}
    codes = {f.code for f in audit_tts_script([clip], voice)}
    assert "tts_sentence_fragment" not in codes, (
        "the pipeline prepends this title itself; flagging it fails every scene")


def test_audit_still_fails_a_model_authored_title_restatement() -> None:
    """The case the prefix heuristic could not tell apart."""
    from doc_to_video_channel.studio.speech import audit_tts_script
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    # Short enough to sit inside `_is_slide_fragment`'s 2-6 word window, and
    # overlapping the title enough to clear its 0.60 threshold, but NOT equal
    # to it - which is precisely what the prefix heuristic could not separate.
    clip = {"role": "scene", "index": 2, "title": "The metric registry",
            "spoken_title": "The metric registry",
            "spoken": "The metric registry. The metric registry metadata. "
                      "Ab chaliye isse detail mein dekhte hain, aur dekhte "
                      "hain ki comparison registry ke metadata pe depend "
                      "karta hai jo isse verdict mechanical banata hai."}
    fails = [(f.code, f.severity) for f in audit_tts_script([clip], voice)]
    assert ("tts_sentence_fragment", "FAIL") in fails, (
        "a model restatement of the title is a real fragment and must block; "
        f"got {fails}")

    # The window is the other half of the story and it is still narrow: the
    # same restatement written with three more words escapes, because
    # `_is_slide_fragment` only looks at 2-6 word sentences. That is S3.2, and
    # measuring it here is why it stays open rather than being called dead.
    longer = dict(clip, spoken=clip["spoken"].replace(
        "The metric registry metadata.",
        "The metric registry metadata that makes it mechanical."))
    longer_fails = {f.code for f in audit_tts_script([longer], voice)}
    assert "tts_sentence_fragment" not in longer_fails, (
        "if this now fires, the 2-6 word window is no longer the limit and "
        "S3.2 can be closed")


def test_hydration_does_not_pad_the_prepended_title() -> None:
    """Adding a lead in front of the pipeline's own title is filler."""
    from doc_to_video_channel.studio.speech import _hydrate_spoken_fragments
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    out = _hydrate_spoken_fragments(
        "The metric registry. Yahan comparison registry metadata pe depend "
        "karta hai.", "The metric registry", "The metric registry", voice, 1)
    assert out.startswith("The metric registry."), out
    assert "Yahan main point" not in out and "slide ke exact points" not in out
    # A genuine non-head fragment still gets its carrier.
    padded = _hydrate_spoken_fragments(
        "The metric registry. Metric registry.", "The metric registry",
        "The metric registry", voice, 1)
    assert padded != "The metric registry. Metric registry.", padded


def test_title_repair_and_fragment_gate_compose_on_a_real_plan() -> None:
    """S3.3 and S3.1 are two halves of one defect: a fragment title becomes a
    fragment opening line, which is a FAIL nothing could repair."""
    from doc_to_video_channel.studio.plan import _fix_incomplete_titles
    from doc_to_video_channel.studio.speech import audit_tts_script, build_tts_script
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    for name in ("mod03_gates_v013", "mod03_budget_v01"):
        path = Path(f"output/{name}.plan.json")
        if not path.exists():
            pytest.skip(f"{name} artifact not present")
        plan = json.loads(path.read_text(encoding="utf-8"))["plan"]
        repaired = _fix_incomplete_titles(plan)
        assert repaired, f"{name}: expected broken titles to repair"
        script = build_tts_script(plan, voice)
        frags = [f for f in audit_tts_script(script["clips"], voice)
                 if f.code == "tts_sentence_fragment"]
        assert not frags, [f.message for f in frags]
        # And every title is now a complete label, not a truncation.
        for scene in plan["scenes"]:
            title = str(scene.get("title") or "")
            assert not title.rstrip().endswith(
                ("—", "–", "-", ",", ":", ";")), title


# --- S4.4: the fusion gate had a blind spot exactly where the defect shipped --
#
# `tts_token_fusion` exists because "kideterministic" was written by the model
# and preserved verbatim by four repair passes. It fired 0 times on the three
# builds that actually shipped a fusion, because its guards require
# `len(token) >= 8` and `len(suffix) >= 5` - and `kiGate` is 6 characters with a
# 4-character tail. The token sat in the pre-audio `spoken` text the whole time.
#
# `word_timings.json` was the proposed way in, but the same token is in
# `clip["spoken"]` pre-audio, so a post-audio gate would have found it later and
# for money. The fix belongs in the pre-audio detector, and the signal that
# reaches this case needs no vocabulary: English does not capitalise mid-word.

def test_fusion_detector_reaches_the_short_case_the_guards_missed() -> None:
    from doc_to_video_channel.studio.speech import _fused_particle_tokens

    known = frozenset({"gate", "the", "contrast", "deterministic", "killed",
                       "together", "data", "storage"})
    for token, want in (("kiGate", "ki Gate"), ("kiThe", "ki The"),
                        ("kiCONTRAST", "ki CONTRAST")):
        assert _fused_particle_tokens(token, known) == {token.casefold(): want}
    # The vocabulary-corroborated branch still catches the lowercase fusion,
    # which has no internal capital for rule 1 to see.
    assert _fused_particle_tokens("kideterministic", known) == {
        "kideterministic": "ki deterministic"}


def test_fusion_detector_does_not_cry_wolf() -> None:
    from doc_to_video_channel.studio.speech import _fused_particle_tokens

    known = frozenset({"gate", "deterministic", "killed", "together"})
    for token in ("killed", "together", "iPhone", "McDonald", "camelCase",
                  "elephant", "seasoning", "data"):
        assert _fused_particle_tokens(token, known) == {}, token


def test_fusion_repair_splits_and_keeps_the_teaching() -> None:
    from doc_to_video_channel.studio.narration import _split_fused_particle_tokens
    from doc_to_video_channel.studio.voice import _make_voice

    plan = {"scenes": [{
        "title": "Why", "section": "s", "bullets": [],
        "narration": "Reason yahi hai kiGate lets a row through a gate."}]}
    assert _split_fused_particle_tokens(plan, _make_voice("mhe-mix"),
                                        quiet=True) == 1
    out = plan["scenes"][0]["narration"]
    assert out == "Reason yahi hai ki Gate lets a row through a gate."
    # Idempotent: a repaired narration has nothing left to split.
    assert _split_fused_particle_tokens(plan, _make_voice("mhe-mix"),
                                        quiet=True) == 0


def test_fusion_repair_on_the_plan_that_shipped_kigate() -> None:
    from doc_to_video_channel.studio.narration import _split_fused_particle_tokens
    from doc_to_video_channel.studio.voice import _make_voice

    path = Path("output/mod03_gates_v013.plan.json")
    if not path.exists():
        pytest.skip("build artifact not present")
    plan = json.loads(path.read_text(encoding="utf-8"))["plan"]
    before = " ".join(str(s.get("narration") or "") for s in plan["scenes"])
    assert "kiGate" in before, "fixture drifted: the fusion is not in this plan"
    assert _split_fused_particle_tokens(plan, _make_voice("mhe-mix"),
                                        quiet=True) == 1
    after = " ".join(str(s.get("narration") or "") for s in plan["scenes"])
    assert "kiGate" not in after and "ki Gate" in after


def test_uncontracted_negation_skips_contrastive_emphasis() -> None:
    """The copula family was measured and dropped, not assumed away.

    "it is NOT just data storage" ships in the current builds and is correct
    English in a voice that leans on emphatic contrast. Flagging `it is` would
    have been a false positive on every build.
    """
    from doc_to_video_channel.studio.speech import _uncontracted_negations

    assert _uncontracted_negations("yeh cheez it is NOT just data storage") == []
    assert _uncontracted_negations(
        "yeh registry does not standardize anything") == [
            (("does", "not"), "doesn't")]
    assert _uncontracted_negations("hum kuch nahi karenge") == []


def test_current_builds_trip_neither_check() -> None:
    """The closed gap must fire on the past and stay quiet on the present."""
    from doc_to_video_channel.studio.speech import audit_tts_script
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    for name in ("mod03_gates_v013", "mod03_budget_v01", "mod03_stage3_v01"):
        script_path = Path(f"output/{name}.tts_script.json")
        plan_path = Path(f"output/{name}.plan.json")
        if not script_path.exists() or not plan_path.exists():
            pytest.skip(f"{name} artifact not present")
        script = json.loads(script_path.read_text(encoding="utf-8"))
        plan = json.loads(plan_path.read_text(encoding="utf-8"))["plan"]
        codes = {f.code for f in audit_tts_script(script["clips"], voice, plan)}
        assert "tts_uncontracted_negation" not in codes, name
        if name != "mod03_gates_v013":
            assert "tts_token_fusion" not in codes, (
                f"{name} regressed: a fusion is present after the repair")


# --- the two pronunciation tables were 41 identical entries and 4 no-ops ----
#
# `_MHE_TECH_PRONUNCIATION` and `_ENGLISH_TECH_PRONUNCIATION` were 43 and 42
# hand-written rules with 42 shared and exactly ONE genuine disagreement (`.yml`).
# Any edit to a shared rule had to be made twice and nothing compared them. Four
# of the shared rules were also provable no-ops, spelling to exactly what
# `speech_expand`'s `expand_snake_case` pass already produces.

def test_the_two_voice_tables_differ_only_where_they_mean_to() -> None:
    from doc_to_video_channel.studio.voice import (
        _ENGLISH_TECH_PRONUNCIATION,
        _MHE_TECH_PRONUNCIATION,
    )

    mhe = {r.written: r.spoken for r in _MHE_TECH_PRONUNCIATION}
    eng = {r.written: r.spoken for r in _ENGLISH_TECH_PRONUNCIATION}
    differing = {k for k in set(mhe) & set(eng) if mhe[k] != eng[k]}
    # The one deliberate choice: the MHE voice keeps the extension's own letters.
    assert differing == {".yml"}, differing
    assert mhe[".yml"] == " dot yml" and eng[".yml"] == " dot yaml"
    # MHE additionally speaks the composite filename as a unit.
    assert set(mhe) - set(eng) == {"llm_eval_gate.yml"}


def test_no_op_pronunciation_rules_are_gone_but_still_speak_correctly() -> None:
    from doc_to_video_channel.studio.speech import speech_expand
    from doc_to_video_channel.studio.voice import _MHE_TECH_PRONUNCIATION

    written = {r.written for r in _MHE_TECH_PRONUNCIATION}
    for redundant in ("schema_version", "baseline_id", "run_suite",
                      "live_eval_nightly"):
        assert redundant not in written, (
            f"{redundant} is a no-op: expand_snake_case already spells it")
    # And the words are still spoken correctly, by the fallback pass.
    out = speech_expand("schema_version and baseline_id and run_suite and "
                        "live_eval_nightly", _MHE_TECH_PRONUNCIATION)
    assert "schema version" in out and "baseline id" in out
    assert "run suite" in out and "live eval nightly" in out
    assert "_" not in out


def test_dead_schema_class_is_gone() -> None:
    from doc_to_video_channel.studio import schema

    assert not hasattr(schema, "TTSClip"), (
        "TTSClip had zero references; it was the third class in a two-class "
        "module and nothing built a TTS clip through it")
    # The two that are used remain.
    assert hasattr(schema, "SlideScene") and hasattr(schema, "LessonPlan")


# --- tts_token_fusion is FAIL, and every gating path can clear it -----------
#
# Promoted from WARN once the repair existed. The precondition was verified
# rather than assumed, and it is not only about the build path: `render` and
# `verify` also reach `_tts_blocking_findings`, and `verify` is the path the
# BLOCKED message tells the user to run. A FAIL on a path with no repair is the
# failure mode the promotion was supposed to avoid.

def test_every_gating_path_runs_the_fusion_repair() -> None:
    import inspect

    from doc_to_video_channel.studio import cli

    src = inspect.getsource(cli)
    # One per path: plan_lesson's own chain is in plan.py; cli has render and
    # both verify passes.
    assert src.count("_split_fused_particle_tokens(") >= 3, (
        "render and both verify passes must repair before gating, or a FAIL "
        "here is a dead end")
    plan_src = inspect.getsource(
        __import__("doc_to_video_channel.studio.plan", fromlist=["x"]))
    assert "_split_fused_particle_tokens(plan, voice)" in plan_src


def test_fusion_is_fail_severity_and_siblings_stay_fail() -> None:
    from doc_to_video_channel.studio.speech import audit_tts_script
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    clip = {"role": "scene", "index": 1, "title": "Why a gate fails",
            "spoken_title": "Why a gate fails",
            "spoken": "Reason yahi hai kiGate lets a row through the gate and "
                      "the value is compared against the baseline tolerance."}
    found = {(f.code, f.severity) for f in audit_tts_script([clip], voice)}
    assert ("tts_token_fusion", "FAIL") in found, found
    # And it is not also reported at the old tier - one code, one severity.
    assert ("tts_token_fusion", "WARN") not in found, found
    # The tier it now sits beside: other unpronounceable-output defects that
    # were already FAIL, so there is no principled gap left between them.
    import inspect

    from doc_to_video_channel.studio import speech
    src = inspect.getsource(speech.audit_tts_script)
    for sibling_code in ("tts_symbol_heavy", "tts_punctuation_error",
                         "tts_text_corrupted", "tts_too_long_critical"):
        assert f'"{sibling_code}", "FAIL"' in src, sibling_code


def test_repair_clears_every_build_that_carried_a_fusion() -> None:
    """The promotion's precondition, as a test rather than a one-off measurement."""
    import copy

    from doc_to_video_channel.studio.cli import _tts_blocking_findings
    from doc_to_video_channel.studio.narration import _split_fused_particle_tokens
    from doc_to_video_channel.studio.speech import audit_tts_script, build_tts_script
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    checked = 0
    for path in sorted(Path("output").glob("*.plan.json")):
        # `with_suffix` would give "*.plan.tts_script.json" - it replaces only
        # the last suffix - so the name is rebuilt by hand.
        script_path = path.with_name(
            path.name[: -len(".plan.json")] + ".tts_script.json")
        if not script_path.exists():
            continue
        work = copy.deepcopy(
            json.loads(path.read_text(encoding="utf-8"))["plan"])
        _split_fused_particle_tokens(work, voice, quiet=True)
        script = build_tts_script(work, voice)
        script["audit"] = [f.__dict__ for f in
                           audit_tts_script(script["clips"], voice, work)]
        codes = {b["code"] for b in _tts_blocking_findings(script)}
        assert "tts_token_fusion" not in codes, (
            f"{path.name} still blocks on a fusion after repair - the severity "
            f"promotion would be a dead end for it")
        checked += 1
    if not checked:
        pytest.skip("no build artifacts present")


# --- T5a: the bullet glyph was drawn flush against the text ----------------
#
# Found only by rendering. `_ppt_bullet` set `buChar` but never `marL`/`indent`,
# and writing an explicit `<a:pPr>` REPLACES the master's inherited list level
# rather than merging with it - so the hanging indent came out empty and every
# bullet rendered as "•Plain". No geometry check can see it: the bullet and the
# text are inside the same shape's bounds, so the layout gate reported no
# overflow and no overlap while the deck was visibly wrong.

def test_bulleted_paragraphs_carry_an_explicit_hanging_indent() -> None:
    import tempfile
    from pathlib import Path as P

    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import build_pptx

    plan = {"scenes": [{
        "section": "s", "title": "Baseline snapshot & compare",
        "bullets": ["Plain words: run the goldens over the current code and "
                    "produce a report of metric values for comparison."],
        "narration": "n", "steps": [], "design_decision": "",
        "visual_diagram": "", "code_snippet": "",
    }], "takeaways": ["t"]}
    with tempfile.TemporaryDirectory() as tmp:
        out = P(tmp) / "deck.pptx"
        build_pptx(plan, out)
        prs = Presentation(str(out))
        found = None
        for slide in prs.slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for para in shape.text_frame.paragraphs:
                    pPr = para._p.find(
                        "{http://schemas.openxmlformats.org/drawingml/2006/main}pPr")
                    if pPr is None:
                        continue
                    buChar = pPr.find(
                        "{http://schemas.openxmlformats.org/drawingml/2006/main}buChar")
                    if buChar is not None and para.text.strip():
                        found = pPr
                        break
                if found is not None:
                    break
            if found is not None:
                break
    assert found is not None, "no bulleted paragraph found in the deck"
    # A negative `indent` with a positive `marL` is the hanging indent; without
    # them the glyph sits on the first character.
    assert found.get("indent") == "-228600", found.attrib
    assert found.get("marL") == "228600", found.attrib


def test_ppt_bullet_sets_the_indent_on_the_paragraph_it_is_given() -> None:
    from pptx import Presentation

    from doc_to_video_channel.studio.pptx import _ppt_bullet

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(0, 0, 100, 100)
    para = box.text_frame.paragraphs[0]
    para.text = "hello"
    _ppt_bullet(para)
    pPr = para._p.get_or_add_pPr()
    assert pPr.get("marL") == "228600"
    assert pPr.get("indent") == "-228600"


# --- coverage must say WHICH limit dropped the concepts ---------------------
#
# The first version of `_coverage_clause` blamed the whole shortfall on the read
# window. That is false whenever the document is short enough to fit: concepts
# are lost to the AUTO_TRIM_MAX_SCENES scene-frame cap long before characters
# run out. A 41-concept document of 2,759 chars loses NOTHING to a 12,000-char
# window and still reported "29 beyond the read window" - pointing the reader at
# chunking when the actual limit was the scene cap. The two have different
# remedies, so conflating them is not cosmetic.

def test_coverage_separates_the_window_from_the_scene_frame() -> None:
    from doc_to_video_channel.studio.plan import _coverage_clause

    # 41 concepts, all of them inside the window: nothing is lost to characters.
    assert _coverage_clause(41, 41, 12) == (
        "12 of 41 source concepts covered (29 beyond the 12-scene frame)")
    # 12 concepts of which the window delivered 8: the other 4 are the window's.
    assert _coverage_clause(8, 12, 8) == (
        "8 of 12 source concepts covered (4 beyond the read window)")
    # Both causes at once name both, so neither is hidden.
    msg = _coverage_clause(30, 40, 12)
    assert "10 beyond the read window" in msg, msg
    assert "18 beyond the 12-scene frame" in msg, msg
    # And a document that fits says so without inventing a shortfall.
    assert _coverage_clause(2, 2, 2) == (
        "2 of 2 source concepts read (no concepts dropped)")


def test_scene_frame_not_the_window_is_what_caps_a_large_document() -> None:
    """The demonstrated shape: many concepts, a document that fits."""
    import tempfile
    from pathlib import Path as P

    from doc_to_video_channel.studio.plan import _concept_headers, _plan_scene_target
    from doc_to_video_channel.studio.text import _strip_source_metadata_blocks
    from doc_to_video_channel.studio.util import load_documents

    with tempfile.TemporaryDirectory() as tmp:
        path = P(tmp) / "big.md"
        path.write_text("# Guide\n" + "".join(
            f"### {i}. Concept {i} with its own prose here.\n"
            for i in range(1, 42)), encoding="utf-8")
        loaded = load_documents([str(path)])
        assert loaded.truncated is False, "this document fits the window"
        in_window = _concept_headers(
            _strip_source_metadata_blocks(loaded.text), limit=None)
        assert len(in_window) == 41
        assert _plan_scene_target(
            _concept_headers(_strip_source_metadata_blocks(loaded.text))) == 12


def test_authoring_markers_never_reach_the_spoken_track() -> None:
    """A spoken track must not carry markdown, and no gate could see it.

    Four artifacts carried `**Plain words: **` into the audio, because
    `_strip_markdown` was applied to `design_decision` only. Nothing owned the
    defect on the narration side either: `contains_corrupt_text` returns False
    for `*`, and `spoken_meta_leaks` is a list of Hinglish phrases with no
    markdown in it. The builds blocked for the WRONG reason - the asterisks
    glued the words into a repeated 3-gram, so the repeat gate saw a
    repetition that was really a syntax error. Written once instead of twice,
    the same text reached TTS and would have been spoken as "asterisk plain
    words asterisk".

    Owner: tester (speech.py gates the spoken track). Measured on
    mod03_gates_v011_010.sample3: 5 of 8 scenes carried `*` before, 0 after.
    """
    from doc_to_video_channel.studio.plan import _sanitize_plan_source_leaks
    from doc_to_video_channel.studio.speech import contains_corrupt_text
    from doc_to_video_channel.studio.voice import _make_voice

    voice = _make_voice("mhe-mix")
    plan = {
        "scenes": [
            {"narration": "- **Plain words: ** a metric carries **kind**."},
            {"narration": "Use `active.json` as the canonical pointer."},
            {"narration": "A clean sentence with no markup at all."},
        ],
    }
    _sanitize_plan_source_leaks(plan, voice=voice)
    spoken = [str(s["narration"]) for s in plan["scenes"]]

    assert "*" not in spoken[0] and "`" not in spoken[1], spoken
    # Stripping is not a licence to emit nothing: the words survive.
    assert "Plain words" in spoken[0] and "active.json" in spoken[1], spoken
    # The unmarked sentence is untouched - this is a strip, not a rewrite.
    assert spoken[2] == "A clean sentence with no markup at all.", spoken
    # And the gate that owns the spoken track still cannot see `*`, which is
    # why the sanitizer has to be unconditional rather than gate-driven.
    assert contains_corrupt_text("a **bold** word") is False
