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

__all__ = ["EXIT_NOT_BUILT", "VERBS", "build_parser", "main"]

PROG = "doc-to-video-channel"

#: A verb this package declares but has not built yet. Distinct from argparse's
#: 2 (usage error) so a wrapper can branch on the number alone.
EXIT_NOT_BUILT = 3

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
    "render": "re-render media from a saved .plan.json without re-planning",
}


def build_parser() -> argparse.ArgumentParser:
    """The parser, built separately so tests can inspect it without exiting."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Studio: docs -> scene plan -> synced video + PPTX lesson.",
    )
    sub = parser.add_subparsers(dest="verb", required=True, metavar="VERB")
    for name, help_text in VERBS.items():
        sub.add_parser(name, help=help_text, description=help_text)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch one invocation. Returns the process exit code.

    Every currently-declared verb is unimplemented, so this reports that and
    returns 3. It does NOT pretend to build anything, and it does not accept a
    verb it has not declared.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    print(
        f"{PROG}: `{args.verb}` is declared but not built yet. "
        f"This is Phase 0 -- see docs/PLAN-tutorial-lane.md (P0-a, P0-d, P0-e).",
        file=sys.stderr,
    )
    return EXIT_NOT_BUILT
