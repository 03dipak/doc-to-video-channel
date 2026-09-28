"""The single egress chokepoint: nothing writes media except through here.

`AC#26` needs a control that cannot be bypassed, and a control is only real if
there is exactly one door. `publish` was withdrawn for the same reason it is being
replaced here: a verb nobody is obliged to run gates nothing, and a verb that
re-reads a manifest to print a verdict is `verify` under a second name.

So the control lives in the writer, and **both** `_render_media` call sites in
`cli.main` -- the `build` branch and the `render` branch -- route through it. The
count is asserted by `test_both_render_call_sites_route_through_the_writer`,
because a second door is exactly the thing this exists to prevent.

**The exit code is 4, not 2, and `AC#26`'s text is the stale one.** The LLD's own
§12.1 table gives **2** to argparse's usage error and reserves **4** for "refused
on purpose". A refusal exiting 2 would be indistinguishable from a typo, and a
caller that treats every non-zero as "retry or escalate" would retry a standing
policy. The measured refusal is therefore `SystemExit(4)`, and the divergence from
`AC#26`'s wording is recorded rather than quietly resolved.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

__all__ = [
    "EXIT_REFUSED",
    "FixtureRefusal",
    "fixture_bit",
    "write_media",
    "write_media_manifest",
]

#: LLD 12.1: 0 success, 1 gated, 2 usage error, 3 declared-not-built,
#: 4 refused on purpose. Reserved here and nowhere else.
EXIT_REFUSED: int = 4


class FixtureRefusal(SystemExit):
    """A `--test-fixture` artefact reached the writer.

    A `SystemExit` subclass rather than a `SystemExit(EXIT_REFUSED)` raised at the
    call site, so the refusal is a *typed* event a caller can catch and branch on
    without parsing a message -- the same reason the withdrawn `publish` was a bad
    place for this control.
    """

    def __init__(self, out_base: Path, source: str) -> None:
        self.out_base = out_base
        self.source = source
        super().__init__(EXIT_REFUSED)


def fixture_bit(plan: dict[str, Any]) -> bool:
    """Whether this build is a fixture. Absent means False, not "unknown".

    The bit is carried on the plan by the ingestion path; a plan that never went
    through `--test-fixture` simply has no key, and treating that as "unknown"
    would make every ordinary build raise.
    """
    for key in ("fixture", "is_fixture"):
        value = plan.get(key)
        if isinstance(value, bool):
            return value
    fixture = plan.get("FIXTURE")
    if isinstance(fixture, dict):
        return bool(fixture.get("is_fixture"))
    return False


def write_media_manifest(out_base: Path, plan: dict[str, Any], vendor_ref: str) -> Path:
    """Write the media's own manifest, carrying the bit and the reference.

    `AC#26` requires the bit to reach the media's manifest *alongside*
    `vendor_ref`, so a shipped artefact can name both its own origin and whether it
    was ever publishable. The stamp has to be **in the artefact**, not in a log
    line, because a log line is not what a later reader of the file can see.
    """
    manifest = {
        "schema_version": 1,
        "vendor_ref": vendor_ref,
        "fixture": fixture_bit(plan),
        "media": out_base.name,
    }
    target = out_base.with_suffix(".media.json")
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def write_media(plan: dict[str, Any], out_base: Path, vendor_ref: str) -> Path:
    """The chokepoint. Writes the manifest, or refuses.

    Refusal happens **before** anything is written, so a refused build leaves no
    media behind that a later step could pick up. A refusal that cleaned up after
    itself would still be a refusal that ran the thing it refuses.
    """
    if fixture_bit(plan):
        source = str(plan.get("source_files") or plan.get("title") or "unknown")
        print(
            f"REFUSED: {out_base.name} was built from --test-fixture content. "
            f"A fixture is never publishable, so nothing was written. Source: {source}",
            file=sys.stderr,
        )
        raise FixtureRefusal(out_base, source)
    return write_media_manifest(out_base, plan, vendor_ref)
