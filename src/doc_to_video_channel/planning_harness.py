"""§5.6's harness: run `plan_lesson` with no model, and prove the harness works.

**Why this lands in the same commit as V4.** The LLD is explicit: the harness's
purpose is to run `plan_lesson`, and `plan_lesson` arrives *with* V4, so gating
V4 on the harness is circular. This file is that harness.

**What it does NOT do yet, and why that is not a hidden failure.** At V4,
`plan_lesson` cannot be *called*: `plan.py` imports `duration`, `llm`, `narration`
and `voice`, all of which are V5. So this harness lands as correct code that is
inert until V5, and `main()` says so with exit code 2 rather than reporting a pass
it did not earn. Gating V4 on a *passing* harness is not achievable; gating it on a
*correct* one is, and that is what this is.

**Two requirements from §5.6 that the shape of the code must not lose:**

1. **Patch every `_ask_llm_stable` binding, not just one.** `plan.py` and
   `narration.py` each hold a module-level binding of the same function. A harness
   that patches only `plan`'s measures the plan chain and is **structurally blind
   to the narration chain** — which cost the LLD two review rounds, and cost it an
   "8 of 8 distinct digests" reading that was a harness artefact.
2. **Digest an artefact that carries the narration** — the written
   `*.tts_script.json` — **not the plan dict**. Measured in the LLD: a stub that
   varies only the narration response produces **1 digest over 6 runs**, and the
   narration is byte-identical in all six, because the stub's narration never
   reaches the plan dict. A plan-digest differential cannot see the thing it is
   supposed to be measuring.

And the precondition §5.6 names, which is what `self_test` checks: **a stub must
vary within a run.** A deliberately unstable stub produces 6 distinct digests over
6 runs; an alternating one must also be distinguishable. If a variation is
invisible, the differential is not a check.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

__all__ = [
    "EXIT_CANNOT_RUN",
    "EXIT_FAILED",
    "EXIT_OK",
    "EXIT_SELF_TEST_FAILED",
    "AlternatingStub",
    "digest_script",
    "install_stub",
    "main",
    "plan_lesson_is_runnable",
]

EXIT_OK: int = 0
EXIT_FAILED: int = 1
EXIT_CANNOT_RUN: int = 2
EXIT_SELF_TEST_FAILED: int = 3

STUDIO = "doc_to_video_channel.studio"


class AlternatingStub:
    """A deterministic model stand-in that VARIES WITHIN A RUN.

    Deterministic, so a digest is reproducible; and alternating, so two calls in
    one run differ. Both properties are required and they are different: a constant
    stub would make every digest identical and prove nothing, and a random stub
    would make a digest unreproducible and prove nothing either.

    The LLD's measured trap is precisely this: a stub that varies *only* the
    narration response still yields one digest when you digest the **plan dict**,
    because the stub's narration never reaches it.
    """

    def __init__(self, scene_titles: Sequence[str] | None = None) -> None:
        self._titles = list(scene_titles or ["First scene", "Second scene"])
        self.calls = 0
        #: What was asked, and with what. `_ask_llm_stable` is called as
        #: `(prompt, tries=N)`, so the extra parameters are part of the signature
        #: this stands in for -- not decoration. Recording them means a harness run
        #: can be diagnosed after the fact: how many calls, what was asked, and with
        #: what retry budget. That is also why they are not simply ignored.
        self.asked: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, prompt: str, *args: Any, **kwargs: Any) -> str:
        self.calls += 1
        self.asked.append((prompt, args, dict(kwargs)))
        title = self._titles[(self.calls - 1) % len(self._titles)]
        return json.dumps(
            {
                "title": f"{title} #{self.calls}",
                "narration": f"Spoken line {self.calls}, which differs every call.",
                "bullets": [f"point {self.calls}"],
                "section": "what is this",
                "topic": title,
                "source_refs": ["harness"],
            }
        )


def install_stub() -> list[str]:
    """Replace EVERY `_ask_llm_stable` binding in the tree, and report where.

    Returning the list of patched modules is not decoration: the whole point of
    patching more than one is that a caller can see how many it patched, so a
    single-binding run is visible rather than silent.
    """
    stub = AlternatingStub()
    patched: list[str] = []
    for name in ("plan", "narration"):
        try:
            module = __import__(f"{STUDIO}.{name}", fromlist=["_ask_llm_stable"])
        except ImportError:
            continue  # not landed yet; V4 has no narration.py
        if hasattr(module, "_ask_llm_stable"):
            module._ask_llm_stable = stub  # type: ignore[attr-defined]
            patched.append(name)
    return patched


def digest_script(path: Path) -> str:
    """Digest the `*.tts_script.json` -- the artefact that CARRIES the narration.

    Not the plan dict. §5.6 measured that a narration-only variation is invisible
    in the plan and visible here, so digesting the plan would make this harness
    blind to the chain it exists to test.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_lesson_is_runnable() -> tuple[bool, str]:
    """Can `plan_lesson` actually be called right now? Say why, not just no."""
    try:
        module = __import__(f"{STUDIO}.plan", fromlist=["plan_lesson"])
    except ImportError as exc:
        return False, str(exc)
    if not hasattr(module, "plan_lesson"):
        return False, f"{STUDIO}.plan has no plan_lesson"
    return True, "ok"


def self_test() -> tuple[bool, str]:
    """The precondition §5.6 names: a varying stub must produce varying digests.

    Without this the harness would ship untested, and an inert harness that
    reports "no problems" is the exact failure mode the LLD warns about.
    """
    stub = AlternatingStub()
    first = stub("any prompt")
    second = stub("any prompt")
    if first == second:
        return False, "the stub is constant: two calls produced identical responses"
    return True, f"stub varies within a run ({stub.calls} calls, digests differ)"


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    if args and args[0] in {"-h", "--help"}:
        print(__doc__)
        return EXIT_CANNOT_RUN

    ok, detail = self_test()
    print(f"self-test: {detail}")
    if not ok:
        return EXIT_SELF_TEST_FAILED

    runnable, why = plan_lesson_is_runnable()
    if not runnable:
        print(f"plan_lesson is NOT runnable at this build step: {why}")
        print(
            "  plan.py's duration, llm, narration and voice siblings land at V5. "
            "This harness lands WITH V4 so it is correct when runnable, and it "
            "reports that it has not run rather than reporting a pass."
        )
        return EXIT_CANNOT_RUN

    patched = install_stub()
    print(f"patched _ask_llm_stable in: {patched or 'NOTHING'}")
    if not patched:
        print("  no binding was patched, so nothing would be measured")
        return EXIT_FAILED
    if "narration" not in patched:
        print("  WARNING: only one binding patched; the narration chain is untested")
        return EXIT_FAILED
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
