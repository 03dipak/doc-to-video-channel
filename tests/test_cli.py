"""Phase 0 contract for the entry point.

Written WRONG-INPUT-FIRST per AGENTS.md rule 8: the negative cases below are the
ones that must fail, and each was confirmed to fail against the 66-byte stub
before `main` was given a body. The stub printed its greeting for every input
and exited 0, so all three of these are defects the gate could not previously
see.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from doc_to_video_channel import main

# The five verbs the CLI declares, and only these. `publish` was WITHDRAWN
# 2026-09-28 (LLD v010 §8.2): a verb nobody is obliged to run gates nothing, and
# a manifest-reading verb is `verify` under a second name. It must not reappear.
DECLARED_VERBS = ("build", "review", "tts-check", "verify", "render")

# A venv puts its console scripts beside its interpreter, so this is the script
# `pyproject.toml`'s `[project.scripts]` binding produced. Resolving it from
# `sys.executable` rather than trusting PATH is deliberate: the first version of
# this test called bare `doc-to-video-channel` and every case failed with
# `FileNotFoundError` before reaching its assertion -- three red tests proving
# only that PATH was wrong, which is not the contract under test.
SCRIPT = Path(sys.executable).with_name("doc-to-video-channel")


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the installed console script, not `main` in-process.

    `pyproject.toml` binds `doc-to-video-channel = "doc_to_video_channel:main"`,
    so the entry point is only real if the script reaches it. An in-process call
    cannot see a broken binding; this can.
    """
    assert SCRIPT.is_file(), (
        f"console script missing at {SCRIPT}: the [project.scripts] binding is "
        f"declared but not installed, so the CLI cannot be reached at all"
    )
    return subprocess.run(
        [str(SCRIPT), *argv],
        capture_output=True,
        text=True,
        check=False,
    )


# --- the three wrong inputs -------------------------------------------------


def test_unknown_verb_is_refused() -> None:
    """A verb that does not exist must exit non-zero, not exit 0.

    Against the stub this exited 0 and printed "Hello from
    doc-to-video-channel!" -- a silent zero, the failure class
    docs/scratch.md §1 records. `ruff` and `mypy` cannot see a CLI contract, so
    without this the gate passes over an entry point that accepts nonsense.
    """
    result = run(["not-a-verb"])
    assert result.returncode != 0, f"unknown verb exited 0; stdout={result.stdout!r}"


def test_withdrawn_publish_verb_does_not_exist() -> None:
    """`publish` was withdrawn, so it must be refused like any other unknown verb.

    This is the executable form of the mentor ruling: a test that fails if
    someone re-adds the verb is stronger than a paragraph saying not to.
    """
    assert "publish" not in DECLARED_VERBS
    result = run(["publish"])
    assert result.returncode != 0, f"withdrawn `publish` verb accepted: {result.stdout!r}"


def test_no_verb_is_refused() -> None:
    """Bare invocation must be a usage error, not a greeting and exit 0.

    A CLI with a required subcommand that succeeds when given none has no
    contract: the caller cannot tell "I forgot the verb" from "it worked".
    """
    result = run([])
    assert result.returncode != 0, f"bare invocation exited 0; stdout={result.stdout!r}"


# --- the positive cases, added only after the red above was credible ----------


def test_help_exits_zero_and_lists_every_declared_verb() -> None:
    """`--help` must succeed and print usage.

    P0-a's whole content. Against the stub this exited 0 too -- but printed
    "Hello from doc-to-video-channel!" -- which is why the exit code alone was
    never a sufficient assertion for any of these.
    """
    result = run(["--help"])
    assert result.returncode == 0
    for verb in DECLARED_VERBS:
        assert verb in result.stdout, f"usage omits declared verb {verb!r}"


def test_help_does_not_print_the_greeting() -> None:
    """The stub's output must be gone from every path.

    A 66-byte placeholder is a fine first commit and a permanent defect after
    the second: this asserts the string cannot return, which the exit-code tests
    cannot do.
    """
    for argv in (["--help"], ["build"], []):
        result = run(argv)
        assert "Hello from doc-to-video-channel" not in result.stdout + result.stderr


def test_usage_does_not_offer_the_withdrawn_verb() -> None:
    """`publish` must be absent from the verb list, not merely rejected.

    Rejecting it while still advertising it would be a help screen that lies.
    """
    result = run(["--help"])
    assert "publish" not in result.stdout


@pytest.mark.parametrize("verb", DECLARED_VERBS)
def test_declared_verb_reports_not_built_distinctly(verb: str) -> None:
    """A declared verb exits 3, and says which verb it is.

    Exit 3 rather than 2 so a wrapper separates "does not exist" from "exists
    and refuses" on the number alone. Exit 2 here would make a not-yet-built
    verb indistinguishable from a typo.
    """
    result = run([verb])
    assert result.returncode == 3, f"{verb} exited {result.returncode}, expected 3"
    assert verb in result.stderr, f"message does not name the verb: {result.stderr!r}"


def test_main_returns_the_same_code_in_process() -> None:
    """`main` is what `[project.scripts]` binds, so its return value is the code.

    The subprocess tests go through the generated console script; this one calls
    the bound symbol directly, so a re-pointed or renamed binding in
    `pyproject.toml` shows up here rather than as a mysterious green.
    """
    assert main(["verify"]) == 3
