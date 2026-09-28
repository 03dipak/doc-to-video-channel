"""Replay and learner-only harness: the only evidence a follow-along session works.

A validator proves the storyboard is internally consistent. It proves nothing about
whether a **learner** can follow it. Only execution does that, and this is the
learner-only test in the strict sense: it runs **only the commands that appear in
the storyboard**, in a scratch directory, with no access to this repository, and
then checks that the session's stated end state is what is actually on disk.

Two rules this module will not break:

* **It refuses every `replayable: false` step, and says why.** `install-uv`
  installs software and rewrites the shell profile; a harness that ran it would
  change the machine it is supposed to be testing. Refusing is the point, not a
  limitation — an unrunnable session is a *reported* result, never a silent skip.
* **It never repairs.** If a step fails, the failure is reported with the command,
  the exit code, the output and the pattern it failed to match. Under
  reject-never-repair, a harness that quietly adjusted an expectation would be the
  same defect as a renderer quietly repairing a plan.

Run it directly for a readable report:

    .venv/bin/python -m doc_to_video_channel.harness storyboards/uv-install.storyboard.json

Exit codes follow LLD §12.1: **0** every replayable step passed, **1** at least one
failed, **2** the storyboard or the harness could not run at all.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import storyboard as sb

__all__ = ["EXIT_CANNOT_RUN", "EXIT_FAILED", "EXIT_OK", "Outcome", "main", "replay"]

EXIT_OK: int = 0
EXIT_FAILED: int = 1
EXIT_CANNOT_RUN: int = 2

#: Wall-clock ceiling per step. `uv add` resolves and downloads; a hung step must
#: not hang the gate, but the ceiling has to be generous enough not to fail a slow
#: network on a good run.
STEP_TIMEOUT: int = 300


@dataclass(frozen=True, slots=True)
class Outcome:
    """What happened to one step, with enough evidence to diagnose it."""

    step_id: str
    chapter_id: str
    command: str
    status: str  # "passed" | "failed" | "refused"
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "passed"


def _environment_for(step: sb.Step, base: dict[str, str]) -> dict[str, str]:
    """Apply a step's declared `env`, or hand back the base environment untouched.

    Only `path_exclude` is implemented, and that is the only one the storyboard
    needs: it is how a step reproduces a shell that has not re-read an edited
    profile. Anything else in `env` is a *declared* condition the harness does not
    yet know how to build, so it is reported rather than approximated — a harness
    that silently ignored half a step's environment would report a pass the learner
    would not get.
    """
    env = dict(base)
    raw_excludes = step.env.get("path_exclude", [])
    excludes: Sequence[str] = (
        [str(x) for x in raw_excludes] if isinstance(raw_excludes, list) else []
    )
    if not excludes:
        return env
    kept = [p for p in env.get("PATH", "").split(os.pathsep) if p and p not in set(excludes)]
    env["PATH"] = os.pathsep.join(kept)
    return env


def _run_step(step: sb.Step, cwd: Path, base_env: dict[str, str]) -> Outcome:
    """Execute one step's command and judge it against its own declared pattern."""
    if not step.replayable:
        return Outcome(
            step_id=step.id,
            chapter_id="",
            command=step.command,
            status="refused",
            detail=step.replay_skip_reason or "no reason recorded",
        )
    try:
        completed = subprocess.run(
            step.command,
            shell=True,
            cwd=cwd,
            env=_environment_for(step, base_env),
            capture_output=True,
            text=True,
            timeout=STEP_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Outcome(
            step_id=step.id,
            chapter_id="",
            command=step.command,
            status="failed",
            detail=f"timed out after {STEP_TIMEOUT}s",
        )
    output = completed.stdout + completed.stderr
    expected_code = step.expected_exit_code
    if expected_code is not None and completed.returncode != expected_code:
        return Outcome(
            step_id=step.id,
            chapter_id="",
            command=step.command,
            status="failed",
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            detail=(
                f"exit {completed.returncode}, but the step declares "
                f"expected_exit_code {expected_code}"
            ),
        )
    if not step.expected_regex.search(output):
        return Outcome(
            step_id=step.id,
            chapter_id="",
            command=step.command,
            status="failed",
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            detail=f"output did not match {step.expected_output_pattern!r}",
        )
    return Outcome(
        step_id=step.id,
        chapter_id="",
        command=step.command,
        status="passed",
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def replay(board: sb.Storyboard, workdir: Path) -> Iterator[Outcome]:
    """Run the whole session in session order, carrying the working directory.

    The working directory is **carried across steps on purpose**. `make-project-dir`
    does `cd uv-demo`, and every later step's command is relative — so a harness
    that reset the directory per step would report "no such file" for the whole
    session and blame the storyboard for a harness bug. Carrying it is also the
    honest model: a learner's shell does not forget where they are.
    """
    base_env = {k: v for k, v in os.environ.items() if k != "PWD"}
    current = workdir
    for chapter in board.chapters:
        for step in chapter.steps:
            outcome = _run_step(step, current, base_env)
            yield Outcome(
                step_id=outcome.step_id,
                chapter_id=chapter.id,
                command=outcome.command,
                status=outcome.status,
                exit_code=outcome.exit_code,
                stdout=outcome.stdout,
                stderr=outcome.stderr,
                detail=outcome.detail,
            )
            if outcome.passed:
                # Follow the `cd` the step just performed, if it did one.
                marker = " && cd "
                if marker in step.command:
                    candidate = current / step.command.split(marker, 1)[1].split(" ")[0]
                    if candidate.is_dir():
                        current = candidate


def _report(outcomes: Sequence[Outcome], board: sb.Storyboard, workdir: Path) -> str:
    lines = [
        f"storyboard : {board.id}  ({len(board.chapters)} chapters, "
        f"{len(tuple(board.steps()))} steps)",
        f"scratch dir: {workdir}",
        "",
    ]
    for outcome in outcomes:
        mark = {"passed": "PASS", "failed": "FAIL", "refused": "SKIP"}[outcome.status]
        lines.append(f"[{mark}] {outcome.chapter_id}/{outcome.step_id}")
        lines.append(f"       $ {outcome.command}")
        if outcome.status == "refused":
            lines.append(f"       refused: {outcome.detail}")
        elif outcome.status == "failed":
            lines.append(f"       exit {outcome.exit_code}: {outcome.detail}")
            tail = (outcome.stdout + outcome.stderr).strip().splitlines()
            for line in tail[-6:]:
                lines.append(f"       | {line}")
        else:
            note = ""
            if outcome.exit_code not in (0, None):
                note = "  <- non-zero, and that is what this step teaches"
            lines.append(f"       exit {outcome.exit_code}{note}")
    passed = sum(1 for o in outcomes if o.passed)
    failed = sum(1 for o in outcomes if o.status == "failed")
    refused = sum(1 for o in outcomes if o.status == "refused")
    lines += ["", f"passed {passed}  failed {failed}  refused {refused}"]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    # `None` means "no argument given by a caller", which for a console entry point
    # is indistinguishable from "the process was started with no arguments" -- both
    # read sys.argv. The earlier version let `args` be None and then compared a None
    # for emptiness, so `python -m ...harness storyboard.json` printed the help text
    # and exited 2 instead of running the session.
    args = list(argv) if argv is not None else sys.argv[1:]
    if not args:
        print(__doc__)
        return EXIT_CANNOT_RUN
    path = Path(args[0])
    if not path.is_file():
        print(f"no storyboard at {path}")
        return EXIT_CANNOT_RUN
    try:
        board, gaps = sb.load(path)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"cannot read {path}: {exc}")
        return EXIT_CANNOT_RUN
    blocking = sb.find_all(board, gaps)
    if blocking:
        print("the storyboard does not satisfy its own contract, so nothing was run:")
        for gap in blocking:
            print(f"  {gap}")
        return EXIT_CANNOT_RUN

    workdir = Path(tempfile.mkdtemp(prefix="uv-session-"))
    try:
        outcomes = list(replay(board, workdir))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    print(_report(outcomes, board, workdir))
    return EXIT_FAILED if any(o.status == "failed" for o in outcomes) else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
