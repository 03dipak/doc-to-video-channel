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
