"""Phase 0 contract for the entry point.

Written WRONG-INPUT-FIRST per AGENTS.md rule 8: the negative cases below are the
ones that must fail, and each was confirmed to fail against the 66-byte stub
before `main` was given a body. The stub printed its greeting for every input
and exited 0, so all three of these are defects the gate could not previously
see.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from doc_to_video_channel import BUILT, EXIT_NOT_BUILT, EXIT_REFUSED, main

BOARD = Path(__file__).resolve().parents[1] / "storyboards" / "uv-install.storyboard.json"

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


#: The verbs still to build. `render` left this set at V7 and now takes a
#: STORYBOARD argument, so it is excluded here and covered by
#: `test_render_*` below. The list is derived from `BUILT` rather than written out,
#: so a verb cannot be left in a "not built" test after it has been built.
NOT_BUILT_VERBS = sorted(set(DECLARED_VERBS) - BUILT)


@pytest.mark.parametrize("verb", NOT_BUILT_VERBS)
def test_declared_verb_reports_not_built_distinctly(verb: str) -> None:
    """A declared-but-unbuilt verb exits 3, and says which verb it is.

    Exit 3 rather than 2 so a wrapper separates "does not exist" from "exists and
    refuses" on the number alone. Exit 2 here would make a not-yet-built verb
    indistinguishable from a typo.
    """
    result = run([verb])
    assert result.returncode == 3, f"{verb} exited {result.returncode}, expected 3"
    assert verb in result.stderr, f"message does not name the verb: {result.stderr!r}"


def test_a_built_verb_is_not_still_reported_as_not_built() -> None:
    """The check that catches a verb being built and left in the old contract.

    This test failed at V7 for exactly that reason: `render` had been wired but the
    parametrised test still asserted it exited 3, so the suite reported a green
    package whose own help text lied about one of its five verbs.
    """
    result = run(["render", "--help"])
    assert result.returncode == 0
    assert "declared but not built" not in result.stdout + result.stderr


def test_render_requires_a_storyboard_and_says_so() -> None:
    """A usage error stays argparse's 2. A verb that now takes an argument cannot
    accept a bare invocation and exit 3, because 3 would mean "unbuilt" and the verb
    IS built."""
    result = run(["render"])
    assert result.returncode == 2
    assert "STORYBOARD.json" in result.stderr


def test_render_refuses_a_missing_storyboard_with_four() -> None:
    """4, not 2 and not 3: the verb exists, the file does not, and the caller must
    be able to tell that from a typo without reading the message."""
    result = run(["render", "no-such-storyboard.json"])
    assert result.returncode == 4
    assert "no such storyboard" in result.stderr


def test_render_refuses_an_unshippable_storyboard_and_writes_nothing(
    tmp_path: Path,
) -> None:
    """THE DEFAULT IS A REFUSAL, and it writes nothing.

    `render_scenes` does not check provenance, so without this the build would emit a
    clean-looking lesson built on 7 unanchored scenes. Measured on the real
    storyboard: 1 of 8 scenes is anchored, so the default path refuses.
    """
    out = tmp_path / "out"
    result = run(["render", str(BOARD), "-o", str(out)])
    assert result.returncode == 4
    assert "REFUSED" in result.stderr
    assert not out.exists() or not any(out.rglob("*.png")), (
        "a refused render left frames behind for a later step to pick up"
    )


def test_render_can_be_forced_for_inspection(tmp_path: Path) -> None:
    """The override renders, and still says what it stepped over."""
    out = tmp_path / "out"
    result = run(["render", str(BOARD), "-o", str(out), "--allow-unshippable"])
    assert result.returncode == 0
    assert "for inspection only" in result.stderr
    assert "unanchored_scene" in result.stderr, "the override must still name the gaps"
    frames = sorted(out.rglob("*.png"))
    assert frames, "--allow-unshippable produced no frames"


def test_main_returns_the_same_code_in_process() -> None:
    """`main` is what `[project.scripts]` binds, so its return value is the code.

    The subprocess tests go through the generated console script; this one calls
    the bound symbol directly, so a re-pointed or renamed binding in
    `pyproject.toml` shows up here rather than as a mysterious green.
    """
    assert main(["verify"]) == 3


# --- in-process, so COVERAGE can see it ---------------------------------------
#
# The render tests above go through the console script in a subprocess, which is the
# right way to prove the binding works -- and the wrong way to measure it, because
# nothing the child process does reaches this process's coverage database. Measured:
# 41 of the 70 missed statements in this package's own code were `_run_render`, all
# of it exercised, none of it counted. So the same behaviour is checked again here,
# in process, and the reason is written down rather than left as a puzzle.


def test_render_refuses_unshippable_in_process(tmp_path: Path) -> None:
    assert main(["render", str(BOARD), "-o", str(tmp_path / "out")]) == 4
    assert not any((tmp_path / "out").rglob("*.png"))


def test_render_writes_frames_in_process(tmp_path: Path) -> None:
    code = main(["render", str(BOARD), "-o", str(tmp_path / "out"),
                 "--allow-unshippable"])
    assert code == 0
    # `board.id`, not the filename stem: the storyboard file is
    # `uv-install.storyboard.json` and its id is `uv-install`, so a test that
    # guessed the stem from the filename looks in the wrong directory.
    assert sorted((tmp_path / "out" / "uv-install").glob("*.png"))


def test_render_missing_storyboard_in_process(tmp_path: Path) -> None:
    assert main(["render", str(tmp_path / "nope.json")]) == 4


def test_render_refuses_a_storyboard_with_gaps(tmp_path: Path) -> None:
    """A storyboard that fails its own checks must not reach the renderer.

    The projection refuses an unshippable lesson; the storyboard's own `find_all`
    refuses a malformed one. Both are refusals and both are 4, so a caller sees one
    answer for "I will not build this" rather than two.
    """
    raw = json.loads(BOARD.read_text(encoding="utf-8"))
    raw["chapters"][0]["steps"][0].pop("common_failure")
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(raw), encoding="utf-8")
    out = tmp_path / "out"
    assert main(["render", str(broken), "-o", str(out), "--allow-unshippable"]) == 4
    assert not any(out.rglob("*.png"))


def test_every_exit_code_the_cli_can_return_is_distinct() -> None:
    """Four codes, four meanings, and no two may collide.

    Measured here rather than asserted in a comment: 0 built and shipped, 2
    argparse's usage error, 3 a declared verb this package has not built, 4 a verb
    that exists and refused. A wrapper branches on the number alone, so two branches
    sharing a number is the defect `publish` was withdrawn for, reproduced in the
    dispatcher.
    """
    codes = {0, 2, 3, 4}
    assert len(codes) == 4
    assert main(["verify"]) == 3
    assert main(["render", "no-such.json"]) == 4
    assert run(["nonsense"]).returncode == 2
    assert EXIT_REFUSED not in (EXIT_NOT_BUILT, 2)
