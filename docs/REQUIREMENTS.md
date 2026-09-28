# REQUIREMENTS — functional and non-functional

Written 2026-09-27. Derived from the 27-item ledger in
[`DECISIONS.md`](DECISIONS.md) §1 and a measured audit of the ten proposed
non-functional requirements. **Nothing here is aspirational unless marked.**

---

## 1. How to read this

- **FR-xxx** — functional. Each is one ledger item, with a checkable
  acceptance criterion and the wave it lands in.
- **NFR-xxx** — non-functional. Each is **MEASURED VIOLATED**, **PARTIAL**, or
  **ASPIRATIONAL**, with the evidence and the smallest check that would fix it.

Seven of the ten NFRs are **currently violated**. That is not a criticism of the
proposal; it is what a baseline measurement looks like before a fix.

## 2. Functional requirements

### Wave 0 — the front door. *Nothing exists without these.*

| ID | requirement | acceptance criterion |
|---|---|---|
| **FR-001** | `.docx` is a supported input | all 18 corpus files load; a `.docx` no longer raises `UnicodeDecodeError` |
| **FR-002** | Unsupported input is **refused at the door** | an unknown extension raises one clear line **before** any LLM call. `LLD:51` already commits to "fail loudly and early" |
| **FR-003** | The read window is settable, and the omitted fraction is reported | `--read-window` exists; `chars_read / chars_total` is beside the coverage counts, not only on stdout |
| **FR-004** | Prose without headings is segmented by paragraph | a source with no `^#{1,3}` yields **one section per paragraph**, not a single 1,200-char pair. *Measured today: 1 of 6 scenes gets a `source_chunk`; after, 6 of 6* |
| **FR-005** | The rotted reference file carries a standing header | `CALL-FLOW.md` states its anchor state (51 unique anchors; symbol→line pairs do not resolve) so no fix cites it blind |

### Wave 1 — a gate that means something. *The blocker.*

| ID | requirement | acceptance criterion |
|---|---|---|
| **FR-006** | Grounding reads `narration` | a fabricated date in `scenes[*].narration` is **rejected**. *Measured today: `grounding: clean, render-blocking: clean`* |
| **FR-007** | Entity + temporal grounding, and date order | dates in the narration must exist in the source; the per-scene date sequence is non-decreasing. **Reject, never repair** — repairing deletes the date and manufactures a wrong-but-passing video |
| **FR-008** | The LLM can declare a gap | a `needs_user_input` item is emitted instead of a guess. *Today a missing fact is filled silently, which is why FR-006 is needed* |
| **FR-009** | `source_refs` is removed or renamed | it is model-authored and **wrong in 2 of 8 scenes**, contradicting its own `source_assignment` |
| **FR-010** | Coverage publishes the population it was counted over | the count becomes a **list** of segments with an unclaimed *reason* |
| **FR-011** | Caller-supplied audio is accepted | `--audio-dir` with exactly `clip_count(N)` files; files are **copied** into the work dir (`_normalize_loudness` is destructive in place) |
| **FR-012** | An audio contract gate exists | per-clip ffprobe (count, duration, codec) + ebur128 vs target; the 20/90-word band re-expressed in **seconds**; a **caption gate that fails loudly**. *Measured today: a −22.3 LUFS clip ships under `verdict: PASS`; captions go 55 → 0 with no log line* |

### Wave 2 — publishable output

| ID | requirement | acceptance criterion |
|---|---|---|
| **FR-013** | Three on-screen leaks removed | the literal word `opening`; `BRAND_NAME = PACKAGE_NAME`; the positional eyebrow enum `spread[(idx-2)%4]` |
| **FR-014** | A **media box**: one reserved rect per scene taking a still, a clip, or a file tree | composited at `assemble_video`, so the reserved-space invariant is untouched. *Full-bleed is a measured **pixel no-op**; with a scrim every chrome element falls to 1.05:1* |
| **FR-015** | An asset-existence gate | a scene referencing a missing asset **fails loudly**. *Precedent: caller-preplaced audio in `output/<name>_audio/` is silently overwritten and the build reports PASS* |
| **FR-016** | Commands are verified source data | a command carries a `claim_id` and a provenance record; it is never model output |
| **FR-017** | Screen-capture secret hygiene | a checkable check for API keys, usernames, home paths, private filenames in a recorded frame |
| **FR-018** | Chapters exist | `0:00 Title` markers emitted — **0.00 in** of body budget |
| **FR-019** | A partial cut is disclosed | a disclosure line, **4.880 in of an 8.50 in** footer box |

### Wave 3 — iteration

| ID | requirement | acceptance criterion |
|---|---|---|
| **FR-020** | Per-scene artifacts and regeneration | scene 4 re-renders without touching scenes 1–3. *The repair chain has no per-scene address today* |
| **FR-021** | A third text channel | `caption_text` is an authored field, not derived from narration |
| **FR-022** | Document text is data, never instructions | source is delimited, marked as data, and a conflicting instruction routes to FR-008 |

### Wave 4 — the channel

| ID | requirement | acceptance criterion |
|---|---|---|
| **FR-023** | Three manifests | corpus · video row · channel index, joined on `segment_id` |
| **FR-024** | `claim_id` and `source_segment_ids[]` exist | "which material has no video yet" becomes a **query**, not a claim a build writes about itself |
| **FR-025** | The plan names its producer | `llm.model` and a **prompt fingerprint** in `*.plan.json`. *Measured: **zero of 133 plans** carry a model key, while the TTS provider is recorded. The probabilistic half records nothing* |

### Wave 5 — deferred, not v1

| ID | requirement | status |
|---|---|---|
| FR-026 | `TopicProfile` + adapter + audience profiles | deferred — `narration.py`/`voice.py` need **zero** changes for it |
| FR-027 | Vertical MP4 | deferred — usable width −46.7% against body budget **+112%**; a second layout, and the deck half is unnecessary |

### Wave 1 — the rights gate

| ID | requirement | why it is not a comment |
|---|---|---|
| **FR-028** | **A source allow-list.** A build whose source resolves inside an excluded path **fails loudly**; a flag marks a test-fixture build as non-publishable | `RIGHTS.md` §0 excludes the 18 course transcripts from publication. A ruling with no gate is a comment, and **a documented rule this repo never enforced is the exact defect class of CHECK-CMD-001** — so this one gets a gate and a test in the same wave. Cheapest form: compare each resolved source path against `EXCLUDED_SOURCE_PREFIXES`; refuse unless `--test-fixture` is passed, and stamp that flag into the plan and the release report |

The point of measuring the gate on the *excluded* path first: a check only ever
shown a true statement is untested (`AGENTS.md` rule 8).

---

## 3. Non-functional requirements — as measured

| ID | requirement | status | evidence / smallest fix |
|---|---|---|---|
| **NFR-001** | a failed scene is retried without redoing completed ones | **VIOLATED** | `render_scenes` re-renders every page and variant; a re-run burns the full 828 s. *Fix: a `render_manifest.json` keyed by `(plan_sha256, page, reveal)` that skips existing PNGs. ~30 LOC + 1 test* |
| **NFR-002** | low-resolution preview before full HD | **VIOLATED** | `video.py:713` hardcodes 1280×720; zero resolution flags in 27 CLI args. *A policy problem, not a number — defer until both renderers share a scale scalar, or the four-times-repeated drift returns* |
| **NFR-003** | a beginner can make a first storyboard without coding | **ASPIRATIONAL** | needs a usability study and a seeded corpus. Offline `review` on a saved plan already exits 0 |
| **NFR-004** | every video offers captions and a transcript | **VIOLATED** | measured `cues=0, file=False, log=''` — silent, behind `if vtt_cues:`. `verdict: PASS` still written. *Fix: read the `.vtt` back into `verify.json` and FAIL on zero cues. **~15 LOC + 1 test — best value on this list*** |
| **NFR-005** | source text is not treated as instructions | **ASPIRATIONAL / VIOLATED** | no delimiter, no data framing (`plan.py:2219`); output *is* schema-validated, so injected text can steer content but cannot smuggle code. Needs an adversarial corpus to test |
| **NFR-006** | disclose when source leaves for a cloud provider | **VIOLATED** | zero privacy strings in the docs; no disclosure field in `verify.json`; source **and** full narration go to Microsoft unannounced. *Fix: emit `disclosure: {llm_host, tts_host, source_bytes_sent, narration_bytes_sent}`. ~20 LOC + 1 test* |
| **NFR-007** | scene types are reusable renderer modules | **VIOLATED** | 2 monolithic renderers (283 and 347 lines), zero scene-type modules, 4 shared imports, absolute character-count wrap widths |
| **NFR-008** | runs on Windows without CUDA | **ASPIRATIONAL / UNVERIFIED** | CI is `ubuntu-latest` only; zero `sys.platform` branches in `src/`. The no-CUDA half is probably fine, equally unverified |
| **NFR-009** | every job has stage logs **and** a quality report | **SPLIT: report PASS, logs VIOLATED** | `*.verify.json` is rich and written on blocked paths too. But there is no `logging` in `src/`, and no elapsed/stage key — so the render split is **not recoverable from any artifact**. *Fix: `time.monotonic()` per stage into `verify.json`, test `abs(sum(parts) − total) < 1.0`. ~25 LOC* |
| **NFR-010** | the core workflow runs local / open-source | **VIOLATED** | all deps are OSS and `review`/`verify`/`render` run offline — but `build` cannot: TTS is a cloud client with no local backend, and `LLM_BASE_URL` defaults to `""` |

**The five cheapest checks** — NFR-004, 009, 006, 010, 001 — total **~110 LOC
and 5 tests**, under a day, no network. Three of them turn a **silent zero**
into a red build.

## 4. The release gate

Nothing is published until all of these are true, and each is a reading, not a
configuration:

1. `verify.json` `verdict` is `PASS` — and captions exist.
2. No fabricated date or command survives (**FR-006**, **FR-016**).
3. The rights attestation is written ([`RIGHTS.md`](RIGHTS.md) §0).
4. No secret is visible in any frame (**FR-017**).
5. The data-egress disclosure is present (**NFR-006**).
6. A legible thumbnail exists — one element, ≥7.4 px cap at 210 px.
7. The plan names its model and prompt fingerprint (**FR-025**).

---

## 5. Measured coverage gaps

An external catalogue proposed ~150 numbered test cases and a traceability
matrix. Both were measured against the suite before being accepted, and the
useful part is this section rather than the new files. **A gap is a requirement
with no test, not only a failed test** — that is `AGENTS.md` rule 8 restated, and
it is the one idea worth keeping from the proposal.

This is a **measured sample, not a full FR→test matrix.** Mapping all 28
requirements against 307 test functions is not something I have read line by line,
and it is not claimed here.

| requirement | what was measured | verdict |
|---|---|---|
| `FR-016` command provenance | `claim_id` = **0** in all of `src/` **and** all of `tests/`. The 14 provenance hits are the audit digest, not the command | **no test, no implementation** — `A32` |
| `FR-022` untrusted source text | **0 of 7** test files touch injection; `plan.py:2219` raw-concats `content[:2500]` with no delimiter | **no test** — `A40` |
| pronunciation rules | **23** `speech_expand` assertions across 2 files, but `pyproject` = **0**, `README` = **0**, `uv` = **0** | framework tested, **the terms are not** — `A38` |
| PDF ingestion | `pdf` = **0**, `OCR` = **0**, `tesseract` = **0** in `src/`. Supported inputs are `.md, .txt, .pptx` (`cli.py:359`) | **not a gap in the suite — a capability that does not exist** |
| multilingual (hi-IN / mr-IN / MHE) | `config.py:124` forbids non-Latin script in any slide-visible field | **ruled out by design**; those cases test a lane we declined |
| 9:16 vertical output | `FR-027` deferred — usable width −46.7% against body budget +112% | **deferred, correctly** |
| voice clone consent | `DECISIONS` §14, mode 3, v1 = recorded | **future path**, not a v1 gate |

**The pattern across the proposal:** roughly a third of its catalogue tests
PDF/OCR, multilingual, 9:16 and voice-cloning — capabilities this engine has
either never built or deliberately ruled out. Writing those as test cases would
manufacture a permanent red suite for features nobody has agreed to build. A
test for an unbuilt capability belongs on the roadmap, not in the gate.
