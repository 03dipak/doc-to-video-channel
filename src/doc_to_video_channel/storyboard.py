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
    "find_undelivered_state_changes",
    "find_unshown_state_dependencies",
    "load",
    "required_fields",
    "spoken_command_trigrams",
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
    #: Filenames this step creates as a SIDE EFFECT of a tool, which a command
    #: cannot show: `uv init` writes `pyproject.toml` without naming it. Declared
    #: rather than inferred, because inference produced 8 false positives on the
    #: real storyboard. Empty string means "nothing indirect is claimed".
    creates_indirectly: str = ""

    #: Environment the harness must build to run this step faithfully. Found by
    #: building the harness: `prove-not-on-path` expects `uv: not found`, but uv IS
    #: on PATH on the build machine, so the step is unrunnable as written and
    #: nothing said so. `path_exclude` reproduces a shell that has not re-read an
    #: edited profile. `why` is required whenever anything is set, so a modified
    #: environment is a claim with a reason rather than a silent trick.
    env: dict[str, Any] = field(default_factory=dict)

    #: Expected process exit code, or None when the code is not part of the claim.
    #: Found by running the harness: two steps turned on the exit code as part of
    #: what they teach -- `grep -c` EXITS 1 when the count is zero, so
    #: prove-with-not-recorded "succeeds" with a failure code -- and the contract had
    #: nowhere to say so. None means "not asserted", never "any code is fine".
    expected_exit_code: int | None = None

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
        token = token.rstrip(".,;:").rstrip("/")
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
            step_env = _as_dict(s_raw.get("env"))
            # `env: {}` means "no special environment" and must not trip the check:
            # only a step that actually asks for something owes the reader a `why`.
            if step_env and not str(step_env.get("why", "")).strip():
                gaps.append(
                    Gap(
                        "unjustified-env",
                        where,
                        "`env` is set with no `why`, so a step can alter the "
                        "environment the learner is shown without saying what for",
                    )
                )
            if not replayable and not reason:
                gaps.append(
                    Gap(
                        "unjustified-skip",
                        where,
                        "`replayable: false` with no `replay_skip_reason`, so nothing "
                        "says why this step is exempt from the harness",
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
                    creates_indirectly=str(s_raw.get("creates_indirectly", "")),
                    env=step_env,
                    expected_exit_code=(
                        s_raw["expected_exit_code"]
                        if isinstance(s_raw.get("expected_exit_code"), int)
                        else None
                    ),
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
        # A path the step itself creates is fine: it is shown being made. Note the
        # asymmetry, which is deliberate -- a `state_change` promise may satisfy a
        # LATER step (it is registered into `known` below), but it may not satisfy
        # THIS step. Prose is a claim, and a claim is not evidence. See
        # `find_undelivered_state_changes` for the check on the claims themselves.
        for path in sorted(referenced - known):
            if _produces(step.command, path):
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
    """True when the command itself brings `path` into existence.

    Two forms: a shell redirect, and `mkdir`. The `mkdir` form was DEAD until a
    test caught it -- the first version tested `token.startswith("-p ")`, but
    `mkdir -p src` splits into the tokens `mkdir`, `-p`, `src`, so no token ever
    contains a space and the branch could not fire. That is the worst shape of bug
    in a validator: it reads as if `mkdir` is handled, it is not, and nothing says
    so.
    """
    tokens = command.split()
    for index, token in enumerate(tokens):
        follows_redirect = token in {">", ">>"} and index + 1 < len(tokens)
        if follows_redirect and tokens[index + 1].rstrip("'\"").endswith(path):
            return True
        if token == "mkdir":
            for operand in tokens[index + 1 :]:
                if operand.rstrip("/").rstrip("'\"").endswith(path):
                    return True
    return False



_FLAG_WORDS: Final = {"-": "dash", "--": "dash dash"}


def spoken_command_trigrams(command: str) -> list[str]:
    """Every 3-gram inside a command's SPOKEN form, for use as protected terminology.

    **This is the mechanism for LLD 12.6 (finding F1).** The trigram repeat gate
    forbids a repeated 3-word phrase. Naming a command three times, as a practical
    session must, produces three repeated 3-grams -- measured on the V-1 spike:
    `run uv dash` x3, `uv dash dash` x3, `dash dash version` x3. Satisfying the gate
    instead produced "try that same check once more", which a learner LISTENING
    rather than looking cannot act on. The gate was right that the prose repeated
    and wrong about what to do about it.

    The resolution: a follow-along video must repeat its commands verbatim, so the
    trigrams **inside a spoken command** are protected terminology, exactly as
    source-derived terminology already is. What stays banned is repeated *prose*
    around the command -- which is the repetition a listener actually notices.

    A flag is spelled the way TTS says it: `--version` becomes `dash dash version`,
    so the protected span matches the narration rather than the source text. That
    matters, and it is the whole reason this is not a string search over the
    command.
    """
    spoken: list[str] = []
    for raw in command.split():
        if raw.startswith("--"):
            spoken.extend(["dash", "dash", raw[2:]])
        elif raw.startswith("-"):
            spoken.extend(["dash", raw[1:]])
        else:
            spoken.append(raw)
    tokens = [w for w in re.findall(r"[A-Za-z0-9_]+", " ".join(spoken).lower()) if w]
    return [" ".join(tokens[i : i + 3]) for i in range(max(0, len(tokens) - 2))]

def find_undelivered_state_changes(board: Storyboard) -> list[Gap]:
    """Promised state the command cannot be shown to deliver.

    `state_change` is prose, and prose is what a model-written plan gets wrong. A
    step whose command became `cat > /dev/null` while its prose still said "Creates
    src/main.py." SATISFIES the unshown-state check, because the next step
    legitimately declares that file in its precondition -- so without this check a
    video could show a step claiming to create a file it never makes and every
    other check would report clean.

    **This deliberately does not infer tool side effects.** A first version tried,
    and it fired on all 8 real promises in the storyboard -- every one a false
    positive -- because `uv init` and `uv add` create `pyproject.toml` and `uv.lock`
    without either filename appearing in the command. Only a redirect and `mkdir`
    are visible in a command; the rest is the tool's business. A check that cannot
    tell a tool's side effect from an omission is worse than none: it cries wolf
    eight times and then gets switched off.

    So indirect creation is DECLARED, in `creates_indirectly`. A promise with neither
    a visible producer nor a declaration is reported, but only when a later step
    actually depends on it -- a promise nothing uses is documentation, and a check
    that fires on documentation is a check that gets disabled.
    """
    gaps: list[Gap] = []
    for step in board.steps():
        promised = _paths_in(step.state_change)
        if not promised:
            continue
        visible = {p for p in _paths_in(step.command) if _produces(step.command, p)}
        declared = _paths_in(step.creates_indirectly)
        for path in sorted(promised - visible - declared):
            depended_on = any(
                path in _paths_in(other.command) for other in board.steps() if other is not step
            )
            if not depended_on:
                continue
            gaps.append(
                Gap(
                    "undelivered-state",
                    step.id,
                    f"`state_change` promises `{path}`, the command does not visibly create "
                    f"it, and `creates_indirectly` does not name what does -- so a later step "
                    f"depends on a file this step only claims to make",
                )
            )
    return gaps


def find_all(board: Storyboard, gaps: Sequence[Gap] = ()) -> list[Gap]:
    """Every check, in one call, so a caller cannot run a subset by accident."""
    return [
        *gaps,
        *find_elisions(board),
        *find_unshown_state_dependencies(board),
        *find_undelivered_state_changes(board),
    ]
