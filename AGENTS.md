# Working rules — doc-to-video-channel

This folder holds **decisions**, not code. The engine is a sibling tree at
`../doc-to-video-tutor`. Before anything else, read `docs/DESIGN.md` (the design
record and its three open decisions) and `docs/scratch.md` (what the engine got
wrong, and the pattern behind it).

## Reviewing: evidence, not opinion

A finding is something you measured, not something you suspect. Before reporting
a defect you must have produced and inspected real output.

1. **Run it.** Never review statically when the code can be executed. Build,
   render, or generate the actual artifact and look at it. A shape can be
   positioned correctly and still look wrong.
2. **Cross-check the code's own invariants.** Find what the code already asserts
   about itself — `LAYOUT_NOTES`, `_audit_layout`, `_render_blocking_problems`,
   docstrings claiming "X should never happen" — and verify those claims against
   the real output, not against the code's logic.
3. **Root cause with numbers.** Compute the exact values and show the arithmetic
   that ties them to a line. "8.30in wide, matching
   `min(8.92, 12.72) − max(0.42, 0.62)`" is a finding; "there may be an overlap"
   is not.
4. **Disprove before reporting.** Re-check at a second input, setting, or
   resolution. If it does not survive, drop it and say you dropped it. A number
   taken from the middle of a process must have its endpoint stated before it
   becomes a finding.
5. **Rank by evidence strength.** Confirmed-with-exact-cause first, then
   plausible, then cosmetic. Never bury one confirmed bug under ten nitpicks.
6. **Minimal fix, and why the old logic was wrong** — at the level of the wrong
   comparison ("this looked at one character where a clause boundary was
   required"), not "add a check here".
7. **Check for regressions of past defects.** `docs/DESIGN.md` § *Rejected, with
   reasons* and `docs/scratch.md` are the baseline, plus the engine's own ledger
   at `../doc-to-video-tutor/docs/quality_review.md`. **Half-fixes are findings.**
8. **A check that has only ever been shown a true statement is untested.** Write
   the *wrong* input first and confirm it fails, before writing the right input
   and confirming it passes. This is how the engine shipped 315 tests and a gate
   suite that passes a fabricated date in the narration — see `docs/scratch.md` §1.

If you cannot execute or render, say so explicitly and mark every finding
`UNVERIFIED — static read only`.

## Cite symbols, not lines

A `file:line` is a search hint with a shelf life. The engine's
`../doc-to-video-tutor/docs/CALL-FLOW.md` presents itself as the file:line
reference and has **51 unique anchors, none pointing at the right line** (median drift −813 lines).
One documentation pass in the engine wrote 12 wrong or stale citations, of which
four were code anchors.

- Name the **symbol**. Add a line number only as a convenience beside it.
- When several citations go in at once, resolve **all** of them. A sample is not a
  check.
- Never cite a line you have not opened in this session.
- A doc that tracks another doc must be re-read after that doc is edited, or it
  will cite its own change as pre-existing. This happened once already.
- No forward references to a section that does not exist. The engine's LLD gained
  a dangling "see §10.6" that way.

## Stored numbers are claims, not measurements

A number in a document is re-derived or it is deleted. The engine's review file
carried 20 "N tests pass" banners, all stale, and the figure was never
re-measured for the life of the file.

- State the population a count was taken over. The engine publishes
  `unclaimed_source_sections: 0` beside `source_sections: 12` — two different
  12s, numerator over 8 — and it reads as 100% coverage.
- A count with no denominator is a lie that looks like a pass.
- Prefer the measured form to the configured one, and say which you mean.
- Ink-density and row-extent are not the same measurement. For the engine's MP4:
  **3.8%** mean ink-pixel density over 65 frames, versus **69.2%** mean
  bounding-box extent. Both are correct; only the first says how much is on
  screen. The deck's body fill (40.5–89.4%, mean 63.4%) is a third measurement
  again, and its disposition is disputed in the engine's ledger §E1.

## Rendered evidence is available on this box

`soffice` (LibreOffice 26.2.5.2) and `pdftoppm` (poppler 26.01.0) are installed,
so findings may be attributed to rendered pixels. Give `soffice` a private
profile when converting, or a second invocation silently no-ops:
`-env:UserInstallation=file:///tmp/lo_profile_<unique>`.

## Which reviewer to use

Each role may only use the evidence it is scoped to. Do not ask one to do
another's job — that is how a fix lands in one place and misses the other.

| role | evidence | use for |
|---|---|---|
| `viewer` | the rendered video **in sequence** | whether the lesson *lands* — the channel contract, and pedagogical order. **The only role with a human at the other end** |
| `pipeline-architect` | artifacts vs each other, no render | provenance, drift, timing, coverage claims |
| `graphic-reviewer` | rendered pixels (`soffice`/`pdftoppm`) | anything that only *looks* wrong — including whether the output is publishable |
| `tester` | L1 gates + ffprobe/ffmpeg | narration contract, loudness, duration, media |
| `reviewer` | prose claims vs `file:line` | docs accuracy — explicitly **not** whether code works |
| `code-reviewer` | the source itself | duplication, dead paths, complexity |
| `mentor` | all of the above, plus product calls | rulings and trade-offs |

**Three boundaries the `viewer` must not cross.** Truth belongs to the grounding
gates and `FR-006`/`FR-007`; layout belongs to `graphic-reviewer`; command
provenance belongs to `CHECK-CMD-001`/`A32`. A lesson can be *beautiful and
wrong*, or *true and unteachable* — `viewer` is the only role that sees the
second failure, and it is worthless if it starts relaying the others' findings.

## Facts that will bite you

- **There is no code here yet.** `src/doc_to_video_channel/__init__.py` is one
  66-byte stub, there is no `tests/` directory, and the gate is this project's own:
  `.venv/bin/ruff check src tests && .venv/bin/mypy src && .venv/bin/pytest`.
  `ruff check src tests` **currently exits 1** with `E902 No such file or
  directory` because `tests/` does not exist, and `pytest` reports `no tests
  collected` — so `AC#2` fails today and Phase 0 has three items, not two.
- **`.venv` is a real venv, and it cannot import the engine.** There is no
  dependency on `doc-to-video-tutor` — `uv.lock` holds 0 references, and that is
  deliberate (owner ruling 2026-09-28, `docs/LLD-tutorial-lane.md` §14.1). The
  earlier version of this bullet said `.venv` was a symlink to the engine's
  interpreter and that it was the only one that could `import doc_to_video_tutor`;
  both halves were false and the second produced exactly the misleading
  `ModuleNotFoundError` this file warns about. **The instruction stands: use
  `.venv/bin/python`, never bare `python3`** — the engine's own tests, when you
  need them, run from `../doc-to-video-tutor/.venv/bin/`.
- **`VENDOR_REF` does not exist yet.** `docs/LLD-tutorial-lane.md` §5.4 routes V-1
  against "the baseline tree at `VENDOR_REF`", and the constant is **created by
  V0** — it has 0 occurrences in the baseline. Until V0 lands, the reference is
  literally `a7d63e0` (`git -C ../doc-to-video-tutor rev-parse --short HEAD`).
- **Anchors into `../doc-to-video-tutor` are a moving target.** That tree has six
  commits of churn since the last time these numbers were verified. Re-resolve
  before citing.
- **No narrative source document exists on this machine.** `find -iname
  "*histor*" -o -iname "*narrativ*"` across the sibling repos returns 0 hits.
  Every claim about History / car-evolution / forest-growth behaviour is
  `UNVERIFIED` until a real document of that kind is supplied. Do not let a
  synthetic fixture stand in for one without saying so.
- **The engine has two renderers** — `pptx.py` and `slides.py` — and a fix has
  silently missed the other one four times. Any layout change crosses both.
- **Ordering matters.** Several engine defects were a pass that ran *after*
  another pass and so saw a stale plan. If a pass mutates state another depends
  on, order it first or re-run the dependent pass.
- **The engine's narration is gated for the wrong thing.** `mhe-mix`'s
  pure-English check returns an identical verdict on correct English and on
  gibberish, and it never reads the narration for truth at all. See
  `docs/DESIGN.md` §1 — this is the blocker for the whole project.
