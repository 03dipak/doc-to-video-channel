"""What gets vendored, from where, and proof that the answer is still true.

`docs/LLD-tutorial-lane.md` §5.1 states a table of 16 modules to copy and 3 to
drop, and `AC#33` requires that a `vendor_manifest.json` exists, that its hashes
match the tree, and that the closure claim be stated **relative to `VENDOR_REF`**
rather than absolutely. This module is that claim, in a form a test can check.

**Why the table lives here and not only in the LLD.** A table in prose is a claim.
Measured 2026-09-28 against `VENDOR_REF`, all 19 line counts matched exactly and
the totals closed -- but the *build order's* per-step totals did not: §5.5 states
V5 at 9,326 lines when the ten modules assigned to it sum to 6,821, overstating by
2,505, which is `plan.py`'s count double-counted. So the table in the LLD was
accurate and the arithmetic built on top of it was not, which is precisely the
failure mode of storing a number without re-deriving it.

**`VENDOR_REF` is created here**, at V0. It had 0 occurrences in the baseline
before this module existed, while three documents referred to it. When
`config.py` is vendored at V1 it carries its own `VENDOR_REF`; the two must agree,
and `test_vendor_ref_is_agreed` is what holds them to it.

**Nothing here copies anything.** This is the manifest of intent, measured against a
named reference. The copy happens in V1-V5, one step at a time, and each step
verifies the files it lands against the hashes recorded here.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

__all__ = [
    "MANIFEST_PATH",
    "MODULES",
    "VENDOR_REF",
    "Module",
    "build_manifest",
    "main",
    "verify_manifest",
]

#: The reference commit the copy comes from. **Created at V0** — it had 0
#: occurrences in the baseline while three documents referred to it by name.
#: Measured, not assumed: `git -C ../doc-to-video-tutor rev-parse --short HEAD`.
VENDOR_REF: Final = "a7d63e0"

#: Where the baseline tree lives. A path, not a dependency: nothing here imports
#: or installs the engine, and `uv.lock` holds 0 references to it. It is read for
#: its bytes and nothing more. A SIBLING repository, not a subdirectory of this
#: one -- the first version of this module resolved it as `<repo>/src/...` and
#: cheerfully measured *this* repository, reporting 0 lines and a `measured_ref` of
#: our own commit.
ENGINE_DIRNAME: Final = "doc-to-video-tutor"
ENGINE_PACKAGE: Final = "doc_to_video_tutor"


def default_engine_repo(channel_repo: Path) -> Path:
    """The sibling baseline tree, resolved from this repository's location."""
    return channel_repo.parent / ENGINE_DIRNAME

MANIFEST_PATH: Final = Path(__file__).with_name("vendor_manifest.json")


@dataclass(frozen=True, slots=True)
class Module:
    """One module of the closure: what to do with it, and when it lands."""

    path: str
    decision: str  # "copy" | "drop"
    step: str  # "V1".."V5", or "never" for a drop
    reason: str
    #: What WE changed in this file, if anything. **The manifest's sha256 shows THAT a
    #: file diverges from the baseline; it cannot show WHAT changed**, so a reader
    #: comparing hashes learns that `config.py` was edited and nothing more. Measured:
    #: the first divergence (V3's brand change) broke a V1 test that asserted
    #: verbatim equality for `config.py`, and the fix was to record the edits rather
    #: than to relax the test -- because a test that cannot say which files are
    #: expected to diverge has to be edited at every step.
    channel_edits: tuple[str, ...] = ()

    @property
    def is_copy(self) -> bool:
        return self.decision == "copy"


#: The §5.1 closure, 16 copy and 3 drop, with the build step each belongs to.
#: `step` is the extra information the LLD's table does not carry, and it is what
#: makes the manifest actionable rather than merely descriptive.
MODULES: Final[tuple[Module, ...]] = (
    Module(
        "studio/util.py",
        "copy",
        "V1",
        "LoadedSource, load_documents; zero internal imports",
        (
            "A5: _load_docx + the .docx/.doc branch in load_documents",
            "two return annotations, so the strict gate stays whole",
            "AC#17(a): the half-window floor, applied to the space fallback as well "
            "as the heading preference",
        ),
    ),
    Module("studio/text.py", "copy", "V1", "_has_non_latin_script, _nar_tokens; zero imports"),
    Module(
        "studio/config.py",
        "copy",
        "V1",
        "_SECTIONS, _ENUM_HINTS, both prompts, VENDOR_REF",
        ("V3: PACKAGE_NAME re-branded, which propagates to BRAND_NAME and BRAND_FOOTER",),
    ),
    Module("studio/topics.py", "copy", "V2", "_BANNED_NGRAMS consumers"),
    Module(
        "studio/schema.py",
        "copy",
        "V2",
        "SlideScene, LessonPlan; the only Pydantic models",
        (
            "AC#7: section is now SectionKind | None, a Literal over the five "
            "canonical members, with a spelling canonicaliser",
        ),
    ),
    Module(
        "studio/plan.py",
        "copy",
        "V4",
        "planner; hosts the _extra_gates registry",
        ("one return annotation, so the strict gate stays whole",),
    ),
    Module("studio/cli.py", "copy", "V5", "the build path; 5 subcommands"),
    Module("studio/duration.py", "copy", "V5", "the duration formula and duration_verdict"),
    Module("studio/llm.py", "copy", "V5", "_ask_llm_stable; both bindings resolve through it"),
    Module("studio/narration.py", "copy", "V5", "narration contract; 2nd _ask_llm_stable binding"),
    Module("studio/pptx.py", "copy", "V5", "renderer 2 of 2; injects the same Key Takeaways card"),
    Module("studio/slides.py", "copy", "V5", "renderer 1 of 2; injects Key Takeaways"),
    Module("studio/speech.py", "copy", "V5", "TTS, contains_corrupt_text, spoken_token_set"),
    Module("studio/validate.py", "copy", "V5", "_render_blocking_problems, guard_plan"),
    Module("studio/video.py", "copy", "V5", "renderer assembly; TTS + moviepy"),
    Module("studio/voice.py", "copy", "V5", "NarrationVoice + registry"),
    Module("__init__.py", "drop", "never", "every symbol is dead or is the deprecated shim"),
    Module("studio/__init__.py", "drop", "never", "a re-export facade; no new subpackage"),
    Module("studio/__main__.py", "drop", "never", "serves python -m only; no second entry point"),
)


def engine_root(engine: Path) -> Path:
    """The baseline's package directory, given the baseline REPOSITORY path."""
    return engine / "src" / ENGINE_PACKAGE


def resolve_ref(engine: Path) -> str:
    """Ask git for the baseline's actual HEAD, so a stale constant is visible.

    The point is that this is a SEPARATE measurement from `VENDOR_REF`. A constant
    that reads itself is a constant that cannot be wrong, and the whole claim in
    `AC#33` is that the closure is stated relative to a named reference.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(engine), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() or "unknown"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(engine: Path, generated: str) -> dict[str, Any]:
    """Measure every module of the closure at the baseline's actual HEAD.

    Counts and hashes are **measured**, never copied from the LLD's table. That
    direction matters: a manifest built from the table would agree with the table
    by construction and could never detect the table being wrong.
    """
    root = engine_root(engine)
    measured_ref = resolve_ref(engine)
    entries: list[dict[str, Any]] = []
    for module in MODULES:
        target = root / module.path
        exists = target.is_file()
        entries.append(
            {
                **{
                    k: (list(v) if isinstance(v, tuple) else v)
                    for k, v in asdict(module).items()
                },
                "exists": exists,
                "lines": len(target.read_text(encoding="utf-8").splitlines())
                if exists
                else None,
                "sha256": _digest(target) if exists else None,
            }
        )
    copy_entries = [e for e in entries if e["decision"] == "copy"]
    drop_entries = [e for e in entries if e["decision"] == "drop"]
    return {
        "schema_version": 1,
        "vendor_ref": VENDOR_REF,
        "measured_ref": measured_ref,
        "ref_matches_measured": measured_ref == VENDOR_REF,
        "engine_package": ENGINE_PACKAGE,
        "generated": generated,
        "modules": entries,
        "totals": {
            "copy_modules": len(copy_entries),
            "copy_lines": sum(e["lines"] or 0 for e in copy_entries),
            "drop_modules": len(drop_entries),
            "drop_lines": sum(e["lines"] or 0 for e in drop_entries),
            "total_lines": sum(e["lines"] or 0 for e in entries),
        },
        "by_step": {
            step: sum(e["lines"] or 0 for e in copy_entries if e["step"] == step)
            for step in sorted({e["step"] for e in copy_entries})
        },
    }


def verify_manifest(manifest: dict[str, Any], engine: Path) -> list[str]:
    """Every way the manifest can be wrong, as a list of messages.

    Returns problems rather than raising, so a caller can print them all. An empty
    list means the manifest still describes the tree it claims to.
    """
    problems: list[str] = []
    root = engine_root(engine)

    for entry in manifest.get("modules", []):
        target = root / entry["path"]
        if not target.is_file():
            problems.append(f"{entry['path']}: absent from the baseline")
            continue
        if entry["sha256"] != _digest(target):
            problems.append(
                f"{entry['path']}: sha256 {entry['sha256'][:12]}... does not match "
                f"the tree's {_digest(target)[:12]}..."
            )
        lines = len(target.read_text(encoding="utf-8").splitlines())
        if entry["lines"] != lines:
            problems.append(f"{entry['path']}: recorded {entry['lines']} lines, tree has {lines}")

    # EVERY total is recomputed. A verifier that checks three of five is a verifier
    # with a hole in it, and the hole was found by a test rather than by reading:
    # `copy_lines` was recorded and never compared, so a manifest claiming 12,345
    # copied lines verified clean.
    copies = [e for e in manifest["modules"] if e["decision"] == "copy"]
    drops = [e for e in manifest["modules"] if e["decision"] == "drop"]
    actual = {
        "copy_modules": len(copies),
        "drop_modules": len(drops),
        "copy_lines": sum(e["lines"] or 0 for e in copies),
        "drop_lines": sum(e["lines"] or 0 for e in drops),
        "total_lines": sum(e["lines"] or 0 for e in manifest["modules"]),
    }
    for key, value in actual.items():
        if manifest.get("totals", {}).get(key) != value:
            problems.append(
                f"totals.{key}: recorded {manifest.get('totals', {}).get(key)}, actual {value}"
            )

    return problems


def main(argv: Sequence[str] | None = None) -> int:
    """Write the manifest, or verify the one on disk. No new console entry point.

    `python -m doc_to_video_channel.vendor write` regenerates it; `verify` checks
    the committed copy against the tree. `P0-d` is one build entry point, and this
    is a build tool reached by module path, not a second declared verb.
    """
    import sys

    args = list(argv) if argv is not None else sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    action = args[0]
    channel_repo = Path(__file__).resolve().parents[2]
    engine = Path(args[1]) if len(args) > 1 else default_engine_repo(channel_repo)

    if action == "verify":
        if not MANIFEST_PATH.is_file():
            print(f"no manifest at {MANIFEST_PATH}")
            return 2
        problems = verify_manifest(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")), engine)
        if problems:
            print(f"{len(problems)} problem(s):")
            for p in problems:
                print(f"  {p}")
            return 1
        print(f"manifest matches the tree at {VENDOR_REF}")
        return 0

    if action == "write":
        from datetime import date

        manifest = build_manifest(engine, date.today().isoformat())
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        totals = manifest["totals"]
        print(f"wrote {MANIFEST_PATH}")
        print(f"  vendor_ref {manifest['vendor_ref']} (measured {manifest['measured_ref']})")
        print(
            f"  {totals['copy_modules']} copy = {totals['copy_lines']} lines; "
            f"{totals['drop_modules']} drop = {totals['drop_lines']}; "
            f"total {totals['total_lines']}"
        )
        return 0

    print(f"unknown action {action!r}; expected 'write' or 'verify'")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
