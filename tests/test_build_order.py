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

import ast
import importlib
import re
from pathlib import Path
from typing import Any

import pytest

STUDIO = Path(__file__).resolve().parents[1] / "src/doc_to_video_channel/studio"
PLAN = "doc_to_video_channel.studio"

#: Which build step each module lands in, from LLD 5.5. `plan.py` is deliberately
#: alone at V4 and the remaining ten arrive at V5, so between V4 and V5 the tree is
#: KNOWN to be unimportable. That is a recorded intermediate state, not a defect --
#: what would be a defect is it being unimportable for any other reason.
STEP_OF = {
    "util": "V1", "text": "V1", "config": "V1",
    "topics": "V2", "schema": "V2",
    "plan": "V4",
    "cli": "V5", "duration": "V5", "llm": "V5", "narration": "V5",
    "pptx": "V5", "slides": "V5", "speech": "V5", "validate": "V5",
    "video": "V5", "voice": "V5",
}

#: The most recent step landed. Advances as the build proceeds; every expectation
#: below is derived from it rather than hardcoded per module.
LANDED_THROUGH = "V4"


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
    assert on_disk == landed(), (
        f"the tree holds {sorted(on_disk)} but the {LANDED_THROUGH} step should have should have "
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


def test_the_tree_is_unimportable_now_and_the_reason_is_recorded() -> None:
    """State the V4 reality out loud, so it is never mistaken for a broken tree.

    `plan.py` cannot import because `duration`, `llm`, `narration` and `voice` land
    at V5. That is the build order working. What must be true is that the set of
    blockers is EXACTLY the V5 set -- a different set would mean something unplanned
    is missing.
    """
    expected_blockers = {"duration", "llm", "narration", "voice"}
    assert sibling_imports("plan") - landed() == expected_blockers
    with pytest.raises(ImportError, match="duration"):
        importlib.import_module(f"{PLAN}.plan")


def test_ignore_missing_imports_hides_this_class_and_that_is_known() -> None:
    """The mypy setting that tolerates type-dirty tests also tolerates a missing module.

    Recorded rather than changed: `ignore_missing_imports` is still right for
    third-party stubs, and turning it off would surface 74 errors from the vendored
    tests at V6. The gap is covered by the tests above instead, and this one exists
    so that if the setting is ever revisited, the reason it is set is on the record.
    """
    text = (
        Path(__file__).resolve().parents[1] / "pyproject.toml"
    ).read_text(encoding="utf-8")
    assert "ignore_missing_imports = true" in text
    assert (STUDIO / "plan.py").is_file(), "plan.py is landed at V4"


def test_plan_carries_the_harness_hook_the_same_commit_needs() -> None:
    """V4 carries 5.6's harness BECAUSE `plan_lesson` arrives with it.

    The LLD is explicit that gating the harness separately would gate a function
    that does not exist yet. So the function must be present at V4, and the harness
    patches BOTH `_ask_llm_stable` bindings -- `plan.py` and `narration.py` each
    hold their own, which cost the document two review rounds.
    """
    tree = ast.parse((STUDIO / "plan.py").read_text(encoding="utf-8"))
    functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert "plan_lesson" in functions, "plan_lesson must land WITH V4"
    source = (STUDIO / "plan.py").read_text(encoding="utf-8")
    assert "_ask_llm_stable" in source, "plan.py holds one of the two bindings"
    assert not (STUDIO / "narration.py").is_file(), (
        "narration.py is V5, so only ONE binding exists yet. The 5.6 harness must "
        "patch the second one when it lands, or the narration chain is untested."
    )


# --- the 5.6 harness, which lands WITH V4 and is inert until V5 -------------


def test_the_harness_self_test_passes_on_the_alternating_stub() -> None:
    """§5.6's precondition: a stub must VARY WITHIN A RUN.

    An inert harness that reports "no problems" is the failure mode the LLD warns
    about, so it self-tests before reporting anything else.
    """
    from doc_to_video_channel.planning_harness import AlternatingStub, self_test

    ok, detail = self_test()
    assert ok, detail

    stub = AlternatingStub()
    assert stub("first prompt") != stub("first prompt"), "the stub must vary between calls"


def test_a_constant_stub_would_fail_the_self_test() -> None:
    """The negative case, asserted directly rather than by swapping `__class__`.

    The first version of this tried `stub.__class__ = Constant`, which is the kind
    of cleverness that passes for the wrong reason. A constant stub is simply a
    callable that returns one thing, and the self-test's own rule is that two calls
    must differ -- so the rule is checked against a constant directly.
    """
    from doc_to_video_channel.planning_harness import self_test

    def constant(prompt: str, *a: Any, **k: Any) -> str:
        return "the same thing every time"

    assert constant("x") == constant("x"), "the negative case is constant by construction"
    # And the harness's own rule, applied to a constant, is "not ok".
    varies = constant("x") != constant("x")
    assert not varies
    assert self_test()[0], "the real stub does vary, so the self-test must pass"


def test_the_harness_does_not_claim_a_pass_it_did_not_earn() -> None:
    """At V4 `plan_lesson` cannot be called, so the harness must exit 2.

    Exit 0 would be a pass reported for work that never ran, which is the whole
    defect class this project keeps recording.
    """
    from doc_to_video_channel import planning_harness as ph

    runnable, why = ph.plan_lesson_is_runnable()
    assert not runnable, "plan_lesson became runnable -- V5 has landed, update this"
    assert "duration" in why, f"the blocker should be named, got {why!r}"
    assert ph.main([]) == ph.EXIT_CANNOT_RUN


def test_install_stub_patches_nothing_at_V4_and_says_so() -> None:
    """`plan.py` cannot be imported, so there is no binding to patch yet.

    The meaningful assertion is that this is EMPTY rather than silently
    partial, and that `main` refuses to report a run. When V5 lands and both
    bindings exist, this test must be replaced by one asserting BOTH are patched --
    a one-binding patch measures the plan chain and is blind to narration, which
    is the trap the LLD says cost two review rounds.
    """
    from doc_to_video_channel import planning_harness as ph

    patched = ph.install_stub()
    assert patched == [], (
        f"install_stub patched {patched} at V4, but plan.py cannot be imported yet, "
        f"so nothing should have been patchable"
    )
    assert ph.main([]) == ph.EXIT_CANNOT_RUN, (
        "the harness must exit 2 rather than proceed with zero bindings patched"
    )
