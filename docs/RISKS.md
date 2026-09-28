# RISK REGISTER

Written 2026-27-09. Every row is either a **measurement** or an explicit
**assumption**. Impact and probability are judgements; the evidence column is
not. Owner is a module or a person, not a team we do not have.

Two rules from this project apply to this file: a stored number is re-derived or
deleted, and a risk with no evidence column is a guess wearing a table.

---

## 1. The top three

| ID | risk | why it is first |
|---|---|---|
| **R-01** | **A published video states something false and nothing catches it** | no gate reads the narration for truth. Measured: a fabricated date and a fabricated actor both return `grounding: clean, render-blocking: clean`. **Not fixable by any other means** — it is the whole of `FR-006`/`FR-007` |
| **R-02** | **The rights position is unwritten, and it gates every publication** | no `LICENSE`, no `NOTICE`, no `license` field, zero consent strings. The corpus needs one sentence — [`RIGHTS.md`](RIGHTS.md) §0 — and it does not have it |
| **R-03** | **Review cost.** 911.6 s per video, 91% of it render | this is a **proxy** from mtimes, not recoverable from any artifact. It sets the ceiling on how many videos a week are possible, and it is the number most likely to be wrong |

## 2. The register

| ID | risk | I | P | evidence | mitigation | owner |
|---|---|---|---|---|---|---|
| R-01 | A false claim ships | H | H | fabricated date + actor → `grounding: clean` | `FR-006` + `FR-007`; reject never repair | planning |
| R-02 | ~~Rights unwritten~~ **resolved by exclusion, pending its gate** | H | **certain** | 0 `LICENSE`/`NOTICE`/`license`; 0 consent strings. The corpus is now **excluded** (`RIGHTS.md` §0) — resolved by *removing* the material, not by clearing it | `FR-028` must enforce it, or the ruling is a comment | product owner |
| R-03 | Render cost caps throughput | M | certain | 828 s of a 911.6 s build, **mtime proxy** | `NFR-001` resume manifest reclaims it | renderer |
| R-04 | Captions vanish silently | M | **certain** | measured `cues=0, file=False, log=''` behind `if vtt_cues:` | `NFR-004`: fail on zero cues, **~15 LOC** | audio |
| R-05 | Supplied audio ships at the wrong level | M | **certain** | −22.3 LUFS supplied → ships under `verdict: PASS` | `FR-012` audio contract gate | audio |
| R-06 | Data leaves the machine unannounced | H | **certain** | TTS → Microsoft hard-wired; 0 disclosure strings; no `disclosure` field | `NFR-006` | platform |
| R-07 | Source text steers the model | H | M | `plan.py:2219` raw concat, no delimiter; output *is* schema-validated so it can steer but not smuggle code | `FR-022` + `FR-008` | platform |
| R-08 | A secret appears in a recorded frame | H | M | a terminal is where keys leak; not a gate today | `FR-017` | creator |
| R-09 | Prompt edit silently disables a guard | M | M | **measured**: renaming `Example style` empties `_BANNED_NGRAMS` with no error, and `_opening_template_hit` returns `False`. Zero tests cover it | make the `if` a `raise`; test `len(_BANNED_NGRAMS) >= 1` | planning |
| R-10 | A build cannot be reproduced | M | **certain** | **0 of 133 plans** carry a model key; no prompt version exists; `_SCHEMA_VERSION` is write-only with no reader and no test | `FR-025`; copy the `narration_voice.fingerprint` pattern | platform |
| R-11 | The two renderers drift again | M | **certain** | a fix has landed in one and missed the other **4 times**; 2 monolithic renderers, 4 shared imports | `NFR-007`; the R1 consolidation | renderer |
| R-12 | Source text is silently truncated | M | **certain** | 37% of the one document ever ingested; a 90-min transcript would lose ~84% | `FR-003` | ingestion |
| R-13 | The audience axis makes the product unbuildable | M | certain | 8 of 12 age-band × rhythm combinations are `feasible: 0`; the 20-word floor forces a ≥11.19 s scene | defer all audience work to Wave 5 | product |
| R-14 | Song / lyric is attempted | — | low | **forbidden**: 78 of 87 chorus sentences deleted; the deleting pass has no `protected` parameter; no external-audio path | it is not on any roadmap | product |
| R-15 | The scope grows again | H | **certain** | 4 of 5 content types are blocked; the temptation is to build all five | one lane; a feature ships only with a user story and acceptance criteria | product owner |
| R-16 | Review silently costs more than building | M | M | measured 215 toolcalls / 42 min for one build | `*.verify.json` per build (shipped); `NFR-009` stage timings | process |
| R-17 | 1080p raises cost before it raises legibility | L | certain | +31% build time, and one font size measures 97% of threshold for a 3-year-old and **37%** for a 70-year-old | decide after Wave 2, after the type scale | renderer |

## 3. Retired, and why — do not re-open

| was | retired by |
|---|---|
| "cinematic AI video would improve the channel" | $5,071 for 65 videos, and it replaces the *information* layer with decoration. Any frame carrying a fact must be deterministic |
| "local video generation is worth trying" | 4.8 GiB total, 1.9 free, no GPU. Not slow — **infeasible** |
| "score scenes by importance/novelty/audience" | 2 of 6 axes deterministic, neither carries weight, and no gate can check a self-rating |
| "map-reduce the source first" | moves the ceiling one call; a median segment is 1,200 chars against a 12,000-char window |
| "the 20 test-count banners were a useful record" | 18 of them, all stale (claimed 213–228; collected **315**) |

## 3a. CHECK-CMD-001 — closed, and the answer needs a sixth status

Perplexity proposed five labels. The truth needs one more: **the control exists,
and it is insufficient.** That is a different defect from *the control is
missing*, and it takes a different fix.

| question | answer, measured |
|---|---|
| what field carries a command? | `code_snippet` — `schema.py:30`, `code_snippet: str = ""` |
| is it in the requirement's vocabulary? | **no.** `claim_id` / `verification_status` / `verified_command` / `shell_cmd` = **0** in all of `src/` and `tests/` |
| who writes it? | the LLM. **no** `scene["code_snippet"] =` assignment exists in `src/` — every hit is a read or a prompt field-list |
| does a gate exist? | **yes, and deterministic.** `plan.py:1090` blanks any `code_snippet` failing `_anchored` — the same test behind the hard gate at `plan.py:1808` and the retry path at `plan.py:2212`/`2277` |
| why did the first grep miss it? | vocabulary. The renderer prints `COMMAND CONTEXT` at `slides.py:458`; the schema says `code_snippet`. **A negative grep on the requirement's own wording is weak evidence of absence** |
| how strong is the gate? | `_anchored` passes at `len(tokens & source_tokens) >= 3` (`plan.py:885-895`). A command *is* a short bag of tokens: `uv pip install requests` clears the bar against any source mentioning those four words anywhere |
| does it reach the video? | yes — `slides.py:446`, `pptx.py:476,740`. Syntax-coloured, 8 lines max |

**Perplexity's fail condition is met** — a command produced only by the LLM
reaches a rendered video with no `claim_id` and no provenance record. **Their pass
condition is not.** And "the gate is absent" is **false**, which is why neither
response should have been allowed to write that sentence down.

The worse half is the one nobody asked about: the gate's remedy is to **delete**
the command and print only a count (`plan.py:2434`). In the tutorial lane the
command *is* the content — a legitimate command that trips a 3-token overlap
vanishes from the lesson and the build still succeeds. Per-item detail exists in
`removed`; the console shows a number. Fix is `A32`.

## 4. The two open risks with no mitigation yet

| ID | risk | what is needed |
|---|---|---|
| **R-18** | **We do not know whether viewers will watch any of it.** No document and no local measurement can answer this; it needs published analytics, which cannot exist before publication | a small published pilot, not a larger unbuilt one. Until then every reach assumption is a **bet**, not a measurement |
| **R-19** | **`TUTOR_PROMPT` at `__init__.py:28`** is a fourth prompt with no version and no test. A code reviewer ruled it unreachable from `main()` — which contradicts `quality_review-history.md:1685`'s claim that the legacy path's copies are live | one grep to settle which statement is true, then delete the prompt or document it. Not worth more than that |
