"""Which vendored modules have landed, and can the tree actually import.

**Why this exists.** `pyproject.toml` sets `ignore_missing_imports = true`, which
was justified as "the vendored test files are type-dirty" — a third-party-stub
concern. But it ALSO silences a **missing sibling module**, which is a different
defect entirely: `doc_to_video_channel.studio.duration` not existing is a
build-order state, not an untyped dependency. Measured at V4: `ruff` passed,
`pytest` passed, `mypy` reported one unrelated error, and **all three were
indifferent to the fact that `plan.py` could not be imported at all** because four
of its eight sibling imports land at V5.

So the gate cannot see this class of defect, and something has to. This file states
the expected state per step, and FAILS if the tree is importable earlier than
scheduled or broken later than scheduled — both of which are real defects.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

STUDIO = Path(__file__).resolve().parents[1] / "src/doc_to_video_channel/studio"
PLAN = "doc_to_video_channel.studio"

#: Which build step each module lands in, from LLD 5.5. `plan.py` is deliberately
#: alone at V4 and the remaining ten arrive at V5, so between V4 and V5 the tree was
#: KNOWN to be unimportable. That is a recorded intermediate state, not a defect --
#: what would be a defect is it being unimportable for any other reason.
#:
#: `writer` is OURS and lands at V5, and it is in this table rather than only in
#: `OURS_IN_STUDIO` because `video.py` imports it. Measured: the "every relative
#: import must be scheduled" check failed on `['writer']` -- a file we wrote, in the
#: tree, on the critical path, absent from the one table that says when things
#: arrive. An import nothing can schedule is an import nothing will ever verify.
STEP_OF = {
    "util": "V1", "text": "V1", "config": "V1",
    "topics": "V2", "schema": "V2",
    "plan": "V4",
    "cli": "V5", "duration": "V5", "llm": "V5", "narration": "V5",
    "pptx": "V5", "slides": "V5", "speech": "V5", "validate": "V5",
    "video": "V5", "voice": "V5",
    "writer": "V5",  # OURS, not vendored: AC#26's egress chokepoint
}

#: The most recent step landed. Advances as the build proceeds; every expectation
#: below is derived from it rather than hardcoded per module, so V5 was one line
#: rather than a rewrite -- and the V4-specific tests still had to be REPLACED,
#: because a test that asserts a state which has just become false is a test that
#: fails, and the obvious reading is that the change broke something.
LANDED_THROUGH = "V5"


#: Files WE wrote that live in `studio/` because the renderers must reach them.
#: `writer.py` is the first: AC#26's egress chokepoint, called from
#: `_render_media`. It is not vendored, so `STEP_OF` does not list it, and without
#: this the "landed modules on disk" check reads our own file as an unplanned
#: extra. Declared once here and once in the segregation test, which is a
#: duplication worth naming -- the alternative, a manifest row for a file we wrote,
#: would be a worse lie, because the manifest records what came from VENDOR_REF.
OURS_IN_STUDIO = frozenset({"writer"})


def landed() -> set[str]:
    order = ["V1", "V2", "V4", "V5"]
    limit = order.index(LANDED_THROUGH)
    allowed = {s for s in order[: limit + 1]}
    return {name for name, step in STEP_OF.items() if step in allowed}


def sibling_imports(name: str) -> set[str]:
    source = (STUDIO / f"{name}.py").read_text(encoding="utf-8")
    return set(re.findall(r"^from \.([a-z_]+) import", source, re.M))


def test_every_landed_module_is_on_disk_and_no_others() -> None:
    on_disk = {p.stem for p in STUDIO.glob("*.py")} - {"__init__"}
    assert on_disk == landed() | set(OURS_IN_STUDIO), (
        f"the tree holds {sorted(on_disk)} but through {LANDED_THROUGH} it should hold "
        f"landed {sorted(landed())}"
    )


@pytest.mark.parametrize("name", sorted(landed()))
def test_a_landed_module_imports(name: str) -> None:
    """A module that has landed must actually import.

    This is the check the gate cannot make. `plan.py` is scheduled at V4 and is on
    disk, and it does not import -- which is correct *only* because its missing
    siblings are V5 modules. So the test is split: a module whose siblings have all
    landed must import, and one whose siblings are still scheduled must not.
    """
    missing = sibling_imports(name) - landed()
    if missing:
        pytest.skip(
            f"{name} awaits {sorted(missing)} (V5), so the tree is knowingly "
            f"unimportable at {LANDED_THROUGH}"
        )
    assert importlib.import_module(f"{PLAN}.{name}") is not None


@pytest.mark.parametrize("name", sorted(landed()))
def test_a_landed_module_only_imports_modules_that_are_scheduled(name: str) -> None:
    """A relative import must name a module the build order knows about.

    An import of something the manifest never mentions is a silent dependency: it
    cannot be scheduled, so nothing verifies it.
    """
    unknown = sibling_imports(name) - set(STEP_OF)
    assert not unknown, (
        f"{name}.py imports {sorted(unknown)}, which is not in the build order at "
        f"all -- it cannot be scheduled, so nothing will ever verify it"
    )


def test_the_tree_imports_entirely_now_that_V5_has_landed() -> None:
    """The V4 counterpart asserted the tree could NOT import, and named the blockers.

    Kept as a transition rather than deleted: the V4 assertion was correct then and
    is wrong now, and the point of recording it is that the build order's one
    knowingly-unimportable window has CLOSED.
    """
    for name in sorted(landed() | set(OURS_IN_STUDIO)):
        module = importlib.import_module(f"{PLAN}.{name}")
        assert module is not None, f"{name} is landed but does not import"


# --- the 5.6 harness: inert at V4, live at V5 --------------------------------


def test_the_harness_now_patches_both_bindings() -> None:
    """The V4 test asserted `patched == []`. V5 makes it two, and that is the point.

    One patched binding measures the plan chain and is blind to narration, which the
    LLD says cost two review rounds. Asserting the COUNT is what stops the harness
    from quietly measuring half the pipeline.
    """
    from doc_to_video_channel import planning_harness as ph

    patched = ph.install_stub()
    assert sorted(patched) == ["narration", "plan"], (
        f"patched {patched}: both bindings exist at V5 and both must be patched"
    )


def test_the_harness_no_longer_reports_that_it_cannot_run() -> None:
    """At V4 it exited 2 with the blocker named. That is no longer true, and saying so
    would be a false claim about the tree."""
    from doc_to_video_channel import planning_harness as ph

    runnable, why = ph.plan_lesson_is_runnable()
    assert runnable, f"plan_lesson must be callable at V5: {why}"


# --- planning_harness.main(): the decision tree, and it was ENTIRELY untested ---
#
# Measured: `main()` had ZERO coverage and accounted for 100% of the 38 missed
# statements in this project's own code. The function whose whole job is reporting
# honestly about whether it ran was itself never called -- because rewriting the V4
# section at V5 dropped the one call. So the tree is covered branch by branch, and
# each branch asserts the code that makes it reachable.


def test_help_prints_the_docstring_and_asks_for_no_run(capsys: pytest.CaptureFixture[str]) -> None:
    from doc_to_video_channel import planning_harness as ph

    assert ph.main(["--help"]) == ph.EXIT_CANNOT_RUN
    assert "vary within a run" in capsys.readouterr().out


def test_a_constant_stub_makes_the_harness_refuse_to_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A self-test failure must stop the run with its OWN code, not a pass.

    `EXIT_SELF_TEST_FAILED` is 3, distinct from 0 and from 2. If a broken stub
    produced a pass, the harness would be certifying a measurement it never made --
    which is the failure the whole LLD section is about.
    """
    from doc_to_video_channel import planning_harness as ph

    def constant() -> tuple[bool, str]:
        return False, "the stub is constant: two calls produced identical responses"

    monkeypatch.setattr(ph, "self_test", constant)
    assert ph.main([]) == ph.EXIT_SELF_TEST_FAILED == 3
    assert "not runnable" not in capsys.readouterr().out


def test_an_unrunnable_tree_is_named_not_reported_as_a_pass(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from doc_to_video_channel import planning_harness as ph

    monkeypatch.setattr(
        ph, "plan_lesson_is_runnable", lambda: (False, "No module named 'x'")
    )
    assert ph.main([]) == ph.EXIT_CANNOT_RUN
    out = capsys.readouterr().out
    assert "No module named 'x'" in out, "the blocker must be named, not just refused"


def test_no_patched_binding_is_a_failure_not_a_pass(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Zero bindings patched means nothing was measured, and that is a FAILURE.

    Not exit 2: the tree is fine, the harness is broken. And not 0.
    """
    from doc_to_video_channel import planning_harness as ph

    monkeypatch.setattr(ph, "install_stub", list)
    assert ph.main([]) == ph.EXIT_FAILED == 1
    assert "nothing would be measured" in capsys.readouterr().out


def test_one_patched_binding_is_a_failure_because_narration_is_untested(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The trap the LLD says cost two review rounds, made executable.

    Patching only `plan` measures the plan chain and is blind to narration. That
    must be a failure, because a half-measured differential is worse than none: it
    reports a determinism result for a chain it never touched.
    """
    from doc_to_video_channel import planning_harness as ph

    monkeypatch.setattr(ph, "install_stub", lambda: ["plan"])
    assert ph.main([]) == ph.EXIT_FAILED
    assert "narration chain is untested" in capsys.readouterr().out


def test_both_bindings_patched_is_the_only_path_to_success(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The real tree, unpatched into a state where both bindings exist."""
    from doc_to_video_channel import planning_harness as ph

    assert ph.main([]) == ph.EXIT_OK == 0
    out = capsys.readouterr().out
    assert "'plan'" in out and "'narration'" in out


def test_every_exit_code_the_harness_can_return_is_distinct() -> None:
    """Four codes, four meanings, and no two may collide.

    A wrapper branches on the number; two branches sharing a number is the defect
    `publish` was withdrawn for, reproduced inside a helper.
    """
    from doc_to_video_channel import planning_harness as ph

    codes = [ph.EXIT_OK, ph.EXIT_FAILED, ph.EXIT_CANNOT_RUN, ph.EXIT_SELF_TEST_FAILED]
    assert len(set(codes)) == len(codes), f"colliding exit codes: {codes}"
