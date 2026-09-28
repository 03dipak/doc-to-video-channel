"""Make the vendored tests' data paths resolve, without editing a vendored test.

9 of the reference's 315 tests read two real documents that live OUTSIDE the
reference's `tests/` directory, so that suite is not hermetic:

    modules/08_concepts_mod03_gates.md
    tests/fixtures/04_concepts_mod04_release_gates.md

Those tests address them by the *reference's* repo-relative path strings. The
alternative to symlinking was rewriting nine path literals inside vendored files,
which would have cost the one provenance property this whole exercise bought:
that each of the 7 copied test files is byte-identical to a fresh
`sed 's/doc_to_video_tutor/doc_to_video_channel/'` of its reference, 0 residual
old references. So the paths are made to resolve instead.

The bytes live once, in `tests/fixtures/vendor/`, with their provenance and
sha256 in `PROVENANCE.json` beside them. The symlinks are generated per session
and are gitignored, so nothing generated is ever committed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypedDict, cast

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _ROOT / "tests" / "fixtures" / "vendor"
_PROVENANCE = _VENDOR / "PROVENANCE.json"


class _Fixture(TypedDict):
    local: str
    reference_path: str
    bytes: int
    sha256: str


class _Provenance(TypedDict):
    vendor_ref: str
    fixtures: list[_Fixture]


def _provenance() -> _Provenance:
    """Parse PROVENANCE.json, and refuse rather than proceed on a bad shape.

    An unvalidated `json.loads` here would return `Any` and let a malformed
    manifest silently place zero fixtures -- which is exactly the failure the 9
    dead tests already had once. Every key is checked, so a typo in the file is a
    loud failure at session start instead of 9 `FileNotFoundError`s.
    """
    raw: object = json.loads(_PROVENANCE.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        pytest.exit(f"{_PROVENANCE} must contain a JSON object")
    for key in ("vendor_ref", "fixtures"):
        if key not in raw:
            pytest.exit(f"{_PROVENANCE} is missing the required key {key!r}")
    entries = raw["fixtures"]
    if not isinstance(entries, list) or not entries:
        pytest.exit(f"{_PROVENANCE} must list at least one fixture")
    for entry in entries:
        if not isinstance(entry, dict):
            pytest.exit(f"{_PROVENANCE} has a non-object fixture entry: {entry!r}")
        for key in ("local", "reference_path", "bytes", "sha256"):
            if key not in entry:
                pytest.exit(f"fixture entry missing {key!r}: {entry!r}")
    return cast(_Provenance, raw)


def _place(reference_path: str, local: str) -> Path:
    """Symlink one fixture to where a vendored test expects to find it."""
    target = _ROOT / reference_path
    source = _VENDOR / Path(local).name
    assert source.is_file(), f"vendored fixture missing: {source}"
    if target.is_symlink():
        if target.resolve() == source.resolve():
            return target
        target.unlink()
    elif target.exists():
        # Never clobber a real file that is not ours.
        pytest.exit(f"refusing to replace {target}: it exists and is not a symlink")
    target.parent.mkdir(parents=True, exist_ok=True)
    # A symlink's target is resolved relative to the LINK'S OWN directory, not the
    # repo root. The first version used `source.relative_to(_ROOT)`, which made
    # `modules/08_concepts_mod03_gates.md` point at
    # `modules/tests/fixtures/vendor/...` -- a path that does not exist, so all 9
    # tests kept failing on the same FileNotFoundError with the symlink plainly
    # present in `ls`. relpath against the link's parent is the correct base.
    target.symlink_to(os.path.relpath(source, target.parent))
    return target


@pytest.fixture(scope="session", autouse=True)
def _vendor_fixtures_in_place() -> list[Path]:
    placed: list[Path] = []
    for entry in _provenance()["fixtures"]:
        placed.append(_place(entry["reference_path"], entry["local"]))
    return placed
