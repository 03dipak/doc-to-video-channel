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
import re
import tempfile
from pathlib import Path
from typing import Any

import pytest

from doc_to_video_channel import storyboard as sb

STORYBOARD = Path(__file__).resolve().parent.parent / "storyboards" / "uv-install.storyboard.json"


@pytest.fixture
def raw() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(STORYBOARD.read_text(encoding="utf-8"))
    return loaded


def _load(maybe_mutated: dict[str, Any], tmp_path: Path) -> tuple[sb.Storyboard, list[sb.Gap]]:
    target = tmp_path / "mutant.storyboard.json"
    target.write_text(json.dumps(maybe_mutated), encoding="utf-8")
    board, gaps = sb.load(target)
    return board, gaps


def _step(board: dict[str, Any], chapter_id: str, step_id: str) -> dict[str, Any]:
    for chapter in board["chapters"]:
        if chapter["id"] == chapter_id:
            for step in chapter["steps"]:
                if step["id"] == step_id:
                    found: dict[str, Any] = step
                    return found
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
    loaded: dict[str, Any] = json.loads(STORYBOARD.read_text(encoding="utf-8"))
    return loaded


# --- behaviour verified in throwaway scripts, now permanent ------------------
#
# Each of these was checked by hand while building the module and appeared in no
# test. A verification that lives only in a scratch script protects nothing: it is
# not run by the gate, so it cannot fail the gate, and it is gone next week. These
# are the lines coverage reported as missed.


def test_a_gap_renders_its_own_severity() -> None:
    """`str(gap)` is the user interface of this module, and it carries the severity.

    Asserted on `.kind`/`.detail` everywhere else, which is why the renderer itself
    went uncovered until coverage was run.
    """
    blocking = sb.Gap("elision", "add-requests", "cannot be copied", blocking=True)
    warning = sb.Gap("missing-field", "c/goal", "blank", blocking=False)
    assert str(blocking).startswith("[BLOCKING elision] add-requests:")
    assert str(warning).startswith("[warning missing-field] c/goal:")


def test_expected_output_is_a_compilable_regex() -> None:
    """The `expected_regex` property, which is what the replay harness will use.

    Asserting only that the string is non-empty would not prove it compiles, and a
    pattern that fails to compile is a broken harness waiting for a storyboard.
    """
    board, _ = sb.load(STORYBOARD)
    compiled = [step.expected_regex for step in board.steps()]
    assert len(compiled) == len(tuple(board.steps()))
    for regex in compiled:
        assert isinstance(regex, re.Pattern)
    run = next(s for s in board.steps() if s.id == "record-version")
    assert run.expected_regex.match("uv 0.12.2 (x86_64-unknown-linux-gnu)")
    assert not run.expected_regex.match("not a version line")


def test_a_chapter_states_the_end_state_it_promises() -> None:
    board, _ = sb.load(STORYBOARD)
    for chapter in board.chapters:
        assert chapter.end_state == chapter.goal
        assert chapter.start_state.strip(), f"{chapter.id} has no start state"


def test_replayable_and_blocked_partition_every_step() -> None:
    """The harness relies on these two summing to the whole session.

    If a step were silently in neither, the harness would skip it and report clean.
    """
    board, _ = sb.load(STORYBOARD)
    total = len(tuple(board.steps()))
    assert len(board.replayable_steps()) + len(board.blocked_steps()) == total
    assert len(board.blocked_steps()) == 1
    skipped = board.blocked_steps()[0]
    assert skipped.id == "install-uv"
    assert skipped.replay_skip_reason.strip()


def test_a_file_that_is_not_a_storyboard_is_refused() -> None:
    """A missing `chapters` key raises, rather than producing an empty session.

    An empty board is the dangerous outcome: every check would pass and the harness
    would replay nothing while reporting success.
    """
    not_a_board = Path(tempfile.gettempdir()) / "not-a-storyboard.json"
    not_a_board.write_text('{"nope": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="no `chapters` key"):
        sb.load(not_a_board)


def test_a_redirect_creates_the_file_the_check_looks_for() -> None:
    """`> file` is how a step brings a path into existence, and it must be seen."""
    assert sb._produces("printf 'x' > src/main.py", "src/main.py")
    assert sb._produces("printf 'x' >> src/main.py", "src/main.py")
    assert sb._produces("mkdir -p src", "src")
    assert sb._produces("mkdir -p build src", "src")
    assert sb._produces("mkdir src/", "src")
    assert not sb._produces("cat src/main.py", "src/main.py")
    assert not sb._produces("rm -rf src", "src")


def test_paths_in_ignores_punctuation_only_tokens() -> None:
    """A token that is punctuation once trimmed must not become a path.

    `./` matches the path regex and then strips to nothing, so without the guard it
    would register a path named `./` that no file will ever satisfy -- and the state
    check would then refuse every step that touched a relative path.
    """
    # "./" trims to ".", which IS a real path -- the current directory -- so it is
    # kept. Only a bare "./" with nothing after it is punctuation.
    assert sb._paths_in("./ x") == {"."}
    assert sb._paths_in("a/.") == {"a"}
    assert sb._paths_in("y/,") == {"y"}
    assert sb._paths_in("...") == set()
    assert sb._paths_in("") == set()


def test_mkdir_whose_operands_do_not_match_keeps_scanning() -> None:
    """`mkdir` for something else must not stop the search, and must not match.

    The loop has to survive an operand that is not the path and go on to the next
    token, or a step that creates a directory and then writes a file inside it would
    be judged as creating neither.
    """
    assert not sb._produces("mkdir -p build", "src/main.py")
    assert sb._produces("mkdir -p build && printf x > src/main.py", "src/main.py")


# --- undelivered state: prose is not evidence --------------------------------
#
# A step whose command became `cat > /dev/null` while its prose still said "Creates
# src/main.py." SATISFIED the unshown-state check, because the next step
# legitimately declares that file in its precondition. These three tests are the
# reason `find_undelivered_state_changes` exists.


def test_mutation_prose_claims_creation_the_command_does_not_make(
    raw: dict[str, Any], tmp_path: Path
) -> None:
    """The gap the unshown-state check cannot see, and must not be asked to."""
    mutated = copy.deepcopy(raw)
    step = _step(mutated, "run-and-with", "create-main")
    step["command"] = "cat > /dev/null"
    step["creates_indirectly"] = ""

    board, _ = _load(mutated, tmp_path)
    assert sb.find_unshown_state_dependencies(board) == [], (
        "precondition made this invisible to the unshown-state check, which is why "
        "the separate undelivered check exists"
    )
    found = sb.find_undelivered_state_changes(board)
    assert found, "a step that promises a file and does not make one was not reported"
    assert any("src/main.py" in g.detail for g in found)


def test_dropping_an_indirect_declaration_is_caught(
    raw: dict[str, Any], tmp_path: Path
) -> None:
    """`uv init` really does create `pyproject.toml`, and the command cannot show it.

    That is why the field is a DECLARATION a human can falsify by reading, rather
    than a heuristic: inference produced 8 false positives on the real storyboard.
    Remove the declaration and the promise is unbacked again.
    """
    mutated = copy.deepcopy(raw)
    _step(mutated, "first-project", "init-project").pop("creates_indirectly")

    board, _ = _load(mutated, tmp_path)
    found = sb.find_undelivered_state_changes(board)
    assert found, "an unbacked promise was not reported"
    assert any("pyproject.toml" in g.detail for g in found)


def test_a_declaration_naming_the_wrong_file_is_caught(
    raw: dict[str, Any], tmp_path: Path
) -> None:
    """A declaration that does not name the promised file is not a declaration."""
    mutated = copy.deepcopy(raw)
    _step(mutated, "first-project", "init-project")["creates_indirectly"] = "requirements.txt"

    board, _ = _load(mutated, tmp_path)
    found = sb.find_undelivered_state_changes(board)
    assert found, "a wrong declaration was accepted"
    assert any("pyproject.toml" in g.detail for g in found)


def test_a_promise_nothing_depends_on_is_documentation_not_a_gap() -> None:
    """The check stays narrow on purpose, or it gets switched off.

    `show-requires-python` describes what `init-project` produced. That is
    documentation, and a check that fired on documentation would be a check an
    author turns off within a week.
    """
    board, _ = sb.load(STORYBOARD)
    for gap in sb.find_undelivered_state_changes(board):
        assert "README.md" not in gap.detail, "a documented promise was reported as a gap"
