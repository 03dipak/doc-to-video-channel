"""The V7 seam: project an executable storyboard onto the renderer's plan shape.

**Why this exists.** The renderer takes a `LessonPlan` -- scenes with narration,
bullets, a code snippet and `source_refs`. The channel's authored artefact is a
**storyboard**: chapters of steps, each with a purpose, a command, a checkpoint, a
state change and a named failure, plus a `provenance` block carrying citations
with their verbatim quotes. Before this module the two shapes had no meeting
point, which is why the storyboard could be *replayed* by the harness and never
*rendered*.

**Nothing here invents.** Every field of every scene is assembled from strings a
human or a cited document already put in the storyboard: a bullet is a
`checkpoint`, a `state_change` or a `common_failure` verbatim, the code snippet is
the `command` verbatim, and the narration is the purpose and checkpoint joined by
connectives that carry no content. `source_refs` come from matching a step's own
text against each citation's `verbatim` quote -- a scene whose steps match no
citation is reported as an **unanchored scene**, not quietly given a plausible
reference. That is the whole channel thesis in one function: a claim that cannot be
traced to a citation is a claim that does not ship.

**Scene grouping is deterministic, and it had to be.** Fifteen steps against
`AUTO_TRIM_MAX_SCENES = 12` will not fit one scene per step. The LLD records that
overflow trim is *deterministic* rather than a model decision, so grouping here is
arithmetic: distribute the scene budget across chapters proportionally, never below
one scene per chapter, and never merge steps from different chapters. The result is
reported so the number of scenes is never a claim without a population behind it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from .storyboard import Chapter, Citation, Step, Storyboard, spoken_command_trigrams

__all__ = [
    "Projection",
    "ProjectionGap",
    "project",
    "scene_budget",
]

#: `config.TARGET_MAX_SCENES`. One scene per step overflows this at 15 steps, so
#: the budget is the target and grouping is what brings the count under it.
TARGET_SCENES = 8

#: Steps inside a scene are joined with **punctuation, not words**.
#:
#: The first version used the connectives "First, " and " Then, ", on the reasoning
#: that they carry no content. Measured, they carried *repetition*: of the 7
#: narration repeats `guard_plan` reported on the real storyboard, **2 were caused by
#: these two strings** -- a scene that walks two steps gains "then prove the" as a
#: trigram, and several scenes gain the same one. A join that manufactures the
#: repetition the gate is looking for is not a neutral join. A full stop is
#: punctuation: it adds no token, so it cannot form a trigram, and two sentences
#: read as two sentences.
_STEP_JOIN = ". "


@dataclass(frozen=True)
class ProjectionGap:
    """One thing the storyboard does not say that the renderer needs."""

    kind: str
    where: str
    detail: str


@dataclass
class Projection:
    """The plan, and everything that stopped it being trustworthy."""

    plan: dict[str, Any]
    scenes: int
    steps: int
    unanchored: list[str] = field(default_factory=list)
    gaps: list[ProjectionGap] = field(default_factory=list)

    @property
    def shippable(self) -> bool:
        return not self.gaps and not self.unanchored


def scene_budget(total_steps: int, per_chapter: list[int],
                 target: int = TARGET_SCENES) -> list[int]:
    """Scenes to spend on each chapter, deterministically.

    Never below 1 for a chapter that has steps, never above the chapter's own step
    count, and the total never above `target`. The result sums to the number of
    scenes actually built, and `test_scene_budget_sums_to_the_scenes_built` holds it
    to that -- a budget that is computed and then not honoured is a stored claim.
    """
    if not per_chapter or total_steps <= 0:
        return []
    budget = min(target, total_steps)
    # Proportional with a floor of 1, then any shortfall is handed to the chapters
    # with the most steps, largest first, so the tie-break is a stated order rather
    # than whatever the dict iteration happened to be.
    raw = [max(1, math.floor(budget * n / total_steps)) for n in per_chapter]
    raw = [min(r, n) for r, n in zip(raw, per_chapter, strict=True)]
    while sum(raw) < budget:
        order = sorted(
            range(len(raw)), key=lambda i: (-per_chapter[i], i)
        )
        for i in order:
            if sum(raw) >= budget:
                break
            if raw[i] < per_chapter[i]:
                raw[i] += 1
    while sum(raw) > budget:
        order = sorted(range(len(raw)), key=lambda i: (raw[i], i))
        for i in order:
            if sum(raw) <= budget:
                break
            if raw[i] > 1:
                raw[i] -= 1
    return raw


def _step_text(step: Step) -> str:
    """Every authored field of a step, joined -- the haystack a citation is matched in."""
    return " ".join(
        str(getattr(step, name) or "")
        for name in ("purpose", "command", "checkpoint",
                     "state_change", "common_failure", "precondition")
    )


def _match_citations(
    subject: Step | Chapter, citations: Sequence[Citation]
) -> list[Citation]:
    """Citations whose `verbatim` quote appears in this step's own text.

    Matched on the quote, not on a hand-written `source_ref` field, because a
    hand-written reference is a claim about a citation and this is a check of one.
    A citation whose quote is not in the step supports nothing here, and is not
    attached.
    """
    haystack = _step_text(subject) if isinstance(subject, Step) else (
        f"{subject.title} {subject.goal}"
    )
    return [c for c in citations if c.verbatim.strip() and c.verbatim.strip() in haystack]


#: `schema.SlideScene.bullets` is `max_length=4`. Three steps contributing a
#: checkpoint, a state change and a failure each is nine, so the projection has to
#: choose -- and a choice that silently drops five of nine fields is a scene that
#: teaches less than the storyboard says it does.
BULLET_LIMIT = 4


def _bullets_for(steps: list[Step]) -> tuple[list[str], int]:
    """Up to `BULLET_LIMIT` bullets, verbatim, plus how many were dropped.

    A scene's bullets are the things a learner needs to trust a command: that it
    did something, what it changed, and what to do when it did not. Taken verbatim
    and never paraphrased, because a paraphrase is an unsourced claim.

    Selection is by **decision relevance**, in a stated order, not by taking the
    first four: the first step's checkpoint and state change are what the scene is
    for, then every later step's checkpoint so no command goes unmentioned, then
    the first step's failure. The dropped count is returned rather than discarded,
    because a cap that hides what it discarded reads as a scene with four bullets
    when it is a scene with nine fields and four slots.
    """
    candidates: list[str] = []

    def offer(text: str) -> None:
        clean = text.strip()
        if clean and clean not in candidates:
            candidates.append(clean)

    if steps:
        offer(steps[0].checkpoint)
        offer(steps[0].state_change)
    for step in steps[1:]:
        offer(step.checkpoint)
    if steps:
        offer(steps[0].common_failure)
    for step in steps[1:]:
        offer(step.state_change)
        offer(step.common_failure)
    kept = candidates[:BULLET_LIMIT]
    return kept, len(candidates) - len(kept)


def _narration_for(steps: list[Step]) -> str:
    """Purpose and checkpoint per step, joined by contentless connectives.

    Built from authored text only. The purpose says what the step is for and the
    checkpoint says how the learner knows; joining them with "First," / "Then,"
    adds rhythm without adding a fact, so every word still traces to the
    storyboard.
    """
    parts: list[str] = []
    for step in steps:
        purpose = str(step.purpose or "").strip()
        checkpoint = str(step.checkpoint or "").strip()
        if not purpose and not checkpoint:
            continue
        sentence = purpose if not checkpoint else f"{purpose} {checkpoint}"
        sentence = sentence.rstrip(".")
        if sentence:
            parts.append(sentence)
    return _STEP_JOIN.join(parts)


#: Chapter id -> the `config._SECTIONS` member that stands for it.
#:
#: Written out rather than derived, because the only honest derivation is "the
#: chapter's title, lowercased" -- and "run and borrow a package for one command" is
#: not a member of the vocabulary, and neither is its lower-cased form. The chapter's
#: *name* is prose; the section is the label the slide draws in the corner, and
#: conflating the two is what made the schema refuse all eight scenes.
#:
#: Every value here is a member of `config._SECTIONS`, which is now the single
#: vocabulary: `test_every_projected_section_is_a_schema_member` fails the moment one
#: of these stops being admitted.
CHAPTER_SECTIONS: dict[str, str] = {
    "install-and-verify": "install and verify",
    "first-project": "first project",
    "add-dependencies": "add a dependency",
    "lock-and-sync": "lock and sync",
    "run-and-with": "run and borrow",
}


def _section_for(chapter: Chapter) -> str:
    """The slide's corner label for a chapter, or empty when unmapped.

    Empty rather than a guess: `schema.SlideScene.section` is `SectionKind | None`
    and its own comment says a scene with no section is legitimate, most scenes not
    being section cards. An unmapped chapter therefore gets `None` and
    `guard_plan` reports it, which is the correct report -- better than a label
    borrowed from whichever chapter happened to sort first.
    """
    return CHAPTER_SECTIONS.get(chapter.id, "")


def _scene_title(steps: list[Step], chapter: Chapter) -> str:
    """What the scene does, from the first step's own purpose.

    Falls back to the chapter title only when no step states a purpose, and the
    guard will then complain that the title restates the section -- which is the
    correct complaint about a storyboard that gave nothing better.
    """
    for step in steps:
        purpose = str(step.purpose or "").strip()
        if purpose:
            words = purpose.rstrip(".").split()
            if len(words) > 9:
                return " ".join(words[:9])
            return purpose.rstrip(".")
    return chapter.title


def _topic_for(steps: list[Step], chapter: Chapter) -> str:
    """The scene's subject, assembled from the command's own words.

    `validate._scene_metadata_problems` requires a non-empty `topic` on every scene.
    It is derived mechanically -- the tool and the object the command acts on, read
    off the command and the step's purpose -- because a topic invented to satisfy a
    presence check is a label that describes nothing. `guard_plan` will still
    reject an empty one, which is the correct outcome for a step with no command
    and no purpose.
    """
    parts: list[str] = []
    for step in steps:
        command = str(step.command or "").strip()
        if command:
            tool = command.split()[0].lstrip("$").strip()
            if tool and tool not in parts:
                parts.append(tool)
        if len(parts) >= 2:
            break
    if parts:
        return " ".join(parts)
    for step in steps:
        purpose = str(step.purpose or "").strip()
        if purpose:
            return " ".join(purpose.rstrip(".").split()[:4])
    return chapter.title


def _code_for(steps: list[Step]) -> tuple[str, str]:
    """The scene's command and the context line above it.

    A scene that groups two steps shows the first command as the snippet and names
    the rest, because a code box holding two unrelated commands teaches neither.
    """
    commands = [str(s.command or "").strip() for s in steps if str(s.command or "").strip()]
    if not commands:
        return "", ""
    context = commands[0]
    context = commands[0]
    for extra in commands[1:]:
        context += f"\n# then: {extra}"
    return commands[0], context


def project(board: Storyboard, *, target_scenes: int = TARGET_SCENES) -> Projection:
    """Project the storyboard onto a `LessonPlan`.

    Returns the plan alongside every gap, so a caller cannot render half a
    projection believing it whole. `Projection.shippable` is the single question to
    ask before writing media.
    """
    # `board.citations`, not `board.provenance`. The first version read a
    # `provenance` attribute that does not exist on `Storyboard`, so `citations` was
    # always the empty list and every scene reported unanchored -- a trace check that
    # fails closed for the wrong reason and looks like a content problem. Read from
    # the field the loader actually populates.
    citations = list(board.citations)
    gaps: list[ProjectionGap] = []
    unanchored: list[str] = []

    chapters = list(board.chapters)
    per_chapter = [len(c.steps) for c in chapters]
    total_steps = sum(per_chapter)
    budget = scene_budget(total_steps, per_chapter, target=target_scenes)
    if not budget:
        return Projection(plan={}, scenes=0, steps=0,
                          gaps=[ProjectionGap("empty", board.id,
                                              "the storyboard has no steps to project")])

    scenes: list[dict[str, Any]] = []
    for chapter, scene_count in zip(chapters, budget, strict=True):
        if scene_count <= 0:
            continue
        groups = _split(chapter.steps, scene_count)
        for group in groups:
            scene = _scene(board, chapter, group, citations, gaps, unanchored)
            scenes.append(scene)

    takeaways = [
        str(t) for t in (getattr(board, "takeaways", None) or []) if str(t).strip()
    ]
    plan = {
        "title": board.title,
        "opening": _opening(board, chapters),
        "scenes": scenes,
        "takeaways": takeaways,
    }
    if not takeaways:
        gaps.append(ProjectionGap(
            "no_takeaways", board.id,
            "a lesson with no takeaway does not satisfy the channel contract, and "
            "nothing here can invent one",
        ))
    return Projection(plan=plan, scenes=len(scenes), steps=total_steps,
                      unanchored=unanchored, gaps=gaps)


def _split(steps: Sequence[Step], scene_count: int) -> list[list[Step]]:
    """Split a chapter's steps into `scene_count` contiguous groups.

    Contiguous, so a scene's steps stay in the order a learner does them, and
    balanced, so no scene carries three steps while its neighbour carries one.
    """
    if scene_count <= 0 or not steps:
        return []
    base, extra = divmod(len(steps), scene_count)
    groups: list[list[Step]] = []
    start = 0
    for i in range(scene_count):
        size = base + (1 if i < extra else 0)
        if size == 0:
            continue
        groups.append(list(steps[start:start + size]))
        start += size
    return groups


def _opening(board: Storyboard, chapters: list[Chapter]) -> str:
    """The session opening: the first chapter's stated **start state**.

    The first version used the first chapter's `goal` and was wrong. Measured: every
    chapter's `goal` is the state the chapter *ends* in -- "A shell where
    `uv --version` succeeds", "A recorded requirement, and a resolved lockfile" --
    so the opening announced the outcome of chapter one before the lesson started,
    and `guard_plan` correctly reported "opening drifted" because that sentence
    names no chapter topic.

    `start_state` is the state the learner is *in*, which is what an opening is for,
    and it is authored: "A Linux or macOS shell. `uv` is NOT installed. `curl` is
    present." Nothing here is written, and if the first chapter states no start
    state the opening is empty and the gap is reported -- an opening is the first
    thing a viewer reads, and an invented one is the least defensible sentence in
    the lesson.
    """
    for chapter in chapters:
        start = str(getattr(chapter, "start_state", "") or "").strip()
        if start:
            return start
    return ""


def _scene(board: Storyboard, chapter: Chapter, steps: list[Step],
           citations: Sequence[Citation], gaps: list[ProjectionGap],
           unanchored: list[str]) -> dict[str, Any]:
    """One scene, from one group of steps. Every field traces to the storyboard."""
    # The title must NOT restate the section, or `guard_plan` reports a placeholder
    # title -- and it is right to. `section` is the chapter title, so prefixing the
    # chapter onto the scene title repeats it verbatim. The scene is named by what
    # it does, taken from the step's own purpose.
    title = _scene_title(steps, chapter)
    section = _section_for(chapter)
    if not section:
        gaps.append(ProjectionGap(
            "unmapped_chapter", chapter.id,
            "no entry in CHAPTER_SECTIONS, so the scene carries no section label. "
            "It is reported rather than given a borrowed one",
        ))
    where = f"{chapter.id}/{steps[0].id or '?'}"
    snippet, context = _code_for(steps)
    bullets, dropped = _bullets_for(steps)
    if dropped:
        gaps.append(ProjectionGap(
            "bullets_dropped", where,
            f"{dropped} authored field(s) did not fit the {BULLET_LIMIT}-bullet "
            f"schema cap and were left out of the slide. They are not lost from the "
            f"storyboard, but a viewer does not see them",
        ))
    matched: list[Citation] = []
    for step in steps:
        matched.extend(_match_citations(step, citations))
    unique: dict[str, Citation] = {c.url or c.claim: c for c in matched}

    if not unique:
        unanchored.append(where)
        gaps.append(ProjectionGap(
            "unanchored_scene", where,
            "no citation's verbatim quote appears in this scene's steps, so its "
            "bullets and narration cannot be traced to the source document. It is "
            "not rendered rather than given a reference nobody checked",
        ))

    if not snippet:
        gaps.append(ProjectionGap("no_command", where,
                                  "a step with no command has no code snippet to show"))

    return {
        "title": title,
        "narration": _narration_for(steps),
        "bullets": bullets,
        "topic": _topic_for(steps, chapter),
        "steps": [],
        "code_snippet": snippet,
        "code_context": context,
        "section": _section_for(chapter),
        # `schema.SceneSourceRef` is a **string**, not an object: the schema is
        # `list[str]`, so a dict per ref is refused at validation. The locator goes
        # in the ref and the full citation -- claim, verbatim quote, both dates --
        # rides along under a channel-only key, so nothing traceable is lost to
        # satisfy a type. Found by building the plan, not by reading the schema.
        "source_refs": [c.url or c.claim for c in unique.values()],
        "_citations": [
            {"claim": c.claim, "url": c.url, "verbatim": c.verbatim,
             "page_date": c.page_date, "retrieved_on": c.retrieved_on}
            for c in unique.values()
        ],
        # The spoken form of every command is protected terminology, so the TTS and
        # the caption band cannot paraphrase a flag into something else.
        "_protected_trigrams": [
            tri for s in steps for tri in spoken_command_trigrams(str(s.command or ""))
        ],
        "_step_ids": [str(s.id) for s in steps],
    }
