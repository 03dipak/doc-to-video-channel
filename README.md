# doc-to-video-channel

Turning the `doc-to-video-tutor` engine into a **YouTube channel**: many
documents in, many publishable videos out, across arbitrary topics — History,
Car evolution, Scientific discoveries, Product development, The stages of a
forest's growth, The development of an AI model.

The engine lives in `../doc-to-video-tutor` and is not modified by anything here
yet. This folder holds the decisions, until there is code to hold.

| | |
|---|---|
| **State** | Design decided, nothing built. Phase 0 not started. |
| **Blocking input** | **One real narrative document** — see [Open decisions](docs/DESIGN.md#open-decisions). None exists on this machine. |
| **Design record** | [`docs/DESIGN.md`](docs/DESIGN.md) — the consolidated ruling, with measurements |
| **Retrospective** | [`docs/scratch.md`](docs/scratch.md) — what we got wrong in the engine, and the pattern behind it |
| **Doc strategy** | [`docs/DOCS.md`](docs/DOCS.md) — the test for writing a document at all, the method, **the four we write and the fifteen we refuse** |
| **Requirements** | [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) — FR-001..FR-027 from the ledger, and NFR-001..010 **as measured: 7 violated, 3 aspirational**, with the cheapest fixes |
| **Rights & security** | [`docs/RIGHTS.md`](docs/RIGHTS.md) — the policy that did not exist: attestation, the four surfaces, the software-vs-artefact licence rule, cloud egress, untrusted source text |
| **Risk register** | [`docs/RISKS.md`](docs/RISKS.md) — 19 risks, each with evidence or an explicit assumption; plus what is retired and must not re-open |
| **Plan of record** | [`docs/PLAN.md`](docs/PLAN.md) — **start here to execute**: the lane, the use case, the I/O contract, the architecture, the free sources, five build waves, and what we refuse |
| **Decision ledger** | [`docs/DECISIONS.md`](docs/DECISIONS.md) — every external input, adopted / rejected with the number, and the list of what actually gets added |
| **Inputs under evaluation** | [`docs/SLIDE-DESIGN.md`](docs/SLIDE-DESIGN.md) — an external slide-type/visual-design proposal, assessed; **not adopted** |
| **Engine baseline** | `a7d63e0`, 315 tests, ruff + mypy clean |

## Start here

1. Read `docs/PLAN.md` §7 *Build order*. It assigns all 27 ledger items to five waves, each with a done-when.
2. Read `docs/scratch.md` §1. The engine cannot currently tell a true video
   from a false one, and that is the only thing that cannot be fixed after
   publication.
3. Then ask the three questions in `docs/DESIGN.md` § *Open decisions*.

## What is deliberately not here

- No code. The three highest-value changes are ~12 lines, ~70 lines and ~30
  lines; writing them before the blocking document exists would be building
  against a synthetic fixture.
- No copy of the engine. `docs/DESIGN.md` names symbols and `file:line` in
  `../doc-to-video-tutor/src/doc_to_video_tutor/studio/`; those are anchors into
  a moving tree and must be re-resolved, not trusted.
- No vendored transcripts. The corpus is 18 `.docx` files owned by
  `../rag-apidriven-pipeline/data/transcripts/`.
