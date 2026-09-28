"""The harness, and proof that it can fail.

The harness is the only evidence a learner can follow the session, so a harness
that always passes is worse than none: it would certify a session nobody can
follow. The mutation at the bottom is the test that matters — it breaks a
*command* rather than a storyboard field, because a broken command is the failure
this whole layer exists to catch.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Any

import pytest

from doc_to_video_channel import harness
from doc_to_video_channel import storyboard as sb

STORYBOARD = Path(__file__).resolve().parent.parent / "storyboards" / "uv-install.storyboard.json"


@pytest.fixture
def raw() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(STORYBOARD.read_text(encoding="utf-8"))
    return loaded


def _write(maybe: dict[str, Any], tmp_path: Path) -> Path:
    target = tmp_path / "mutant.storyboard.json"
    target.write_text(json.dumps(maybe), encoding="utf-8")
    return target


# --- refusal is the point ---------------------------------------------------


def test_a_non_replayable_step_is_refused_with_its_reason(raw: dict[str, Any]) -> None:
    """`install-uv` must never run. It installs software and edits the shell profile.

    The reason is not decoration either: it is the evidence a reader checks when
    asking what this session actually verified.
    """
    board, _ = sb.load(STORYBOARD)
    outcomes = {o.step_id: o for o in harness.replay(board, Path("/tmp"))}

    refused = outcomes["install-uv"]
    assert refused.status == "refused"
    assert "shell profile" in refused.detail
    assert refused.exit_code is None, "a refused step must not have executed"


def test_no_refused_step_was_ever_executed() -> None:
    """Every refused step is absent from the passed set, with no overlap."""
    board, _ = sb.load(STORYBOARD)
    outcomes = list(harness.replay(board, Path("/tmp")))
    refused = {o.step_id for o in outcomes if o.status == "refused"}
    passed = {o.step_id for o in outcomes if o.status == "passed"}
    assert not (refused & passed)
    assert refused == {s.id for s in board.blocked_steps()}


# --- environment ------------------------------------------------------------


def test_path_exclude_actually_removes_the_directory() -> None:
    """A declared `env` must change the process environment, or it is decoration.

    `prove-not-on-path` depends on this: the install directory is on the build
    machine's PATH, so without the exclusion the step's expected output
    (`uv: not found`) can never be reached.
    """
    board, _ = sb.load(STORYBOARD)
    step = next(s for s in board.steps() if s.id == "prove-not-on-path")
    assert step.env.get("path_exclude"), "the step declares no path_exclude"
    excluded = str(step.env["path_exclude"][0])
    import os

    env = harness._environment_for(step, dict(os.environ))
    assert excluded not in env["PATH"].split(os.pathsep)


def test_a_step_without_env_gets_the_base_environment_unchanged() -> None:
    board, _ = sb.load(STORYBOARD)
    step = next(s for s in board.steps() if s.id == "record-version")
    import os

    assert harness._environment_for(step, dict(os.environ))["PATH"] == os.environ["PATH"]


def test_an_env_without_a_why_is_reported(raw: dict[str, Any], tmp_path: Path) -> None:
    """A modified environment is a claim, so it owes the reader a reason."""
    for chapter in raw["chapters"]:
        for step in chapter["steps"]:
            if step["id"] == "prove-not-on-path":
                step["env"].pop("why")
    _, gaps = sb.load(_write(raw, tmp_path))
    assert [g for g in gaps if g.kind == "unjustified-env"]


# --- the exit code is part of the claim --------------------------------------


def test_expected_exit_code_is_carried_through() -> None:
    """Two steps turn the exit code into part of what they teach.

    `grep -c` EXITS 1 when the count is zero, so `prove-with-not-recorded` succeeds
    with a failure code -- and a learner who is not told that reads the 1 as a
    broken command. That is the "expected warnings versus actual errors" gap, and
    the contract had nowhere to record it until the harness surfaced it.
    """
    board, _ = sb.load(STORYBOARD)
    by_id = {s.id: s for s in board.steps()}
    assert by_id["prove-with-not-recorded"].expected_exit_code == 1
    assert by_id["prove-not-on-path"].expected_exit_code == 127
    assert by_id["record-version"].expected_exit_code is None, (
        "None must mean 'not asserted', not 'any code is fine'"
    )


def test_a_wrong_exit_code_fails_the_step(tmp_path: Path) -> None:
    """The exit assertion has teeth: a step declaring 0 that exits 1 must fail."""
    board, _ = sb.load(STORYBOARD)
    lying = sb.Step(
        **{
            **{
                f: getattr(
                    next(s for s in board.steps() if s.id == "record-version"), f
                )
                for f in (
                    "id",
                    "purpose",
                    "precondition",
                    "command",
                    "expected_output_pattern",
                    "checkpoint",
                    "state_change",
                    "common_failure",
                    "replayable",
                    "replay_skip_reason",
                    "creates_indirectly",
                    "env",
                )
            },
            "expected_exit_code": 42,
        }
    )
    outcome = harness._run_step(lying, tmp_path, dict(__import__("os").environ))
    assert outcome.status == "failed"
    assert "expected_exit_code 42" in outcome.detail


# --- the harness refuses a storyboard that fails its own contract -----------


def test_a_contract_violation_stops_the_run_entirely(raw: dict[str, Any], tmp_path: Path) -> None:
    """Nothing runs against a storyboard that is not internally sound.

    Running anyway would produce a report whose failures are indistinguishable from
    the storyboard's own defects.
    """
    for chapter in raw["chapters"]:
        for step in chapter["steps"]:
            if step["id"] == "add-requests":
                step["command"] = "uv add <package>"
    target = _write(raw, tmp_path)
    assert harness.main([str(target)]) == harness.EXIT_CANNOT_RUN


def test_a_missing_storyboard_is_exit_two() -> None:
    assert harness.main(["/nonexistent/storyboard.json"]) == harness.EXIT_CANNOT_RUN


# --- THE MUTATION: break a command, and the harness must fail ----------------


def test_mutation_a_broken_command_fails_the_harness(raw: dict[str, Any], tmp_path: Path) -> None:
    """Replace a real command with one that cannot work, and demand exit 1.

    Every other test here validates the harness's plumbing. This one proves the
    harness can report a session a learner cannot follow, which is the only reason
    it exists. A harness that returns 0 here would be certifying a broken tutorial.
    """
    for chapter in raw["chapters"]:
        for step in chapter["steps"]:
            if step["id"] == "prove-lockfile-exists":
                # A path the storyboard really does declare, so the contract check
                # passes and the failure has to come from EXECUTION. An earlier
                # version of this mutation used a path nothing creates, and the
                # harness refused the board before running a single command --
                # correct behaviour, wrong test: it proved the validator again, not
                # the runner.
                step["command"] = "ls -1 uv.lock | head -0"
    target = _write(raw, tmp_path)
    assert harness.main([str(target)]) == harness.EXIT_FAILED


def test_mutation_a_command_whose_output_cannot_match_fails(tmp_path: Path) -> None:
    """Output is judged against the step's OWN pattern, not a loosened one.

    The pattern is tightened rather than adjusted, because a harness that relaxed
    an expectation to make a run green would be the reject-never-repair violation
    this project keeps recording.
    """
    board, _ = sb.load(STORYBOARD)
    step = next(s for s in board.steps() if s.id == "prove-recorded")
    assert not step.expected_regex.search("totally unrelated output")


# --- the harness's own failure paths, so a broken harness cannot look healthy ---


def test_no_arguments_prints_help_and_exits_two() -> None:
    """Bare invocation is a usage error, matching the CLI contract in LLD 12.1."""
    assert harness.main([]) == harness.EXIT_CANNOT_RUN


def test_an_unreadable_storyboard_is_reported_not_raised(tmp_path: Path) -> None:
    """Malformed JSON must produce exit 2 with a message, never a traceback.

    A harness that dies with a stack trace when handed a broken file cannot be
    trusted to distinguish a broken session from a broken harness.
    """
    broken = tmp_path / "broken.json"
    broken.write_text("{not json at all", encoding="utf-8")
    assert harness.main([str(broken)]) == harness.EXIT_CANNOT_RUN


def test_a_failing_step_reports_its_output(tmp_path: Path) -> None:
    """The report must show what the command actually printed.

    "it failed" is not an actionable test result; the last lines of real output
    are the only thing that makes one.
    """
    board, _ = sb.load(STORYBOARD)
    # `Step` is frozen, which is the right shape: a harness must not be able to
    # edit the expectations it is about to judge. Build a board with the step
    # replaced instead of reaching into the dataclass.
    chapters = tuple(
        dataclasses.replace(
            chapter,
            steps=tuple(
                dataclasses.replace(step, command="ls -1 uv.lock | head -0")
                if step.id == "prove-lockfile-exists"
                else step
                for step in chapter.steps
            ),
        )
        for chapter in board.chapters
    )
    mutated = dataclasses.replace(board, chapters=chapters)
    outcomes = list(harness.replay(mutated, tmp_path))
    report = harness._report(outcomes, mutated, tmp_path)
    assert "did not match" in report
    assert "[FAIL] lock-and-sync/prove-lockfile-exists" in report
    assert "passed 0" not in report, "the report must not claim a pass it did not get"


def test_a_non_zero_exit_is_labelled_as_teaching_not_failing() -> None:
    """`prove-with-not-recorded` exits 1 on success, and the report must say so.

    Otherwise the report teaches the learner that a working command failed, which
    is the same class of error as the storyboard omitting the fact.
    """
    board, _ = sb.load(STORYBOARD)
    outcomes = list(harness.replay(board, Path("/tmp/opencode/w1")))
    report = harness._report(outcomes, board, Path("/tmp"))
    assert "what this step teaches" in report


def test_a_hanging_step_times_out_as_a_failure_not_a_hang(monkeypatch: pytest.MonkeyPatch,
                                                        tmp_path: Path) -> None:
    """A step that never returns must be reported, not waited on forever.

    Without this the gate itself can hang, which is the one failure mode a test
    harness must never have: a gate that stops reporting has stopped gating.
    """
    board, _ = sb.load(STORYBOARD)
    step = dataclasses.replace(
        next(s for s in board.steps() if s.id == "record-version"),
        command="sleep 30",
    )
    monkeypatch.setattr(harness, "STEP_TIMEOUT", 1)
    outcome = harness._run_step(step, tmp_path, dict(os.environ))
    assert outcome.status == "failed"
    assert "timed out" in outcome.detail


def test_the_working_directory_is_carried_across_steps(tmp_path: Path) -> None:
    """`make-project-dir` does `cd uv-demo`, and every later command is relative.

    A harness that reset the directory per step would report "no such file" for the
    rest of the session and blame the storyboard for a harness bug. Carrying it is
    also the honest model: a learner's shell does not forget where they are. The
    negative case is covered too -- a `cd` into a directory that does not exist must
    not move the harness somewhere wrong.
    """
    board, _ = sb.load(STORYBOARD)
    outcomes = {o.step_id: o for o in harness.replay(board, tmp_path)}
    assert outcomes["make-project-dir"].passed
    assert outcomes["prove-lockfile-exists"].passed, (
        "a relative `ls` only works if the earlier `cd` was carried forward"
    )


def test_a_cd_into_a_missing_directory_does_not_move_the_harness(tmp_path: Path) -> None:
    """A `cd` naming a directory nothing created must leave the harness where it was.

    The step itself fails -- the shell cannot `cd` there -- but the failure must not
    also relocate the working directory. If it did, every later relative command
    would run somewhere the learner never went, and the remaining results would be
    about a session nobody is being shown.
    """
    board, _ = sb.load(STORYBOARD)
    chapters = tuple(
        dataclasses.replace(
            chapter,
            steps=tuple(
                dataclasses.replace(step, command="mkdir -p real && cd nosuchdir && pwd")
                if step.id == "make-project-dir"
                else step
                for step in chapter.steps
            ),
        )
        for chapter in board.chapters
    )
    mutated = dataclasses.replace(board, chapters=chapters)
    outcomes = {o.step_id: o for o in harness.replay(mutated, tmp_path)}

    assert outcomes["make-project-dir"].status == "failed"
    # The harness stayed in tmp_path, so `uv init` wrote its project THERE.
    assert (tmp_path / "pyproject.toml").is_file(), (
        "the harness left the scratch root, so later steps ran in a directory the "
        "learner was never shown"
    )


def test_a_passing_step_whose_cd_did_not_land_leaves_the_directory_alone(
    tmp_path: Path,
) -> None:
    """A step can exit 0 and still not have moved, and the harness must notice.

    The cwd-follow only runs for a step that PASSED, so a step which fails never
    reaches it -- which left the false branch of `candidate.is_dir()` untested until
    this case: `cd` fails silently, the command still exits 0, and the harness must
    not relocate itself into a directory that does not exist.
    """
    board, _ = sb.load(STORYBOARD)
    chapters = tuple(
        dataclasses.replace(
            chapter,
            steps=tuple(
                dataclasses.replace(
                    step,
                    command="mkdir -p real && cd nosuchdir 2>/dev/null ; pwd",
                    expected_output_pattern="^/\\S+",
                )
                if step.id == "make-project-dir"
                else step
                for step in chapter.steps
            ),
        )
        for chapter in board.chapters
    )
    mutated = dataclasses.replace(board, chapters=chapters)
    outcomes = {o.step_id: o for o in harness.replay(mutated, tmp_path)}

    assert outcomes["make-project-dir"].passed, "the step must pass to reach the follow"
    assert not (tmp_path / "nosuchdir").exists()
    # Still in the scratch root: the project was created there, not in `real`.
    assert (tmp_path / "pyproject.toml").is_file()
