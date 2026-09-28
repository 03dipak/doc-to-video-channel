"""doc-to-video-channel: narrated, source-traceable tutorial videos.

Phase 0. This module is the package's ONLY build entry point
(`docs/PLAN-tutorial-lane.md` P0-d). The baseline keeps a second, deprecated
console-script shim; that second path is deliberately not reproduced here, so
there is one way in and not two that can drift.

Scope of this file is Phase 0 only: a real argument parser, so that a wrong
input fails loudly instead of exiting 0 with a greeting. The five verbs are
DECLARED -- their names are fixed by `docs/LLD-tutorial-lane.md` -- and none is
BUILT. A declared verb reports exit code 3; a usage error is argparse's 2. The
distinction is the same one the mentor ruling on `write_media` rests on: a
wrapper must be able to tell "you asked for something that does not exist" from
"that exists and refused you" without parsing message text.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

__all__ = ["EXIT_NOT_BUILT", "EXIT_REFUSED", "VERBS", "build_parser", "main"]

PROG = "doc-to-video-channel"

#: A verb this package declares but has not built yet. Distinct from argparse's
#: 2 (usage error) so a wrapper can branch on the number alone.
EXIT_NOT_BUILT = 3

#: A verb that exists and refused on purpose. 4, not 2 and not 3: argparse owns 2
#: for a usage error, 3 says "you asked for something this package has not built",
#: and a refusal is neither. Same distinction `write_media` was given at V5 -- a
#: wrapper that cannot tell "does not exist" from "exists and refused you" has to
#: parse message text, and message text is not an API.
EXIT_REFUSED = 4

#: The five verbs, and only these. `publish` is NOT here: it was withdrawn
#: 2026-09-28 because a verb nobody is obliged to run gates nothing, and because
#: re-reading a manifest to print a verdict is `verify` under a second name. The
#: refusal that `publish` implied now lives in the media writer, `write_media`,
#: which both render call sites reach (LLD v010 §8.2, V5).
VERBS: dict[str, str] = {
    "build": "generate lesson video + deck",
    "review": "audit a saved .plan.json (narration/topic/quality)",
    "tts-check": "TTS provider health probe: synthesise a fixed phrase, assert a "
    "plausible duration and that word boundaries are returned",
    "verify": "deterministic pre-build QA on a saved .plan.json (no LLM, no render)",
    "render": "project a storyboard onto a lesson plan and render its slides",
}

#: `render` is the one verb that is BUILT. The other four still report 3.
BUILT: frozenset[str] = frozenset({"render"})


def build_parser() -> argparse.ArgumentParser:
    """The parser, built separately so tests can inspect it without exiting."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Studio: docs -> scene plan -> synced video + PPTX lesson.",
    )
    sub = parser.add_subparsers(dest="verb", required=True, metavar="VERB")
    for name, help_text in VERBS.items():
        child = sub.add_parser(name, help=help_text, description=help_text)
        if name == "render":
            child.add_argument(
                "storyboard", type=Path, metavar="STORYBOARD.json",
                help="the executable storyboard to render",
            )
            child.add_argument(
                "-o", "--out", type=Path, default=Path("out"),
                help="directory to write frames into (default: ./out)",
            )
            child.add_argument(
                "--allow-unshippable", action="store_true",
                help="render even though scenes are unanchored or the lesson has no "
                     "takeaway. The refusal is printed either way; this only stops it "
                     "being fatal. For looking at frames, not for publishing",
            )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch one invocation. Returns the process exit code.

    Every currently-declared verb is unimplemented, so this reports that and
    returns 3. It does NOT pretend to build anything, and it does not accept a
    verb it has not declared.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.verb in BUILT:
        return _run_render(args)
    print(
        f"{PROG}: `{args.verb}` is declared but not built yet. "
        f"`render` is built; the rest are Phase 0 -- see docs/PLAN-tutorial-lane.md "
        f"(P0-a, P0-d, P0-e).",
        file=sys.stderr,
    )
    return EXIT_NOT_BUILT

def _run_render(args: argparse.Namespace) -> int:
    """Project a storyboard, then render its slides. Refuses an unshippable lesson.

    The refusal is the point and it is the default. A storyboard whose scenes cannot
    be traced to a citation renders perfectly well -- `render_scenes` does not check
    provenance -- so a build that skipped this step would emit a clean-looking lesson
    built on claims nobody sourced. Measured on the real storyboard: 1 of 8 scenes is
    anchored, so the default path refuses and writes nothing.

    `--allow-unshippable` exists for looking at frames, and it prints every gap it is
    stepping over. It is not a publish switch, and `write_media` remains the egress
    chokepoint that refuses a fixture build at exit 4 regardless.
    """
    from .projector import project
    from .storyboard import find_all, load

    board_path: Path = args.storyboard
    if not board_path.is_file():
        print(f"{PROG} render: no such storyboard: {board_path}", file=sys.stderr)
        return EXIT_REFUSED

    board, gaps = load(board_path)
    findings = find_all(board, gaps)
    if findings:
        print(
            f"{PROG} render: {board_path} has {len(findings)} storyboard gap(s):",
            file=sys.stderr,
        )
        for gap in findings:
            print(f"  {gap}", file=sys.stderr)
        return EXIT_REFUSED

    result = project(board)
    anchored = result.scenes - len(result.unanchored)
    print(f"storyboard : {board_path}")
    print(f"provenance : {len(board.citations)} citation(s) from {board.source_document}")
    print(
        f"projection : {result.steps} steps -> {result.scenes} scenes, "
        f"{anchored} anchored"
    )

    if not result.shippable:
        print(
            "\nREFUSED: this lesson is not shippable, and nothing was written.",
            file=sys.stderr,
        )
        # A different name from the loop above on purpose: `findings` holds
        # `storyboard.Gap` and `result.gaps` holds `projector.ProjectionGap`, and one
        # name for both made mypy infer the first type and reject the second.
        for problem in result.gaps:
            print(
                f"  {problem.kind} @ {problem.where}: {problem.detail}",
                file=sys.stderr,
            )
        if not args.allow_unshippable:
            print(
                "\nPass --allow-unshippable to render anyway and look at the frames.",
                file=sys.stderr,
            )
            return EXIT_REFUSED
        print(
            "\n--allow-unshippable given: rendering anyway, for inspection only.",
            file=sys.stderr,
        )

    from .studio.slides import render_scenes

    out_dir: Path = args.out / board.id
    work_dir = out_dir / "_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    frames = 0
    for index, scene in enumerate(result.plan["scenes"], 1):
        sub = work_dir / f"s{index:02d}"
        sub.mkdir(parents=True, exist_ok=True)
        for page in render_scenes({"scenes": [scene]}, sub):
            for frame in page:
                (out_dir / f"scene{index:02d}-{frame.name}").write_bytes(
                    frame.read_bytes()
                )
                frames += 1
    print(f"\nrendered   : {frames} frame(s) -> {out_dir}")
    return 0
