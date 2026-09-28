"""The storyboard contract, and proof that the contract can fail.

The tests below are written in the order `AGENTS.md` rule 8 requires: the wrong
input first, confirmed to fail, before the right input is asserted. The four
`test_mutation_*` cases exist for one reason -- a validator that has only ever
been shown a true statement is untested, and this project's own first teeth-check
was vacuous because it named a file neither tool discovered. Each mutation
therefore removes something from the real storyboard and asserts the matching gap
appears by name.

These tests validate the *artifact*. They do not execute the commands: execution
is `harness.py`, and it refuses every step marked `replayable: false`.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from doc_to_video_channel import storyboard as sb

STORYBOARD = Path(__file__).resolve().parent.parent / "storyboards" / "uv-install.storyboard.json"


@pytest.fixture
def raw() -> dict[str, Any]:
    return json.loads(STORYBOARD.read_text(encoding="utf-8"))


def _load(maybe_mutated: dict[str, Any], tmp_path: Path) -> tuple[sb.Storyboard, list[sb.Gap]]:
    target = tmp_path / "mutant.storyboard.json"
    target.write_text(json.dumps(maybe_mutated), encoding="utf-8")
    return sb.load(target)


def _step(board: dict[str, Any], chapter_id: str, step_id: str) -> dict[str, Any]:
    for chapter in board["chapters"]:
        if chapter["id"] == chapter_id:
            for step in chapter["steps"]:
                if step["id"] == step_id:
                    return step
    raise AssertionError(f"no step {chapter_id}/{step_id} in the storyboard")


# --- the real artifact is clean ---------------------------------------------


def test_shipped_storyboard_has_no_gaps() -> None:
    """The storyboard as committed satisfies its own contract.

    If this fails, the contract and the storyboard have drifted apart, and one of
    them is wrong. Read which before editing either.
    """
    board, gaps = sb.load(STORYBOARD)
    found = sb.find_all(board, gaps)
    assert found == [], "\n".join(str(g) for g in found)


def test_every_step_declares_all_six_contract_fields() -> None:
    """Six fields, not five, and not "most of them".

    `expected_output_pattern` counts as one of the six alongside command,
    precondition, checkpoint, state_change and common_failure.
    """
    board, _ = sb.load(STORYBOARD)
    required = set(sb.required_fields())
    for step in board.steps():
        for field in required:
            value = getattr(step, field, "")
            assert value.strip(), f"{step.id}: `{field}` is blank"


def test_commands_are_copyable_verbatim() -> None:
    """No ellipsis, no placeholder, no shell variable, no TODO.

    A learner pastes the command as shown, so a token only the author can expand
    is a gap that looks like a complete command.
    """
    board, _ = sb.load(STORYBOARD)
    assert sb.find_elisions(board) == []


def test_every_path_used_is_created_or_declared() -> None:
    """The learner-only property, checked statically.

    Every path a command touches must be produced by an earlier step, created by
    this step, or declared in a precondition. This is what stops the video
    depending on state the learner never saw.
    """
    board, _ = sb.load(STORYBOARD)
    assert sb.find_unshown_state_dependencies(board) == []


# --- the four mutations ------------------------------------------------------


def test_mutation_removing_a_creating_step_is_caught(
    raw: dict[str, Any], tmp_path: Path
) -> None:
    """Delete the step that makes `src/main.py`, and `run-main` must be flagged.

    This is the highest-value mutation in the file. It is the exact defect the
    source document shipped with: a file that is run but never created. If this
    test ever passes on the mutated board, the state check is decorative.
    """
    mutated = copy.deepcopy(raw)
    chapter = next(c for c in mutated["chapters"] if c["id"] == "run-and-with")
    chapter["steps"] = [s for s in chapter["steps"] if s["id"] != "create-main"]

    board, gaps = _load(mutated, tmp_path)
    found = sb.find_unshown_state_dependencies(board)
    assert len(found) == 1, f"expected exactly one unshown-state gap, got {found}"
    assert found[0].kind == "unshown-state"
    assert found[0].where == "run-main"
    assert "src/main.py" in found[0].detail
    assert not [g for g in gaps if g.kind == "missing-field"]


def test_mutation_blanking_a_command_is_caught(
    raw: dict[str, Any], tmp_path: Path
) -> None:
    """A blank command is render-blocking, not a warning."""
    mutated = copy.deepcopy(raw)
    _step(mutated, "first-project", "init-project")["command"] = "   "

    _, gaps = _load(mutated, tmp_path)
    missing = [g for g in gaps if g.kind == "missing-field" and "`command`" in g.detail]
    assert missing, f"a blank command was not reported: {gaps}"
    assert missing[0].blocking


def test_mutation_eliding_a_command_is_caught(
    raw: dict[str, Any], tmp_path: Path
) -> None:
    """`uv add <package>` is the archetypal elision, and it must fail."""
    mutated = copy.deepcopy(raw)
    _step(mutated, "add-dependencies", "add-requests")["command"] = "uv add <package>"

    board, _ = _load(mutated, tmp_path)
    found = sb.find_elisions(board)
    assert len(found) == 1, f"expected one elision, got {found}"
    assert found[0].where == "add-requests"


def test_mutation_stripping_a_skip_reason_is_caught(
    raw: dict[str, Any], tmp_path: Path
) -> None:
    """`replayable: false` with no reason is a silent exemption.

    A step that opts out of the harness must say why, or the harness quietly stops
    covering part of the session and nobody notices.
    """
    mutated = copy.deepcopy(raw)
    _step(mutated, "install-and-verify", "install-uv")["replay_skip_reason"] = ""

    _, gaps = _load(mutated, tmp_path)
    unjustified = [g for g in gaps if g.kind == "unjustified-skip"]
    assert unjustified, f"an unjustified replay skip was not reported: {gaps}"


# --- the checks' own edge cases, found by running them -----------------------


def test_a_url_is_not_treated_as_a_local_path() -> None:
    """Regression: `https://astral.sh/uv/install.sh` is not a file on this machine.

    The first version of the path regex read the URL as `astral.sh/uv/install.sh`
    and reported every install step as depending on a nonexistent file.
    """
    assert sb._paths_in("curl -LsSf https://astral.sh/uv/install.sh | sh") == set()
    board, _ = sb.load(STORYBOARD)
    assert not [
        gap
        for gap in sb.find_unshown_state_dependencies(board)
        if "astral.sh" in gap.detail
    ]


def test_a_trailing_full_stop_is_not_part_of_the_path() -> None:
    """Regression: `Creates src/main.py.` must yield `src/main.py`.

    With the full stop kept, the creating step stopped registering the file and the
    state check reported a false gap against the very step that creates it -- a
    false NEGATIVE in a check whose only job is catching omissions.
    """
    assert sb._paths_in("Creates src/main.py.") == {"src/main.py"}


def test_a_declared_precondition_satisfies_the_state_check(tmp_path: Path) -> None:
    """A precondition is a legitimate way to declare that a path exists.

    Without this, the state check would have no way to express "this file is
    already here because I said so", and the only alternative would be to add a
    redundant creating step -- so the check would push authors toward noise.
    """
    mutated = copy.deepcopy(_load_raw())
    run = _step(mutated, "run-and-with", "run-main")
    run["precondition"] = "create-main has run. `src/main.py` already exists on disk."
    for chapter in mutated["chapters"]:
        if chapter["id"] == "run-and-with":
            chapter["steps"] = [s for s in chapter["steps"] if s["id"] != "create-main"]

    board, _ = _load(mutated, tmp_path)
    assert sb.find_unshown_state_dependencies(board) == []





def _load_raw() -> dict[str, Any]:
    return json.loads(STORYBOARD.read_text(encoding="utf-8"))
