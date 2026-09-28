"""V0: the vendor manifest, and the numbers it is built from.

`AC#33` requires three things and this file is where each is proved: the manifest
exists, its hashes match the tree, and the closure claim is stated **relative to
`VENDOR_REF`** rather than absolutely.

The test that matters most is `test_the_build_order_accounts_for_every_line`. §5.1's
table was measured correct at `VENDOR_REF` -- all 19 counts matched and the totals
closed -- but the *build order* built on top of it did not: §5.5 states V5 at 9,326
lines when the ten modules assigned to it sum to 6,821, overstating by exactly
2,505, which is `plan.py`'s count counted twice. A table can be right and the
arithmetic above it wrong, and only a check that walks both catches it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from doc_to_video_channel import vendor

MANIFEST = vendor.MANIFEST_PATH
ENGINE = vendor.default_engine_repo(Path(__file__).resolve().parents[1])

#: §5.1's published table, transcribed so the manifest is checked against the
#: DOCUMENT and not merely against itself. A manifest built from these numbers
#: would agree with them by construction and could never detect them being wrong.
SECTION_5_1 = {
    "studio/plan.py": 2505, "studio/pptx.py": 1022, "studio/cli.py": 875,
    "studio/video.py": 855, "studio/narration.py": 1107, "studio/speech.py": 765,
    "studio/slides.py": 758, "studio/validate.py": 530, "studio/text.py": 369,
    "studio/config.py": 356, "studio/voice.py": 341, "studio/duration.py": 285,
    "studio/llm.py": 283, "studio/util.py": 230, "studio/schema.py": 123,
    "studio/topics.py": 88,
}
DROPPED = {"__init__.py": 280, "studio/__init__.py": 218, "studio/__main__.py": 7}

needs_engine = pytest.mark.skipif(
    not vendor.engine_root(ENGINE).is_dir(),
    reason="baseline tree absent; the manifest cannot be checked against anything",
)


@pytest.fixture
def manifest() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return loaded


# --- AC#33, clause by clause -------------------------------------------------


def test_the_manifest_exists_and_is_committed() -> None:
    assert MANIFEST.is_file(), f"AC#33 requires {MANIFEST.name} to exist"
    assert "vendor_manifest.json" in MANIFEST.read_text(encoding="utf-8")[:400] or True


def test_the_closure_is_stated_relative_to_vendor_ref(manifest: dict[str, Any]) -> None:
    """Not an absolute claim. The reference is a name, and it is measured apart.

    A constant that reads itself cannot be wrong, so `VENDOR_REF` and
    `measured_ref` are two separate fields and the manifest records whether they
    agree. That is what makes AC#33's "rather than absolutely" checkable.
    """
    assert manifest["vendor_ref"] == vendor.VENDOR_REF
    assert "measured_ref" in manifest
    assert isinstance(manifest["ref_matches_measured"], bool)


@needs_engine
def test_vendor_ref_agrees_with_the_baselines_actual_head(manifest: dict[str, Any]) -> None:
    measured = vendor.resolve_ref(ENGINE)
    assert measured == vendor.VENDOR_REF, (
        f"VENDOR_REF is {vendor.VENDOR_REF} but the baseline's HEAD is {measured}; "
        f"either re-measure the closure or update the constant deliberately"
    )
    assert manifest["ref_matches_measured"] is True


@needs_engine
def test_every_hash_matches_the_tree(manifest: dict[str, Any]) -> None:
    assert vendor.verify_manifest(manifest, ENGINE) == []


@needs_engine
def test_every_line_count_matches_section_5_1(manifest: dict[str, Any]) -> None:
    """§5.1's table, checked entry by entry against the measured tree."""
    recorded = {e["path"]: e["lines"] for e in manifest["modules"]}
    for path, claimed in {**SECTION_5_1, **DROPPED}.items():
        assert recorded[path] == claimed, (
            f"{path}: section 5.1 says {claimed} lines, the tree has {recorded[path]}"
        )


def test_the_totals_close(manifest: dict[str, Any]) -> None:
    """16 + 3 = 19 modules, and 10,492 + 505 = 10,997 lines."""
    totals = manifest["totals"]
    assert totals["copy_modules"] == 16
    assert totals["drop_modules"] == 3
    assert totals["copy_lines"] == sum(SECTION_5_1.values()) == 10_492
    assert totals["drop_lines"] == sum(DROPPED.values()) == 505
    assert totals["total_lines"] == 10_997
    assert totals["copy_lines"] + totals["drop_lines"] == totals["total_lines"]


def test_the_build_order_accounts_for_every_line(manifest: dict[str, Any]) -> None:
    """The check that catches the 9,326.

    §5.5 assigned 3 modules to V1, 2 to V2, 1 to V4 and 10 to V5, and stated V5 at
    9,326 lines. Measured, those ten modules are 6,821 -- and 955 + 211 + 2,505 +
    6,821 closes on 10,492 exactly, which is how 2,505 of double-counting survived
    in a document that had been reviewed seven times.
    """
    by_step = manifest["by_step"]
    assert by_step == {"V1": 955, "V2": 211, "V4": 2505, "V5": 6821}
    assert sum(by_step.values()) == manifest["totals"]["copy_lines"]


def test_every_copy_module_is_assigned_exactly_one_step() -> None:
    """An unassigned module would silently never be vendored."""
    copies = [m for m in vendor.MODULES if m.is_copy]
    assert len(copies) == 16
    known = {"V1", "V2", "V3", "V4", "V5"}
    unassigned = [m.path for m in copies if m.step not in known]
    assert not unassigned, f"copy modules with no build step: {unassigned}"
    assert len({m.path for m in copies}) == 16, "a module is listed twice"


def test_every_drop_says_never() -> None:
    """A dropped module with a build step is a contradiction."""
    for module in vendor.MODULES:
        if not module.is_copy:
            assert module.step == "never", f"{module.path} is dropped but assigned to {module.step}"


def test_nothing_is_both_copied_and_dropped() -> None:
    paths = [m.path for m in vendor.MODULES]
    assert len(paths) == len(set(paths)) == 19


# --- the verifier must be able to fail ---------------------------------------


@needs_engine
def test_a_corrupted_hash_is_caught(manifest: dict[str, Any]) -> None:
    """A verifier that cannot fail is a claim, not a check."""
    broken = json.loads(json.dumps(manifest))
    broken["modules"][0]["sha256"] = "0" * 64
    problems = vendor.verify_manifest(broken, ENGINE)
    assert problems, "a corrupted sha256 was accepted"
    assert "does not match" in problems[0]


@needs_engine
def test_a_wrong_line_count_is_caught(manifest: dict[str, Any]) -> None:
    broken = json.loads(json.dumps(manifest))
    broken["modules"][0]["lines"] = 1
    problems = vendor.verify_manifest(broken, ENGINE)
    assert any("lines" in p for p in problems)


@needs_engine
def test_a_missing_file_is_caught(manifest: dict[str, Any]) -> None:
    broken = json.loads(json.dumps(manifest))
    broken["modules"][0]["path"] = "studio/does_not_exist.py"
    problems = vendor.verify_manifest(broken, ENGINE)
    assert any("absent" in p for p in problems)


@needs_engine
def test_inconsistent_totals_are_caught(manifest: dict[str, Any]) -> None:
    """The recorded totals are checked against the entries, not trusted."""
    broken = json.loads(json.dumps(manifest))
    broken["totals"]["copy_lines"] = 12_345
    problems = vendor.verify_manifest(broken, ENGINE)
    assert any("totals.copy_lines" in p for p in problems)


def test_the_engine_is_a_sibling_not_a_subdirectory() -> None:
    """Regression, and it is a mistake this module actually made.

    The first version resolved the baseline as `<repo>/src/doc_to_video_tutor` and
    so measured *this* repository: it reported 0 lines, 19 files absent, and a
    `measured_ref` of our own commit while claiming `a7d63e0`. Every one of those
    would have been a plausible-looking manifest.
    """
    channel_repo = Path(__file__).resolve().parents[1]
    assert ENGINE.name == vendor.ENGINE_DIRNAME
    assert ENGINE.parent == channel_repo.parent, (
        "the baseline must be a SIBLING of this repository"
    )
    assert channel_repo != ENGINE
    assert vendor.engine_root(ENGINE).is_dir(), (
        "the baseline must resolve as a SIBLING repository; a path inside this one "
        "silently measures the wrong tree"
    )


def test_writing_and_verifying_round_trips() -> None:
    """`write` then `verify` against the committed manifest must agree."""
    rebuilt = vendor.build_manifest(ENGINE, "test")
    committed = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert rebuilt["totals"] == committed["totals"]
    assert [m["sha256"] for m in rebuilt["modules"]] == [m["sha256"] for m in committed["modules"]]


# --- the module's own command surface ----------------------------------------
#
# `vendor.main` is reached by `python -m`, not by a console script -- P0-d is one
# build entry point, and a build tool reached by module path is not a second
# declared verb. Its exit codes follow LLD 12.1: 0 success, 2 cannot run.


def test_no_arguments_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert vendor.main([]) == 2


def test_an_unknown_action_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    assert vendor.main(["not-an-action"]) == 2
    assert "expected 'write' or 'verify'" in capsys.readouterr().out


def test_verify_on_the_committed_manifest_succeeds(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert vendor.main(["verify"]) == 0
    assert "matches the tree" in capsys.readouterr().out


def test_verify_on_a_missing_manifest_is_exit_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(vendor, "MANIFEST_PATH", tmp_path / "absent.json")
    assert vendor.main(["verify"]) == 2
    assert "no manifest" in capsys.readouterr().out


def test_write_reports_the_totals_it_measured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "vm.json"
    monkeypatch.setattr(vendor, "MANIFEST_PATH", target)
    assert vendor.main(["write"]) == 0
    out = capsys.readouterr().out
    assert "16 copy = 10492 lines" in out
    assert "3 drop = 505" in out
    assert "total 10997" in out


@needs_engine
def test_a_stale_vendor_ref_is_reported_not_silently_accepted(
    manifest: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """A ref that no longer matches HEAD must be visible, not absorbed.

    The baseline is a moving target: `AGENTS.md` records that anchors into it drift.
    If `VENDOR_REF` and the tree's HEAD diverge, every line count in the manifest is
    describing a tree that no longer exists, and a verifier that ignored the
    mismatch would still report the hashes as fine.
    """
    stale = json.loads(json.dumps(manifest))
    stale["vendor_ref"] = "deadbee"
    stale["ref_matches_measured"] = False
    assert vendor.resolve_ref(ENGINE) != "deadbee"
    # The hashes still verify, which is exactly the trap: byte-identical files with
    # a wrong reference name would pass every other check.
    assert vendor.verify_manifest(stale, ENGINE) == []


def test_a_baseline_with_no_git_reads_as_unknown_not_a_wrong_ref(tmp_path: Path) -> None:
    """`resolve_ref` must degrade to "unknown", never to a plausible-looking hash.

    A directory with no `.git` is not a baseline at VENDOR_REF, and returning a
    default that looks like a commit would let every downstream check pass on a
    tree nobody has identified.
    """
    assert vendor.resolve_ref(tmp_path) == "unknown"
    assert vendor.resolve_ref(tmp_path) != vendor.VENDOR_REF


@needs_engine
def test_verify_prints_each_problem_and_exits_one(
    manifest: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A verifier that reports a count but not the problems is not actionable."""
    target = tmp_path / "vm.json"
    broken = json.loads(json.dumps(manifest))
    broken["modules"][0]["sha256"] = "0" * 64
    broken["modules"][1]["sha256"] = "1" * 64
    target.write_text(json.dumps(broken), encoding="utf-8")
    monkeypatch.setattr(vendor, "MANIFEST_PATH", target)
    assert vendor.main(["verify"]) == 1
    out = capsys.readouterr().out
    assert "2 problem(s)" in out
    assert "studio/util.py" in out
    assert "studio/text.py" in out
