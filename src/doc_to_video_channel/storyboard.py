"""The storyboard contract: the executable artifact a practical session is built from.

A **source document** says what the channel teaches. A **storyboard** says what the
video shows and what a learner who follows only the screen can actually do. Those
are different artifacts and conflating them is how a follow-along video ends up
depending on state the learner never saw -- the `src/main.py` that is run but never
created, the `cd` that is assumed but never shown.

This module is that contract. It is deliberately small and it is deliberately
strict, because a validator that has only ever seen a true statement is untested
(see `AGENTS.md`).

**The storyboard is the single source for two consumers** -- the renderer, and the
replay/learner-only harness. That is the whole reason it is a data file rather than
prose: if the harness parsed a transcript of the finished video it would be
testing the transcription, not the video, which is the drift class this project has
now caught four times.

Nothing here executes a command. Execution is `harness.py`'s job, and it refuses
every step marked `replayable: false` rather than installing software underneath a
test run.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

__all__ = [
    "ELISION_PATTERNS",
    "Gap",
    "Step",
    "Storyboard",
    "find_elisions",
    "find_unshown_state_dependencies",
    "load",
    "required_fields",
]

#: Tokens that make a command uncopyable. A learner pastes verbatim, so a literal
#: that only the author can expand is a silent gap: the command looks complete and
#: fails on the learner's machine. `$` is included because a shell variable is not
#: a value the learner can see, and the session is meant to be followed from a
#: cold start.
ELISION_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("an ellipsis", re.compile(r"\.\.\.")),
    ("an angle-bracket placeholder", re.compile(r"<[a-z][a-z0-9_-]*>")),
    ("a shell variable", re.compile(r"\$\{?\w")),
    ("a redaction marker", re.compile(r"\b(?:REDACTED|TODO|FIXME|XXX)\b")),
)

#: A path-looking token in a command or in a declared state change. Deliberately
#: narrow: it wants `uv.lock`, `src/main.py`, `~/.local/bin/uv`, and it must not
#: match a bare word or a glob that happens to contain a slash in prose.
_PATH_TOKEN: Final = re.compile(
    r"(?:~?[\w.-]+/)+[\w.*{}-]*|[\w-]+\.(?:md|toml|lock|py|json|txt|cfg|ini|sh)\b"
)

#: Fields without which a step cannot be rendered as a follow-along session.
#: Severity follows the reject-never-repair rule: a missing command or expected
#: output is render-blocking, a missing failure path is a warning.
_BLOCKING: Final = frozenset(
    {"purpose", "precondition", "command", "expected_output_pattern", "state_change"}
)
_WARNING: Final = frozenset({"checkpoint", "common_failure"})


@dataclass(frozen=True, slots=True)
class Gap:
    """One thing wrong with a storyboard, located well enough to fix."""

    kind: str
    where: str
    detail: str
    blocking: bool = True

    def __str__(self) -> str:
        tag = "BLOCKING" if self.blocking else "warning"
        return f"[{tag} {self.kind}] {self.where}: {self.detail}"


@dataclass(frozen=True, slots=True)
class Step:
    """One command, with everything a learner needs in order to trust it."""

    id: str
    purpose: str
    precondition: str
    command: str
    expected_output_pattern: str
    checkpoint: str
    state_change: str
    common_failure: str
    replayable: bool = True
    replay_skip_reason: str = ""

    @property
    def expected_regex(self) -> re.Pattern[str]:
        """The expected output as a regex, compiled once.

        Always a pattern and never a literal: the cited documentation references
        `uv 0.12.19` while this machine runs `0.12.2`, so a literal expectation
        would fail on both.
        """
        return re.compile(self.expected_output_pattern, re.MULTILINE)


@dataclass(frozen=True, slots=True)
class Chapter:
    """A chapter that works standalone, because each one states its start state."""

    id: str
    title: str
    start_state: str
    goal: str
    steps: tuple[Step, ...]

    @property
    def end_state(self) -> str:
        return self.goal


@dataclass(frozen=True, slots=True)
class Storyboard:
    """The whole session, plus the provenance that makes it honest."""

    id: str
    title: str
    source_document: str
    authored_by: str
    authored_on: str
    environment_of_record: str
    chapters: tuple[Chapter, ...] = field(default_factory=tuple)

    def steps(self) -> Iterator[Step]:
        for chapter in self.chapters:
            yield from chapter.steps

    def replayable_steps(self) -> tuple[Step, ...]:
        return tuple(s for s in self.steps() if s.replayable)

    def blocked_steps(self) -> tuple[Step, ...]:
        return tuple(s for s in self.steps() if not s.replayable)


def required_fields() -> dict[str, str]:
    """The contract, as a mapping of field -> severity, for docs and error text."""
    return {name: "blocking" for name in sorted(_BLOCKING)} | {
        name: "warning" for name in sorted(_WARNING)
    }


def _paths_in(text: str) -> set[str]:
    """Local paths mentioned in `text`.

    Three things this gets wrong if left naive, all three found by running it on a
    real storyboard rather than by reading it:

    * A trailing full stop is part of the token, so `Creates src/main.py.` yields
      `src/main.py.` and a step that *does* create the file looks like it does not.
      That is a false NEGATIVE in a check whose whole job is catching omissions, and
      it would have made this check quietly useless.
    * A URL is not a path. `https://astral.sh/uv/install.sh` must not read as
      `astral.sh/uv/install.sh`, or every install step is reported as depending on
      a file that does not exist.
    * `~` expansion aside, a bare directory such as `uv-demo` is a real path the
      learner must be in, so it stays.
    """
    found: set[str] = set()
    for match in _PATH_TOKEN.finditer(text):
        token = match.group(0)
        # Drop sentence punctuation, keeping interior dots (3.12, main.py).
        token = token.rstrip("/").rstrip(".,;:")
        if not token or "://" in text[max(0, match.start() - 8) : match.start() + 1]:
            continue
        found.add(token)
    return found


def _as_dict(value: object) -> dict[str, Any]:
    """Narrow an untrusted JSON value to a mapping, or to an empty one.

    `json.loads` hands back `Any`, and an `isinstance` guard inside a ternary does
    not narrow it -- mypy correctly refused `prov.get(...)` on a value it still
    believed could be `None`. Every level of an untrusted document gets narrowed
    through this instead of being trusted.
    """
    return value if isinstance(value, dict) else {}


def _require_str(
    raw: dict[str, Any], key: str, where: str, gaps: list[Gap], kind: str = "step"
) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        gaps.append(
            Gap(
                "missing-field",
                where,
                f"`{key}` is absent or blank, and a follow-along session cannot "
                f"render this {kind} without it",
                blocking=key in _BLOCKING,
            )
        )
        return ""
    return value


def load(path: Path) -> tuple[Storyboard, list[Gap]]:
    """Read a storyboard and return it with everything wrong with it.

    Returns gaps rather than raising, because a caller wants the full list. Raise
    only if the file is not a storyboard at all.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "chapters" not in raw:
        raise ValueError(f"{path} is not a storyboard: no `chapters` key")

    gaps: list[Gap] = []
    prov = _as_dict(raw.get("provenance"))
    env = _as_dict(prov.get("environment_of_record"))

    chapters: list[Chapter] = []
    for c_raw_value in raw.get("chapters") or []:
        c_raw = _as_dict(c_raw_value)
        c_id = str(c_raw.get("id", f"chapter-{len(chapters)}"))
        steps: list[Step] = []
        for s_value in c_raw.get("steps") or []:
            s_raw = _as_dict(s_value)
            s_id = str(s_raw.get("id", "step-?"))
            where = f"{c_id}/{s_id}"
            fields = {
                key: _require_str(s_raw, key, where, gaps)
                for key in sorted(_BLOCKING | _WARNING)
            }
            replayable = s_raw.get("replayable", True)
            reason = s_raw.get("replay_skip_reason", "")
            if not replayable and not reason:
                gaps.append(
                    Gap(
                        "unjustified-skip",
                        where,
                        "`replayable: false` with no `replay_skip_reason`, so nothing says why "
                        "this step is exempt from the harness",
                    )
                )
            steps.append(
                Step(
                    id=s_id,
                    purpose=fields["purpose"],
                    precondition=fields["precondition"],
                    command=fields["command"],
                    expected_output_pattern=fields["expected_output_pattern"],
                    checkpoint=fields["checkpoint"],
                    state_change=fields["state_change"],
                    common_failure=fields["common_failure"],
                    replayable=bool(replayable),
                    replay_skip_reason=str(reason),
                )
            )
        chapters.append(
            Chapter(
                id=c_id,
                title=_require_str(c_raw, "title", c_id, gaps, kind="chapter"),
                start_state=_require_str(c_raw, "start_state", c_id, gaps, kind="chapter"),
                goal=_require_str(c_raw, "goal", c_id, gaps, kind="chapter"),
                steps=tuple(steps),
            )
        )

    board = Storyboard(
        id=str(raw.get("id", path.stem)),
        title=str(raw.get("title", "")),
        source_document=str(prov.get("source_document", "")),
        authored_by=str(prov.get("authored_by", "")),
        authored_on=str(prov.get("authored_on", "")),
        environment_of_record=str(env.get("uv", "")),
        chapters=tuple(chapters),
    )
    return board, gaps


def find_elisions(board: Storyboard) -> list[Gap]:
    """Commands a learner cannot paste verbatim.

    Render-blocking, because an elided command *looks* complete. The learner only
    finds out at the terminal, by which point they have lost the thread.
    """
    found: list[Gap] = []
    for step in board.steps():
        for label, pattern in ELISION_PATTERNS:
            if pattern.search(step.command):
                found.append(
                    Gap(
                        "elision",
                        step.id,
                        f"command contains {label}, so it cannot be copied and run as shown: "
                        f"{step.command!r}",
                    )
                )
    return found


def find_unshown_state_dependencies(board: Storyboard) -> list[Gap]:
    """Paths a step touches that no earlier step created and no precondition declares.

    This is the check that catches the two gaps measured in the source document: a
    `src/main.py` that is run but never created, and a working directory that drifts
    because no `cd` is ever shown.

    It walks the steps in session order and carries a running set of paths that are
    known to exist, seeded from each step's own `precondition` -- because a
    precondition is a *declaration* that the path exists, and a declaration is a
    legitimate way to satisfy this check. What it does not accept is a path that
    simply appears in a command with nothing behind it.
    """
    found: list[Gap] = []
    known: set[str] = set()
    for step in board.steps():
        declared = _paths_in(step.precondition)
        known |= declared
        # `expected_output_pattern` is deliberately NOT scanned. It is what a step
        # PRINTS, so scanning it for a path that must pre-exist reports every
        # checkpoint as an unshown dependency -- and a checkpoint is precisely the
        # thing whose job is to name a path the learner should now see. The command
        # is where a read happens, and a read is what needs a producer.
        referenced = _paths_in(step.command)
        for path in sorted(referenced - known):
            # A path the step itself creates is fine: it is shown being made.
            if path in _paths_in(step.command) and _produces(step.command, path):
                continue
            if path in _paths_in(step.state_change):
                continue
            found.append(
                Gap(
                    "unshown-state",
                    step.id,
                    f"`{path}` is used but no earlier step creates it and this step's "
                    f"precondition does not declare it, so a learner following only the "
                    f"screen hits a path that does not exist",
                )
            )
        known |= _paths_in(step.state_change)
    return found


def _produces(command: str, path: str) -> bool:
    """True when the command itself brings `path` into existence."""
    tokens = command.split()
    for index, token in enumerate(tokens):
        follows_redirect = token in {">", ">>"} and index + 1 < len(tokens)
        if follows_redirect and tokens[index + 1].rstrip("'\"").endswith(path):
            return True
        if token.startswith("-p ") and token.endswith(path):
            return True
    return False


def find_all(board: Storyboard, gaps: Sequence[Gap] = ()) -> list[Gap]:
    """Every check, in one call, so a caller cannot run a subset by accident."""
    return [*gaps, *find_elisions(board), *find_unshown_state_dependencies(board)]
