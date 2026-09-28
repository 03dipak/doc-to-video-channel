# DOCS — what we write, and the rule for writing it

Written 2026-09-27, after a doc-tree survey of a 19-document SDLC proposal.
**This file exists to stop us writing 19 documents. Its main output is a list of
things we are deliberately not writing.**

---

## 1. The test for whether to write a document at all

A document earns its place only if **all three** are true:

1. **A change would falsify it.** If nothing we are about to build would make it
   wrong, it is a description, and descriptions belong in the code.
2. **It cannot be derived from a document that already exists.** Duplication is
   how a tree rots: `docs/CALL-FLOW.md` is the proof — 51 unique anchors, none
   pointing at the right line.
3. **Something will read it.** A human, a reviewer, or a gate. If no consumer is
   named, it is a note, and notes go in a commit message.

Against that test, the 19 proposed documents reduce to **4 that we write**, of
which **1 is not yet due**.

## 2. The method

Every rule here exists because it was broken, in this project, and the breakage
is recorded in [`scratch.md`](scratch.md).

| # | rule | the mistake it prevents |
|---|---|---|
| 1 | **One ledger, not a tree.** `DECISIONS.md` §1 is the spine; every document references item IDs and restates no number | a second source of truth that drifts within a week |
| 2 | **Every number carries its basis** — `measured` · `proxy` · `assumption` | the render split quoted as measured when it is an mtime span nobody can re-derive |
| 3 | **Symbols, not lines.** A `file:line` is a search hint with a shelf life | 12 wrong citations in one documentation pass |
| 4 | **Re-read a doc after editing the doc it tracks** | an entry citing its own change as pre-existing |
| 5 | **A check only ever shown a true statement is untested** (`AGENTS.md` rule 8) | 315 tests and a suite that passes a fabricated date |
| 6 | **Resolve all citations in a batch, never a sample** | four mechanical breaks in a single pass |
| 7 | **Check what a marker file actually *holds* before citing it** — a name suggests what it records | `Zone.Identifier` cited as proof of a download; all 18 held no `HostUrl`, and 185 more sat beside the owner's own hand-written `.py`. A marker on your own source cannot mean *downloaded* |
| 8 | **No forward reference to a section that does not exist** | a "see §10.6" that was never written |

## 3. The four documents we write

| doc | repo | due | what it must answer |
|---|---|---|---|
| `RIGHTS.md` · `REQUIREMENTS.md` · `RISKS.md` | channel | **done** | attestation, the four surfaces, FR-001..027, NFR-001..010 as measured, 19 risks with evidence |
| `docs/PLAN-tutorial-lane.md` | channel | **done** | the tutorial lane's build order, and why `PLAN.md` §7 Wave 1 is rescoped: this lane's blocker is command provenance (`A22`/`A32`), not date grounding (`A1`/`A2`) |
| `docs/LLD-tutorial-lane.md` | channel | **done** | the `TopicProfile` seam, the adapter's 8-tuple, and the command-provenance gate. A **narrow exception to this table** — see the note below |
| `docs/ARCHITECTURE.md` → **folds into `PLAN.md` §5** | channel | **Wave 0** | C4 context + container, and **which components are deterministic and which are probabilistic**, marked explicitly. Claude's best point and we have it nowhere |
| `docs/STATE-MODEL.md` | channel | **Wave 3** | the job state machine and its `FAILED_*` states. `A13` per-scene resume and the manifests are both built on it, so it is due exactly when they are |
| `docs/PROMPT-CONTRACTS.md` | **engine** | **Wave 1** | for each of the **four** prompts: purpose, inputs, output schema, forbidden behaviour, validation, fallback, fixtures. This is what makes `A28` mean something — a versioned prompt nobody can review is not governed |
| `docs/GLOSSARY.md` | channel | any time | the acronyms. `WPM`, `LUFS`, `VTT`, `CBR`, `I2V`, `n-gram`, `reveal variant` — the other documents are unreadable without it, and it is the cheapest thing on the list |

**On the heading's "four".** That figure was taken before 2026-09-28 over an
ambiguous population — the table below it has **7 rows** and its first row names
**3** files. The row count is the measurable one; the prose number is not
derivable, so per rule 2 it is stated as a row count and the old figure is
dropped rather than carried forward. *(Two rows — the tutorial-lane pair — were
added 2026-09-28.)*

**The exception, stated rather than smuggled.** §3 originally assigned the LLD to
the **engine** and §6 ruled that *"Wave 0 is unblocked and needs no new
document."* `LLD-tutorial-lane.md` departs from that, and the departure is
recorded here so it is a decision and not drift. It earns its place against
§1's three-question test: a change would falsify it (a seam written as prose
cannot be refactored against); it is not derivable from `PLAN.md` §5, which names
the symbols but gives no refactor, no tuple contract and no gate algorithm; and
Phase 1 and Phase 3 read it. Its scope is correspondingly narrow — canvas, colour,
type scale, orchestration, and the layout contract stay where §3 and §4 put them.


## 4. The fifteen we refuse

| proposed | why not |
|---|---|
| project charter | `PLAN.md` §1–§3 already carries vision, lane and use case. The only missing part is **§"The bet"** — an explicit statement of what we do not know (`RISKS.md` R-18). That is 5 lines, not a document |
| PRD / BRD | `PLAN.md` §1, §3, and the release gate in `REQUIREMENTS.md` §4 |
| personas & journeys | two use cases exist, both in `PLAN.md` §3. A persona document for a one-person channel is fiction with headings |
| SRS | `REQUIREMENTS.md` **is** the SRS |
| scope & roadmap | `PLAN.md` §7 (five waves) and §8 (nine refusals) |
| data models & JSON schemas | `LLD` §6 and `studio/schema.py` |
| pipeline & orchestration | `LLD` §13, `CALL-FLOW.md` §2, `PLAN.md` §5 |
| testing & quality gates | `AGENTS.md` rule 8 plus `REQUIREMENTS.md` §4 |
| observability & failure handling | the report half exists (`*.verify.json`, written on blocked paths too); the state model becomes `STATE-MODEL.md` at Wave 3 |
| video & graphic design system | **deferred.** We have no thumbnail and no type scale; a design system written now would be written against a template we are about to change |
| audio & voice policy | `DECISIONS.md` §14 |
| deployment guide | one box. `render.yml` is the whole deployment surface |
| release plan | no releases exist |
| ADR log | `DECISIONS.md` **is** 16 sections of accepted-and-rejected-with-the-number |
| `schemas/`, `prompts/`, `tests/` re-layout, `examples/` | `schemas/` = churn, the models are already Pydantic. `prompts/` = the gain is **one version constant**, not a directory. `tests/` re-splitting = pure motion that breaks every pinned test name in the ledger. `examples/` = genuine, but nothing to put in it until the first video exists |

Also absent and worth knowing: `CHANGELOG.md`, `LICENSE` and `CONTRIBUTING.md` —
the proposal assumed all three exist. None do. `LICENSE` is on the rights list.

## 5. A second proposal, and why most of it is a template

An **IEC 29148**-framed list of 12 documents arrived after the 19-document survey.
It is the same genre and the same verdict, and one measurement settles it:

> `grep -c "class <T>" src/` for `VideoBrief`, `EvidenceMap`, `Storyboard`,
> `Scene`, `VoiceProfile`, `QualityReport` — **0 class definitions for all six.**
> The engine has `LessonPlan` and `SlideScene`, plus a `grounding` block and
> `*.verify.json`. `VideoBrief` and `EvidenceMap` appear **nowhere** in `src/`.

So item 7 of that list asks us to "define strict structures for" six types that
do not exist, "before LLM integration" — on a system that has been integrating
LLMs for 30 commits. **Following it literally would mean inventing a data model
and then calling it documentation.** That is the three-question test in §1 applied
to the proposal itself, and it fails on question 1.

| proposed | disposition | lives in |
|---|---|---|
| Project Charter | fold into `PLAN.md` §1–§3 + §8 | channel |
| PRD | fold into §1, §3, §7, plus user stories as acceptance criteria on each ledger row | channel |
| Scope and Roadmap | **already** `PLAN.md` §7 (five waves) + §8 (nine refusals) | channel |
| Functional Requirements | **already** `REQUIREMENTS.md` §2 — FR-001..027 | channel |
| Non-Functional Requirements | **already** `REQUIREMENTS.md` §3 — NFR-001..010, as measured | channel |
| System Architecture | add to `PLAN.md` §5: C4 context+container, and **deterministic vs probabilistic marked** | channel |
| Data Model / JSON Schema | **already** `LLD` §6 + `studio/schema.py` — and §5 above corrects the type names | engine |
| LLM Prompt Contract | `A28` + `A29` → `PROMPT-CONTRACTS.md` (Wave 1) | **engine** |
| Video & Graphic Design System | **split.** A *layout contract* (what the renderer guarantees and refuses) is writable now; the canvas / colour / type-scale system waits for the 1080p decision (`RISKS.md` R-17) | engine |
| Testing & Quality-Gate Plan | **already** `AGENTS.md` rule 8 + `REQUIREMENTS.md` §4 | channel |
| Security / Privacy / Copyright / Voice | **already** `RIGHTS.md` — all eight sections | channel |
| Risk Register + ADR Log | **already** `RISKS.md` (19) + `DECISIONS.md` (30 rows, 16 sections) | channel |

**Its "minimum mandatory 7" therefore contains 0 new documents**, and 3 of the 7
are the Wave 0/1 items already logged. The proposal also names **"unverified
commands"** as a blocker. `FR-016` already states the rule — *a command carries a
`claim_id` and a provenance record; it is never model output* — and a grep of
`validate.py` returned **no** `command` reference. **That grep was too weak, and
the widened search closed the check — see `RISKS.md` §3a, fix `A32`.** The control exists;
it is a *different* control from the one the wording implies, and it is
insufficient. `claim_id`, `verification_status`, `verified_command` and
`shell_cmd` return **0 hits across all of `src/` and `tests/`**, yet a
deterministic gate does run at `plan.py:1090`. The first grep missed it on
vocabulary alone: the renderer labels the panel `COMMAND CONTEXT`
(`slides.py:458`) while the schema calls it `code_snippet`.

On the standard itself: IEC 29148 is written for safety-critical and general
enterprise systems and requires a **tailoring record** — an explicit statement
of which artifacts a project does *not* produce and why. It does not require the
full set. `DOCS.md` **is** our tailoring record. Traceability is already carried by
the ledger: requirement → wave → done-when, with a release gate that fails the
build.

## 6. The verdict

**Wave 0 is unblocked and needs no new document.** Its acceptance criteria are
already written (`REQUIREMENTS.md` FR-001..005), its risks are registered, and
its rights position is settled. Writing anything further before starting would
be the failure mode the proposal itself warned against.
