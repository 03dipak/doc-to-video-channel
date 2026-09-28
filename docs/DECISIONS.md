# Decision ledger — every external input, adopted and rejected

**One place.** Three external inputs have been assessed: Claude.ai (two paths),
Perplexity (hierarchical map-reduce), and Perplexity (slide-type / visual
design). Detail lives in [`DESIGN.md`](DESIGN.md) and
[`SLIDE-DESIGN.md`](SLIDE-DESIGN.md); this file is the verdict index and the
list of what actually gets added.

Status 2026-09-27, `doc-to-video-tutor` at `a7d63e0`. **Nothing here is built.**

---

## 1. What actually gets added

Unblocked today — no missing document required:

| # | addition | size | why now |
|---|---|---|---|
| A1 | `_grounding_issues` reads `narration`, the field the viewer hears | small | the blocker: it currently passes a fabricated date |
| A2 | New hard gate: entity + temporal grounding on narration, and non-decreasing date order across scenes. **Reject, never repair** | 1 gate | repairing would delete the date and manufacture a wrong-but-passing video |
| A3 | Three on-screen leaks removed: the literal word `opening` in the title card, `BRAND_NAME = PACKAGE_NAME` in the footer, and the positional eyebrow fallback `spread[(idx-2)%4]` | 3 one-liners | the first thing a viewer reads is a JSON key name; a forest-growth scene is labelled `EXAMPLE` |
| A4 | Chapters artifact — `0:00 Title` markers | small | **0.00 in** of body budget (eyebrow band is 84% empty). `grep -rn "chapter" src/` returns **zero hits** — no code exists |
| A5 | `.docx` reader — a zip, `word/document.xml`, `</w:p>` → newline | ~30 lines | **zero of the 18 corpus files are loadable today** |
| A6 | Paragraph-boundary fallback in `_markdown_sections` | **~12 lines** | measured: 1 of 6 scenes gets a `source_chunk` on prose; this makes it 6 of 6. Highest value per line in the project |
| A7 | `--read-window`, and the omitted fraction reported beside coverage counts | ~3 lines | 37% of the only document ever ingested is silently unread; recorded but read by nothing |
| A8 | Coverage publishes the population it was counted over | data | `unclaimed_source_sections: 0` is published beside `source_sections: 12`, and the two 12s are **disjoint lists** — so a reader divides one by the other. *(Corrected 2026-09-27: I called the field **false**. It is **true** — the pool is the 8 numbered headings and all 8 are claimed. The real defect is that the other 4 sections are excluded by a heading regex, so their coverage is **unprovable from the artifact**, not falsely claimed. A8 stands; my characterisation of it did not.)* |
| A9 | `narrative` **voice** profile — openers, closers, leads, language policy (the *enrichment* half is E2) | small | the `english` profile's leads assert mechanism-plus-use-case, which a history video does not have |
| A10 | `TopicProfile` + the adapter interface (8 returned fields) | ~70 + ~30 lines | the seam; `narration.py`/`voice.py` need **zero** changes, which is the proof this is configuration |
| A11 | LLD §17 criteria 13–18, and a standing header on the engine's `CALL-FLOW.md` — **51 unique anchors, 0 missing files, 0 out of range, but 3 land on blank lines; symbol→line pairs do not resolve** | doc | makes "any document" falsifiable; 0 of 21 CALL-FLOW anchors resolve |
| A12 | Disclosure line for a partial cut — 4.880 in of an 8.50 in footer box | small | free, and a disclosed cut is more honest than a silent one |
| A13 | **Per-scene artifact independence + regeneration** — address one scene, re-render one scene | medium | **the highest-value unbuilt item.** A BA reading the workflow and a code reviewer reading the repair chain converged on it independently (§10.3). Serves the edit loop, and is the prerequisite for the channel fan-out |
| A14 | Treat source document text as **untrusted data, never instructions** (prompt-injection class) | small | the one risk on any list with **no existing control**, and `load_documents` feeds untrusted text straight into the planner prompt |
| A15 | **A hard input-format gate** — allow-list the supported extensions and `raise` on anything else, at the door | ~10 lines | today `util.py:155` sends every non-pptx to `read_text`, so a `.docx` raises `UnicodeDecodeError` **after the LLM call**; 0 of 18 corpus files are loadable. `LLD:51` already commits to "fail loudly and early" |
| A16 | **`--read-window`** (make `max_chars` settable) and report the omitted fraction beside coverage | ~3 lines | 37% of the one document ever ingested is silently unread; 90 minutes would lose ~84% with no override |
| A17 | **`--audio-dir`** — caller-supplied per-scene audio, exactly `clip_count(N)` files | ~33 lines | Mode A's audio half. Must copy into the work dir first: `_normalize_loudness` is destructive in place |
| A18 | An **audio-contract gate** — per-clip ffprobe (count, duration, codec) + ebur128 vs target, behind one gate | ~40 lines | without it, supplying audio makes 3 gate families **meaningless** and lets a −22.3 LUFS MP4 ship under `verdict: PASS` (measured) |
| A19 | **A picture-box compositing path** — one rect per scene carved from the body budget, composite at `assemble_video` | ~15 lines | the only measured working way to put real footage in. Full-bleed `overlay` is a **pixel no-op**; with a scrim every chrome element falls to 1.05:1 |
| A20 | **Delete or rename `source_refs`** | small | model-authored, **wrong in 2/8 scenes**, and contradicts its own `source_assignment` on those same scenes — while being the field a reader trusts most |
| A21 | A **media box**: one reserved rect per scene accepting a still, a clip, or a file tree | ~15 lines + templates | the only measured working way to put real content in a frame, and independently proposed by a video-production input. Unlocks 4 of the 10 tutorial scene types from one primitive |
| A22 | **Commands as verified source data**, never model output — a `command` field with a `claim_id` and a provenance record | small | a command in a tutorial is a factual claim the viewer will **type**. It fails on their machine, in public, on the recorded video |
| A23 | **Screen-capture secret hygiene** as a checkable gate — no API keys, usernames, home paths, private filenames in a recorded frame | ~20 lines | a recorded terminal is exactly where credentials leak. Appears in **none** of the five inputs' risk sections as a gate, only as a checklist line |
| A24 | A **`needs_user_input`** output channel — the LLM declares a gap instead of filling it | small | the cheapest mitigation for the §1 blocker available: a declared gap is a routed question, an undeclared one is a fabricated date that measures `grounding: clean` |
| A25 | **Demo-first ordering** — the user records, then the LLM plans around what exists | small, reordering | makes A22 structural rather than advisory: the recording *is* the verification, so the LLM decides what to explain, not what is true |
| A26 | A **third text channel** — `caption_text` as an explicit field, not derived from narration | small | the engine has two and derives the third; the derivation is exactly what fails for `uv --version`, and §11.4 measured captions collapsing to 0 without word timings |
| A40 | **Prompt injection has zero tests, against a measured unmitigated path** | ~6 tests, ~1 day | measured: **0 of 7** test files touch prompt injection, while `plan.py:2219` concatenates source into the frame as `content[:2500]` with **no delimiter and no quoting** (`SOURCE DOC:\n` + raw text). The output *is* schema-validated, so it can steer the model but cannot smuggle code — but nothing asserts that, so the mitigation is currently an assumption. Note the gate must be proven on the *malicious* fixture first: a mitigation only ever shown a benign document is untested (`AGENTS.md` rule 8) |
| A34 | **Review the MP4, not the deck** — `graphic-reviewer` pulls frames with `ffmpeg` from the rendered video instead of converting the PPTX | ~10 LOC | **measured on `lld_tests_v18`:** `ffmpeg` extracts 8 frames in **1.6 s**; `soffice`+`pdftoppm` takes **7.3 s** for the same 8 — **4.6×**. And the deck is the *wrong medium*: reveal variants and narration sync exist only in the MP4, so a frame from the PPTX cannot show them. `on disk: 53 pptx vs 19 mp4`, so most visual review to date has been done on the artifact nobody watches |
| A35 | **One gate pass, read by everyone** — make `*.verify.json` unconditional, and run L1 gates **first** so a failing build aborts before any visual review | ~25 LOC | `cli.py:833,855` prints the evidence path, but only **6 of 133** plans have one: the three artifact reviewers each re-derive what the build already knew, which is where the toolcalls go. Measured review cost for one build: **215 toolcalls / 42 min** — that is the number to cut, and `soffice` at 7.3 s is *not* in it |
| A36 | **`--skip-deck`; the deck is not on the video lane's critical path** | ~15 LOC | there is `--skip-video` but **no `--skip-deck`** (`cli.py:367,412`), so every build pays for a PPTX: **53 built vs 19 videos**. `FR-027` already ruled "the deck half is unnecessary". **Claim deliberately not made:** how much of the 828 s render this saves. `R-03` is an mtime span, not per-stage timing — get `NFR-009` numbers on one build before optimising the biggest line item blind |
| A33 | **Corpus excluded from publication; the publishable source is the owner's own notes** | gate, ~30 LOC | the 18 transcripts are a paid instructor-led course the owner **attended as a student** — established from the transcript text alone (cohort, live Q&A, breaks, "nine months journey"). I also cited `ZoneId=3` as proof of a download: **withdrawn** — all 18 sidecars carry no `HostUrl`, and 185 more sit beside the owner's own hand-written `.py`, so the marker tracks the copy out of Windows, not the content. The draft attestation I wrote for `RIGHTS.md` §0 asserted he *delivered* them and was **false**. Wave 0 is unaffected — 18 real 90-minute `.docx` files are an excellent **local parser fixture** — and since the owner's notes will be Markdown, which `load_documents` already reads as plain text, **`.docx` support is no longer on the critical path to publishing**; it becomes an optional import. That reorders Wave 0 and needs the owner's call (`PLAN.md` §7) |
| A32 | **Commands carry no source location** — bind `code_snippet` to the admitted source span, and make a *deleted* command **blocking**, not a count | ~40 LOC + 2 tests | **CHECK-CMD-001, closed by measurement.** The field is `code_snippet` (`schema.py:30`, default `""`, so optional); the requirement's own vocabulary is absent — `claim_id`, `verification_status`, `verified_command`, `shell_cmd` = **0 hits in all of `src/` and `tests/`**. The only writer is the LLM's JSON: **no** `scene["code_snippet"] =` assignment exists in `src/`, every hit being a read or a prompt field-list. A gate *does* exist (`plan.py:1090` blanks any unanchored `code_snippet`) and it is deterministic, so "no gate" would have been **false** — the first grep missed it purely on vocabulary. But `_anchored` passes at **3 shared tokens** (`plan.py:885-895`) and a command *is* a short bag of tokens, and no source location is recorded: FR-016's rule is unimplemented while its spirit is partly enforced. **A31 is skipped in this ledger on purpose** — line 221 already cites the *engine's* `A31`, and two ledgers sharing a number is how a citation silently stops meaning what it says |
| A30 | **Fix 8 dangling references to a file that does not exist** — `doc/design/03_lld_tests.md` is cited by `README.md:23,26` (the headline copy-paste example), the shim banner `__init__.py:4-5`, and the *source document* at `modules/08_concepts_mod03_gates.md:4,280`. Measured: the file is absent. A first-time user copy-pastes the README's first command and gets a `FileNotFoundError` | ~5 lines | Wave 0 — a README example that cannot run is the first thing a new user meets. It is also live proof that `source_refs` is model-authored: the shipped plan's `source_refs` cites **this** missing path |
| A28 | **Prompt + model provenance in the plan** — `llm.model` and a sha256 **prompt fingerprint**, copying the `narration_voice.fingerprint` pattern | ~6 LOC + 1 test | measured: **0 of 133 plans** name a model; no prompt version exists anywhere; `_SCHEMA_VERSION` is **write-only** (no reader, no test) and versions the container while leaving the producer anonymous |
| A29 | **Make `_BANNED_EXAMPLE` extraction fail loudly** | ~3 LOC + 1 test | measured: renaming the `Example style` anchor in `STUDIO_PROMPT` empties `_BANNED_NGRAMS` **with no error**, and `_opening_template_hit` returns `False` — the guard that stops the model copying its own example turns itself off on a routine prompt edit. Zero tests cover it |
| A27 | An **asset-existence gate** — every referenced asset exists, is readable, and was not silently replaced | ~15 lines | there is a measured precedent for the failure: caller-preplaced audio in `output/<name>_audio/` is **silently overwritten** and the build reports PASS. The moment A21 lands, this is the same silence one layer up |

Blocked on **one real narrative document**, which does not exist on this machine:

hero image · before/after · timeline · chart · a true labeled-diagram · the
`narrative` profile's enrichment set · validating A2 against real content · the
thumbnail template.

---

## 2. Adopted as proposed

| # | item | source | what it adds |
|---|---|---|---|
| B1 | Do not use one design everywhere; identify the content type first, then choose the visual format | Perplexity 2 | the core insight, and it **independently corroborates** the five-shape finding from a different method |
| B2 | The LLM may choose `slide_type` — **narrowed** to a profile's allowed set, never the content | Perplexity 2 | template selection is a layout decision, not a factual claim, so it is safe to delegate; the strings filling the template stay grounded |
| B3 | Storyboard JSON shape: `scene_id`, `slide_type`, `source_segments` | Perplexity 2 | maps onto `source_segment_ids[]` and the adapter interface |
| B4 | `SLIDE_TEMPLATES` dispatch | Perplexity 2 | in principle. Note the engine already has an unstarted `visual_pattern` dispatch item — same idea, twice |
| B5 | Coverage matrix + `coverage_rate` | Perplexity 1 | **6 of 7 columns map to existing fields**; needs A8 to be meaningful |
| B6 | Modular responsibility split | Perplexity 1 | in part — the validator role. The rest is B7/A10 |
| B7 | Coverage-first as the *direction*; chapter the source, run the existing pipeline per chapter | Claude | gated on a slice selector that does not exist, and on the `source_assignment` partition fix |
| B8 | Three channel artifacts: corpus manifest, video manifest row, channel index | Claude | the load-bearing field is `source_segment_ids[]` — without it there is no edge from a video to the corpus |
| B9 | Six existing block types: `steps`, `flow`, `analogy`, `takeaway`, `value_table`, `status_badges` | Perplexity 2 | no change. They are already the vocabulary |
| B10 | `myth-versus-fact` | Perplexity 2 | **a relabel of `design_decision`**, which already has that exact shape. No new field |
| B11 | **Audience age band as a first-class axis**, six profiles | Perplexity 3 | the best product idea any input has produced, and cheap: `NarrationVoice` is *already* a parameterised profile with a registry and a flag. An `audience_profile` is a second axis on an existing seam |
| B12 | Copyright and licensing rules for a monetised channel | Perplexity 3 | correct, necessary, and **stated nowhere in our docs**. Our own output already carries an unnamed problem: the package name on every frame, and a named TTS voice |
| B13 | Layer 1 content / Layer 2 presentation separation | Perplexity 3 | independently restates A10 — the adapter plus `TopicProfile`. Third party to arrive at the same seam |

---

## 3. Already true — no work, recorded so it is not re-derived

| # | item | source | the fact |
|---|---|---|---|
| C1 | Preserve timestamps / `segment_id` / `evidence_segments` | Perplexity 1 | **the transcripts are timestamped and titled.** I ruled this "inapplicable, no ASR" by reasoning from an LLD; that ruling was wrong. The engine's equivalent also already exists as `section_index` + `section_digest` + `chunk_digest` |
| C2 | "Never silently remove a required point" | Perplexity 1 | already the rule — engine ledger §B2 (no coverage floor) and §B3 (report, do not re-cut) |
| C3 | "Do not let the video model decide what matters" | Perplexity 1 | already held — `_concept_headers` → `MANDATORY_SCENE_FRAME` → one LLM call fills slots. The real gap is that selection is **source-order, not value** |
| C4 | Change the visual treatment every 10–25 s | Perplexity 2 | already exceeded — one reveal variant per bullet gives a change every **4–7 s**. Kept as a symptom of the measured 28 s / 11% near-black runtime, not as a target |

---

## 4. Rejected, with the number

| # | item | source | reason |
|---|---|---|---|
| D1 | **8–14 scenes for a 4-minute video** | Perplexity 2 | the engine's own `word_budget(scenes, 240.0)`: **15 scenes → 19.5 words/clip against a 20-word hard floor, `feasible: 0`.** The hard ceiling is **15 scenes per 240 s** — and the binding constraint is actually the documented cap `AUTO_TRIM_MAX_SCENES = 12`. *(Corrected 2026-09-27: I had published 14 scenes and a 17.1 s minimum, derived from the **measured** 107.276 wpm. The engine's own model uses the **configured** 103.0 (`duration.py:44`), giving 20 words = 11.65 s + 3.0 s gap = 14.65 s marginal, so (240−10)/14.65 = 15.7 → 15. Two rates live in the engine; say which one you mean.)* 11 scenes is exactly the 25-word WARN line. Buildable range is **8–14**, and anything faster than one scene per 17 s is unbuildable *(corrected 2026-09-27: an earlier version of this row attributed 19.5 words/clip to 14 scenes; that is the 15-scene row — `word_budget` returns `clips = scenes + 1`)* **CLOSED 2026-09-27 — the question dissolves.** Ruling: duration is *derived from the source*, not a target and not a ceiling. See `PLAN.md` §4. |
| D2 | **500–580 spoken words in 4 minutes** | Perplexity 1 | measured 107.276 wpm + 37.36 s structural silence → a 240 s MP4 holds **362 words**. The band is +24% to +66% over that. 540 words is a **5 min 39 s** lesson. 450 words needs 252 s of *speech alone* **CLOSED 2026-09-27** — same ruling: the word budget is a consequence of the admitted source, never an input. |
| D3 | **Fail the build if estimated duration > 240 s** | Perplexity 1 | contradicts `duration.py:261-267`: *"the remedy is source-grounded teaching, which no mechanical step can supply."* Would reject all three recent builds (253.6 / 254.6 / 261.6 s) the engine itself labels `OK` inside its own 220.8–276.0 s zone **CLOSED 2026-09-27** — no hard cap is adopted, so this is moot. The band stays advisory and a duration is *reported*. |
| D4 | The weighted scoring formula over importance / audience value / novelty / evidence / visual potential | Perplexity 1 | **unverifiable by construction.** 2 of 6 axes have a deterministic analogue and neither carries weight (0.30 + 0.25 are the two that do not). Every gate works by comparing two independently computed artifacts; these have no second computation to differ from. A new *assertion*, which is worse than a new measurement |
| D5 | Per-chunk structured summaries feeding a master outline | Perplexity 1 | as specified it **moves the ceiling one call** rather than removing it — it sits downstream of the read cut and would summarise the same 11,351 chars. A median corpus segment is ~1,200 chars against a 12,000-char window; nothing needs reducing |
| D6 | 15–30 s chunk overlap | Perplexity 1 | architecturally impossible: assignment is globally exclusive by design (`taken: set[int]`), and that fixed three defects. Overlapping would reopen them |
| D7 | A fixed seconds-per-section budget table (hook 0–15 s, context 15–40 s, …) | Perplexity 1 | a **second** budget arithmetic beside `words_for_target`, which budgets words per clip over `clip_count(n)+1`. Two budget models that disagree is the defect, not the design |
| D8 | `duration_seconds` in the storyboard JSON | Perplexity 2 | invites the model to **assert** a duration. That is the exact class of unverified claim the §1 blocker is about |
| D9 | Near-white background and per-topic palettes | Perplexity 2 | collides with a documented rule, not a style choice: `config.py:322-323` reserves `RED` for FAIL semantics only, never for body text, never paired with green. A forest theme repurposing green, or a before/after slide using red for "bad", breaks it |
| D10 | `body_size 26`, `max_bullets 4` | Perplexity 2 | moves *away* from the measured fix. At ~210 px display the current 23 px title is a 4 px smear and body text has **zero** surviving pixels; the fix is a **2.1×** title, ≤4 words, one line, with the eyebrow and body **deleted** |
| D11 | Path A — hard cap at 4 minutes, always | Claude | three conflicts: the recorded advisory-band ruling (D3); engine ledger §B3 "deterministic repair may not remove teaching material to satisfy a length preference"; and it is the wrong shape for this corpus, where a median segment is **half** a 4-minute video **CLOSED 2026-09-27** — a hard cap is neither target nor ceiling, so the cut-to-4-minutes shape does not arise. |
| D12 | `selection.json` with rank scores and selected/dropped | Claude | no ranking machinery exists, and the rank score would be D4. The **coverage matrix** (B5) is the closer fit and is adopted instead |
| D13 | "Fits your existing architecture as-is" | Claude | false in both directions. A's "only the new front-end stage" is *all* of A; B needs a slice selector that does not exist, and there is no source-slice input among the 12 CLI flags |
| D14 | "Nothing in Layer A/B changes at all" | Claude | false twice: the `.vtt` writer has **no gate** (non-fatal by design), so 12 parts multiply an undetected failure surface by 12; and `source_assignment` is already not a partition of `source_sections` (4 unassigned and unrecorded), which no gate catches |
| D15 | Keep both renderers plus an agreement test | Claude | detects today's drift, not tomorrow's — and there are already four instances of a fix landing in one renderer and missing the other |
| D16 | Per-request `--mode trailer\|chaptered` | Claude | probably unnecessary. For this corpus the **segment is already the unit**, so a mode flag would select between two behaviours nobody needs. Held as a product question, not a rejection |

---

## 5. Undecided

| # | item | blocked on |
|---|---|---|
| E1 | hero image · before/after · timeline · chart · a true labeled-diagram | a real narrative document, and a thumbnail that exists. Zero presence in `schema.py` / `slides.py` / `pptx.py` — but each needs work in **both** renderers, which is the engine's most repeated failure |
| E2 | the `narrative` profile's enrichment set | a document. The `english` profile's leads were measured wrong for the domain, so *something* must change, and what is not knowable without real content |
| E3 | the hybrid "overview + chapters" as a third mode | the channel-shape decision, which is a product call |
| E4 | group segments to ~8–12 min, or one video per segment (65 vs ~500) | the same product call |
| E5 | whether the thumbnail is a new renderer or a variant of the cover card | a design decision nobody has made |
| E6 | **May `NARRATION_WORDS_MIN_FAIL = 20` move for a young audience?** | a contract change nobody has authorised, and §8.1 shows no audience band under ~17 s/scene is buildable without it |
| E7 | 16:9 → 9:16 Shorts | a layout pass in **both** renderers, on a fixed landscape canvas |
| E8 | `PyMuPDF` / `python-docx` / `matplotlib` / `tesseract` installs | not blocked, just not done — `python-docx` alone unblocks 0 → 18 corpus files |

---

## 6. Cinematic video — not a local problem, and not the right layer

**The machine, measured** (not the quoted "8 GB, no CUDA"):

| | measured |
|---|---|
| GPU | none. `nvidia-smi` absent, no VGA/3D device on PCI |
| RAM | **4.8 GiB total, 1.9 GiB available** — not 8 GB |
| CPU | 4 cores, **Intel i5-7200U @ 2.50 GHz** (2017 laptop) |
| disk | 860 GB free |
| ffmpeg | 8 of the filters a compositing pipeline needs: `zoompan`, `overlay`, `xfade`, `scale`, `format` |

**Self-hosting a video model is not "slow" here — it is impossible.** A heavily
quantized 1.5B video-diffusion model needs more working memory than the entire
free RAM on this box, which is simultaneously running the LLM, TTS, Pillow,
python-pptx and ffmpeg. This is a stronger constraint than the one quoted, and it
removes the option rather than pricing it.

**But cinematic video was never generated on anyone's own machine.** Veo, Kling,
Runway and Sora all run on cloud GPU farms. The question is not "how do I get
cinematic locally" but **"how do I rent cinematic frames and keep the
deterministic pipeline as the authority."**

### The design rule that makes this safe

> **Any frame carrying a fact must be deterministic. Any frame carrying mood may
> be generative.**

A generative model cannot render a correct date, a correct diagram, or a correct
number — and §1 of `DESIGN.md` is precisely that nothing verifies truth. So
generative footage is **decoration by construction**, and decoration must be
visually separable from information. This is not a compromise; it is the only
architecture in which the narration gate and the visuals can both be true.

### Four tiers

| tier | what | cost for the 65-video corpus (16,904 s of finished video) |
|---|---|---|
| **T0** | deterministic slides + real TTS — what exists now | **$0** |
| **T1** | still-image backgrounds, licensed stock or AI-generated stills, animated with `zoompan` | **~$0** |
| **T2** | image-to-video for hooks and section transitions only | **$211** at 10% coverage / **$1,014** at 20%, at $0.12/s with 2.5× for rejected generations |
| **T3** | fully generative video | **$5,071** at $0.12/s — and it would *replace the information layer with decoration* |

**T1 is what most good educational channels actually use**, and it is nearly
free. T2 uses **image-to-video, not text-to-video**: I2V is billed at the same
rate but is far more controllable, because the first frame is one you already
approved. Text-to-video throws that away.

**Rates verified against provider pages, September 2026** — Runway Gen-4 Turbo
$0.05/s and Gen-4.5 $0.12/s at 720p; Google Veo 3.1 Lite $0.05/s, Fast $0.10/s,
Standard $0.40/s (audio bundled); Kling 3.0 $0.084–0.168/s by resolution and
audio. Audio on models that do not bundle it adds ~$0.03/s. **These rates change
monthly; re-verify before budgeting.** Batch mode is ~50% off where offered.

**One time-sensitive fact:** the **Sora 2 API shuts down 24 September 2026** —
three days from now — with no named replacement. Do not prototype on it.

**Ruling: adopt T0 and T1 now, T2 when the thumbnail exists, reject T3 for a
teaching channel.** The local box keeps its job as the editor and compositor; only
the *footage* is rented. The pipeline stays deterministic end to end.

---

## 7. Animation — the cheapest quality win, and we already own the hard part

**Animation is not an AI problem on this project. It is a rendering-loop problem,
and the loop already exists.** That is the whole answer, and it is worth stating
plainly because §6 sent us looking at cloud video models when the highest-value
motion is free and already half-built.

### The asset being wasted

`*.word_timings.json` is written at `video.py:800-812` with **per-word `start`
and `duration`**. Measured on `output/mod03_budget_v01.word_timings.json`: clip 0
carries **47 words over 23.91 s = 1.97 words/s**, 379 words across 9 clips, and
`ticks_per_second` is recorded for lossless reconstruction.

Its **only** consumer today is `spoken_words = sum(...)` at `video.py:810` — a
count for a log line. The `.vtt` does not use it either: cue times advance by
each clip's *measured duration*, because every clip carries trailing silence
after its last word.

So we hold ~2 words/second of timing resolution on disk and spend it on a
counter. **Word-synced kinetic text is the single most valuable animation
available to this project, and it costs $0** — no new block type, no image asset,
no cloud call, no new model.

### The frame loop already exists

`_slide_variants` (`slides.py:703`) renders `count + 1` PNGs per scene into a
work dir, and `assemble_video` holds each for its audio span. Any *timed*
animation is the same loop with a finer clock. The invariant to respect is the
one the engine already learned the hard way: the row stack must **reserve
identical space across every variant**, or the video reflows as the reveal
advances (engine ledger §A31 — measured lowest text y 7.01 in at reveal steps
0–3). The same rule governs a 24 fps animation.

### Six classes, priced and judged

| class | cost | verdict |
|---|---|---|
| **1. Word-synced kinetic text** | **$0** | **ADOPT — first.** The data exists. Also serves accessibility, and it is the only motion that can be *exactly* correct because it is driven by the audio |
| **2. Progressive draw-on** for `flow` / `visual_diagram` | $0, small | **ADOPT** once class 1 lands. Arrow draw, node pop-in — the same reserved-space rule |
| **3. Ken Burns / camera move** | $0 (ffmpeg has `zoompan`) | **RE-DECIDE, do not just add.** It was **removed on purpose** (the L-bar edge artifact) and there is now **zero** use of `zoompan`/`rotate`/`overlay`/`drawtext` anywhere in `studio/*.py`. Reinstating it means respecting why it went |
| **4. Hand-drawn "whiteboard" explainer** | $0, deterministic | **WORTH A LOOK, not scheduled.** A seeded variable-width stroke renderer is fully code-generatable, needs no assets and carries no licence risk. It is a *renderer for the block types* already blocked in `SLIDE-DESIGN.md` §5 E1, not a separate track |
| **5. 3D / Blender** | — | **REJECT on this machine.** EEVEE needs a GPU and there is none. A 10 s 24 fps shot is 240 frames; on 4 cores of a 2017 i5 with 1.9 GiB free that is minutes per frame, and we need 4.7 hours of finished footage |
| **6. Generative / video-to-video motion** | §6 T2/T3 | Already priced. Not "animation" in the craft sense — it re-renders an AI image. I2V, because the first frame is then one you approved |

### The honest limit

Animation raises **retention after the click**. It does not raise the
**click-through rate**, and on YouTube the click is decided in about two seconds
by the thumbnail. So classes 1–3 are high value per dollar but strictly
*downstream* of the thumbnail problem in `SLIDE-DESIGN.md` §5 E1. Nothing here
displaces the three on-screen leaks or the §1 narration gate.

**Ruling: adopt classes 1 and 2, re-decide class 3 deliberately, reject class 5.**
Class 1 is the single best value-per-line item found in this entire engagement,
and it is smaller than the 12-line paragraph fallback.

---

## 8. Input 3 — "topic-aware studio": one genuinely new idea, and it breaks the pause

Third pass on the same ground. Most of it corroborates or repeats; **one idea is
new and load-bearing, and its own numbers are incompatible with the engine.**

### 8.1 The new idea: audience age band as a first-class axis

"One source → many video styles for different viewers", parameterised across six
age bands with `speech_speed`, `max_words_per_scene`, `caption_size`,
`scene_change_seconds`, `text_density`, `color_theme`.

**This is the best product idea any of the three inputs has produced**, and it is
cheap for us: `NarrationVoice` (`voice.py:146`) is *already* a parameterised
narration profile with a registry and a CLI flag. An `audience_profile` is a
second axis on an existing seam, not a new subsystem. It is also the honest
answer to D16 — I rejected `--mode trailer|chaptered` as unnecessary because the
corpus's segment is already the unit. Audience age is a *different* axis and
survives that objection.

**But the scene rhythms it specifies are unbuildable.** Using the engine's own
`structural_silence_seconds` and `word_budget` at 240 s:

| band | scene rhythm | clips | silence | per clip | feasible |
|---|---|---:|---:|---:|---|
| 3–6 | 4 s | 60 | 190.0 s (**79%**) | 1.3 | **0** |
| 3–6 | 8 s | 30 | 100.0 s (42%) | 7.6 | **0** |
| 7–12 | 8 s | 30 | 100.0 s (42%) | 7.6 | **0** |
| 7–12 | 15 s | 16 | 58.0 s (24%) | 18.1 | **0** |
| 13–18 | 6 s | 40 | 130.0 s (54%) | 4.5 | **0** |
| 13–18 | 12 s | 20 | 70.0 s (29%) | 13.7 | **0** |
| 18–45 | 10 s | 24 | 82.0 s (34%) | 10.6 | **0** |
| 18–45 | 20 s | 12 | 46.0 s (19%) | 25.2 | 1 |
| 45–70 | 15 s | 16 | 58.0 s (24%) | 18.1 | **0** |
| 45–70 | 25 s | 10 | 40.0 s (17%) | 30.7 | 1 |
| 70+ | 20 s | 12 | 46.0 s (19%) | 25.2 | 1 |
| 70+ | 30 s | 8 | 34.0 s (14%) | 38.7 | 1 |

**4 of 12 feasible — and they are the three oldest bands.** The three youngest,
which the proposal is most excited about ("big characters, simple words, songs"),
are structurally impossible in 4 minutes.

The cause is one number. `NARRATION_WORDS_MIN_FAIL = 20` at the measured
107.276 wpm means **a scene cannot be shorter than 11.19 s of speech**; with the
3.0 s inter-scene pause, 240 s admits at most **14 scenes** — one per 17.1 s.
The floor is a contract (`config.py:335`), so this is not tunable by prompt.

And the 7–12 profile compounds it by specifying `max_words_per_scene: 16`,
**below the enforced floor of 20**. As written, that build is refused.

**This is the same arithmetic that killed D1**, now aimed at a whole audience
segment. The escape is already on the table and already ruled a *product*
decision, not a defect: `--pause` 3.0 → 1.5 recovers 13.5 s. But even at zero
pause the floor alone caps a scene at 11.19 s, so **the pause cannot fix this
alone** — the 20-word floor must move, and that is a contract change nobody has
authorised.

**Ruling: adopt the audience axis as a profile extension; reject the six bands'
scene rhythms as specified; treat "may the 20-word floor move for a young
audience" as a new open question for the user.**

### 8.2 The toolchain, measured rather than recommended

| suggested | status here |
|---|---|
| `python-pptx`, Pillow, pydantic, edge-tts, ffmpeg/ffprobe, soffice, pdftoppm | **present** |
| **`ollama`** | **present** — a local 1B–3B model for iteration is available, which the input did not know |
| `python-docx` | **ABSENT** — and `.docx` is **0 of 18** corpus files loadable today |
| `PyMuPDF` | **ABSENT** — "PDF with selectable text" in their Phase 1 is not currently possible |
| `matplotlib` | **ABSENT** — and charts are already a blocked block type (`SLIDE-DESIGN.md` E1) |
| `tesseract` | **ABSENT** — so "OCR when needed" has no implementation |
| Whisper / faster-whisper | **ABSENT** — and **not needed**: every source we have is already text |
| Piper, Manim, networkx, cairosvg, svgwrite, pydub | **ABSENT** — none is on a critical path |

So the install list implied by work we have *already* scoped is short and
ordered: **`python-docx`** (unblocks the corpus), **`PyMuPDF`** (unblocks a
claimed input format), **`matplotlib`** (unblocks charts), **`tesseract`**
(optional). Everything else is a nice-to-have.

### 8.3 Adopt: copyright and licensing rules

Correct, necessary for a monetised channel, and **stated nowhere in our docs**.
Our own output already carries a licence problem we had not named: every frame
is branded `doc-to-video-tutor v0.1.0` (engine `config.py:352-356`), and the
narration voice is `hi-IN-SwaraNeural` / `en-IN-NeerjaNeural`. Adopt verbatim in
substance: own narration, own or licensed visuals, open-licensed music, original
AI music only after checking the model licence, and no copyrighted songs, clips,
characters or scraped images.

### 8.4 Third corroboration of the shape mapping

The input's information-structure table (object parts → labeled diagram, sequence
→ timeline, numbers → chart, comparison → side-by-side, cause/effect → flow,
abstract → analogy, emotion → character, question → quiz) is the **third**
independent pass at the same idea — `code-reviewer` from the source, Perplexity 2
from design practice, now this. The counts differ by granularity (5 shapes, then
9, now 8) but the mapping is stable, which is why `DESIGN.md` §4.4 treats the
shape count as settled.

### 8.5 What is wrong or self-contradictory here

| item | problem |
|---|---|
| `"importance": 10` per key point in the knowledge map | **D4 resurfacing.** A self-rating the model assigns to its own output, with no second computation to check it against |
| the decision tree (`does it contain questions → Quiz template`) | keyword-based routing, which **the same document disavows** four sections earlier: *"A good system does not decide visuals from keywords alone."* Both cannot be true |
| "hook in the first 5–10 seconds" | our `TITLE_HOLD` is 4.0 s so a hook *could* land in-window — but the measured first 11 s is the **emptiest frame in the build** (7.1% body fill) carrying the literal word `opening` in its caption. The hook window is structurally the worst 11 seconds of the video. **This is a new argument for A3.** |
| "a new visual beat every 8–20 s" | already exceeded at 4–7 s — see C4 |
| "a question every 30–60 s" | needs a **quiz scene type we do not have**; another dependency on the blocked block list |
| `"canvas": "1920x1080"` | we render 1280×720. 1080p is 2.25× the pixels for Pillow on 4 cores, and our render leg is already 91% of a 911 s build. **Unmeasured — flagged, not ruled** |
| "8 GB RAM, CPU-only Intel HD graphics" | **wrong for the third time.** Measured: 4.8 GiB total, 1.9 GiB available, i5-7200U @ 2.50 GHz, 4 cores |

---

## 9. Channel network: all ages, all types — the measured verdict

The user asked for music/song, teaching, story, quiz and documentary, on any
topic, for **all ages 3 to 100**, using only free and open tools, and for content
viewers love. Five specialists answered within their evidence. **The answer is
that this is a portfolio of 5–6 channels, not one pipeline — and 4 of the 5
content types are blocked by the engine, not by taste.**

### 9.1 Per content type, against the real gates

| type | verdict | the measurement |
|---|---|---|
| **documentary summary** | **SHIPS UNCHANGED** | `_render_blocking: PASS (none)`, `audit FAIL=0 WARN=0`, `guard_plan` clean |
| **teaching** | ships, capped at 4/5 | the natively supported shape — but a third of the material never reaches the planner (`concepts_read 8 / concepts_total 12`) regardless of style |
| **nursery rhyme / lullaby** | **CONTRACT CHANGE** | ships only via an undocumented loophole, and the repair **ate 27 sentences, −14.6%**. The exemption requires duplicating the refrain into `takeaways`, which then trips `near-duplicate bullets vs takeaways` |
| **quiz** | **CONTRACT CHANGE ×2** | `FAIL=7`: `tts_too_short_critical` on 4/6 clips at **11–19 words** (min 20), plus `tts_required_concept_missing` and `unrepairable narration repeat`. Repair deleted **0** sentences → a resample loop. And `assemble_video(..., pause: float = 3.0)` (`video.py:431`) is **one scalar for every clip** — think-time is not representable |
| **song / lyric** | **FORBIDDEN OUTRIGHT** | 29 banned phrases, **78 of 87 chorus sentences deleted**. The deleting pass is `_drop_within_scene_exact_repeats`, called at `narration.py:279`, and its signature has **no `protected` parameter at all** — so protection cannot reach the first pass. Two further independent blockers: `synth_scenes` synthesises every clip unconditionally and `assemble_video` zips `strict=True`, so **there is no external-audio path**; and reveal placement needs a monotonic *spoken-token* match, which a sung lyric cannot supply (returns −1 → even split) |

**1 of 5 ships unchanged. 1 is forbidden. 3 need a contract change.**

The binding block on song is **not** beat detection. That was measured: a
spectral-flux onset detector reached **0.2% inter-onset error** on a synthetic
120 BPM signal using ffmpeg plus the numpy already installed — ~40 lines, zero
new dependencies. The blockers are the audio ingest path and the untimed text
channel.

### 9.2 The finding that should stop a plan in its tracks

**The default narration profile forbids Hindi and Marathi outright.**
`mhe-mix`'s pure-English check counts **21 romanised Latin** Hinglish markers
(`hai`, `kya`, `aap`). A Hindi or Marathi video written in **Devanagari scores
0** and is reported `narration looks pure English (0 marker hit(s), < 3
required)`.

Measured across all four combinations — 3-year-old English, 70+ English,
Devanagari Hindi, Devanagari Marathi — **all four FAIL the default profile.**

So **2 of the 5 intended languages are blocked before any content gate runs**,
and the project has been advertising them.

The `english` profile is no answer. `must_not_be_pure_english = False` returns
`(True, "pure English legal")` **before reading a single token** — it passes on
correct English *and on gibberish*. And `dd_leads` (`"Reason:"`,
`"Design choice:"`) **never enter spoken text**; they are a card-rendering
vocabulary.

**There is no age or register field anywhere in the voice contract.**

### 9.3 "All ages 3 to 100" against the template, from pixels

Body text is 14 px. Measured against a `cap ≥ D/150` legibility threshold:

| band | device | required cap | have | ratio |
|---|---|---:|---:|---:|
| 3–6 | tablet 12″ | 10.4 px | 10 px | **97%** |
| 18–45 | laptop 24″ | 15.1 px | 10 px | 66% |
| 70+ | TV 55″ @10 ft | 26.7 px | 10 px | **37%** |

**One font size is tuned to the youngest band and abandons the oldest.** The
single `S` scalar cannot fix it — `S` scales both axes and the canvas is fixed —
and the wrap widths in `slides.py` are **absolute character counts calibrated to
1280 px** (`_wrap(s,60)`, `(b,70)`, `(node,22)`, plus five `[:NN]` truncations).
Change the font size without re-deriving those and every block silently
overflows. Counted: **14 `_font(Npx)` sites in `slides.py`**, **20 `Pt(...)`
literals in `pptx.py`**.

**Split ruling.** An age band **can** be added with **zero renderer lines** for
speech rate (`voice.py:168` already exists), words per scene
(`config.py:335-338`), scene count (`config.py:310-312`) and pause
(`duration.py:29`). It **cannot** for visual density. Bundling those two together
is exactly what would make the age axis look expensive.

### 9.4 A new confirmed defect, and three self-corrections

**The `TAKEAWAY` label is drawn and both items are silently dropped.** Scene 1
has `takeaways=2`; the label renders at rows 635–644 so `yy=639`, the item needs
`yy+18=657`, and `BODY_MAX=652` — **rejected by 5 px.** Zero takeaways are
visible in any of the 5 reveal variants. In a shipped build, and not cosmetic: the
closing summary of the lesson does not appear on screen.

The same pass **corrected three of its own earlier figures**: 3.8% ink → 4.95%
whole-frame / **1.98% of the body region**; 11% near-black → 1 frame in 105; 69.2%
extent → **54.3%** chrome-free.

**Two specialists disagreed on 9:16**, and both are right that the scalar fails.
One measured usable width −46.7% against body budget **+112%** — opposite
directions — and called it a rewrite; the other counted ~36 parameterised sites
and called it a dataclass. **Ruling: a `Canvas` dataclass *plus* a second
layout.** And the deck half is unnecessary, because `assemble_video` is the only
consumer of `render_scenes`: **ship vertical MP4 only, keep the deck landscape.**

### 9.5 The economics: a render-cost problem, not an LLM-cost problem

**Proxy, not a reading.** Split per video: render **829.6 s (91%)**, planner 50.4 s (5.5%),
TTS 21.9 s (2.4%) — derived from file mtimes across a build, and **not
recoverable from any artifact**: there is no `logging` in `src/` and no stage or
elapsed field in `*.verify.json` (measured: no `elapsed`/`timing`/`wall`/`stage`
key exists). By this repo's own rule that split is **a rumour until it is
measured inside the tool**, which is now NFR-009. At 65 base videos:

| bands × types | videos | wall hours | LLM calls | TTS calls |
|---|---:|---:|---:|---:|
| 2 × 2 | 260 | 65.8 | 520 | 2,340 |
| 3 × 3 | 585 | 148.1 | 1,170 | 5,265 |
| 5 × 5 | 1,625 | 411.5 | 3,250 | 14,625 |

**The render is 91% of every cell.** Batching the planner across variants buys
**≤5.5%** of wall clock, and TTS (2.4%) cannot be batched at all because every
variant needs its own audio. Any fan-out plan justified by *"one source, many
outputs, so the LLM cost amortises"* is **arithmetically wrong here** — nothing
amortises, because the expensive leg is re-run per output.

### 9.6 The missing field for a fan-out

The finest traceable unit today is `chunk_digest`, which answers *which excerpt*,
never *which assertion*. A reviewer can prove two videos both drew on
`4fa14f8859246b60`; they cannot prove they asserted the same fact, or the same
number.

**The field is `claim_id`**, plus `derived_from_plan_sha256` and
`variant_axes: {content_type, audience_band}`. The precedent is already in-tree:
`check_audit_binding` (`validate.py:235`) does exactly this shape for plan↔audit.

Second in line: `tts_script.json`, `word_timings.json` and the `.vtt` trace to
their plan **by filename and title string only** — and the title is the field the
truncation defect corrupts.

### 9.7 Licensing — nothing exists, and this blocks a monetised channel

Checked exhaustively: **no `LICENSE`, no `COPYING`, no `NOTICE`**, and
`pyproject.toml` declares no `license`. Zero mentions of licence, copyright or
commercial use in `README.md`, `AGENTS.md`, `CALL-FLOW.md`, the LLD, the BRIEF,
the ledger or the retrospective. The **only** positive grant in the tree is
`LLD:1013`, about DejaVu.

Four things must be settled in writing before the first video ships:

1. **The TTS voices.** `pyproject.toml:13-16` itself concedes edge-tts is "an
   unofficial wrapper around a **consumer endpoint**". Consumer terms are not a
   commercial-publication grant. No file in this repo answers it; Microsoft's
   terms have to be read directly.
2. **Fonts — the two cases differ.** The `.pptx` carries no font exposure: names
   only, no font parts, no `embeddedFontLst` (verified on a real artifact).
   **The MP4 is the opposite** — `slides.py:208-217` rasterises real DejaVu
   outlines into every frame, so the shipped video *does* redistribute glyph data
   and the Bitstream-Vera-derived terms genuinely apply. And `slides.py:221`'s
   "or None → PIL default bitmap" fallback is silent, producing glyphs from an
   unstated face.
3. **`BRAND_NAME = PACKAGE_NAME`** puts the literal string
   `doc-to-video-tutor v0.1.0` into **every published frame** (`slides.py:535,565`,
   `pptx.py:428`). A third party's name in every frame is a nominative-use
   question, not self-branding — and it is also a credibility question for a
   channel.
4. **Narration text** is third-party LLM output: whose copyright, and does the
   provider permit commercial publication of it?

### 9.7a CORRECTION (2026-09-27) — the corpus is **text**, and the rights blocker is smaller than I stated

I wrote "**18 third-party recordings**" and "eighteen third-party recordings is a
distribution surface". **Wrong.** Measured: `data/transcripts/` holds **18 `.docx`
text transcripts and 0 audio or video files.** There is no audio in the corpus
today, so there is no voice or likeness question *yet*.

That splits the rights question in two, and the split matters:

| surface | exists today | what it needs |
|---|---|---|
| **transcript text** — a teacher's spoken class, transcribed | **yes** | a one-line **attestation**: "I taught this, or I hold the right to use it." Not a licence-clearance project |
| **voice + likeness** — his own narration, and screen recordings of his own screen | no, until he records | his own material, so simpler — but consent for anyone else visible or audible on that screen |
| **the 18 recordings I wrongly asserted** | **they do not exist** | — |

And it contradicts a second thing I wrote: §9.8 said the corpus "needs no licence
research, no attribution and no clearance" while §11.6 demanded consent for the
same 18 files. **Both cannot hold, and both were mine.** The reconciled position:
the corpus needs **no external licence research and no attribution**, because it
is the user's own material — but it does need an **attestation**, and until that
sentence is written the corpus is not cleared for a public channel.

### 9.8 Free sources — a checklist to verify, not assets to trust

I have no licence-cleared list and will not manufacture one. What can be said
without a per-source check is structural:

- **The corpus you already own is the largest free asset here.** 18 transcripts
  of your own teaching, 522 pre-titled timestamped segments, 426,596 words. It
  needs no licence research, no attribution and no clearance — and it is the only
  *domain-authentic* material on this machine. Every external source is a worse
  version of it.
- **Everything else is a checklist**, and each item needs its licence read at the
  source: public-domain and openly-licensed archives; free-licence stock footage
  and stills whose terms permit monetisation *and* redistribution; open-licence
  music and sound; and self-generated music, where the **model's** licence is the
  thing to check, not the tool's.
- **Fonts are a separate list from images**, and the easiest to get wrong —
  because "the name is set" and "the glyphs are licensed" are different claims
  (§9.7 item 2).
- **The trap:** in this repo `provenance` means *fact-grounding*
  (`narration.py:500`, `plan.py:452`, `util.py:183`) and **never** rights. Anyone
  auditing for licence provenance will be misled by the word. If licence
  provenance is ever tracked it needs a different name.

### 9.9 What nobody here can tell you

**No document and no local measurement can say what viewers watch.** Retention,
completion, whether a 3-year-old or a 97-year-old returns, whether music or
teaching or documentary earns most — that needs published channel analytics,
which cannot exist before publication. It is a **bet, not a measurement**, and
the honest response is a small published pilot rather than a larger unbuilt one.

Also undecidable locally: Microsoft's terms for commercial republication of
`edge-tts` audio; whether any LLM provider permits commercial publication of its
output; YouTube Content ID behaviour against generated music.

---

## 10. Input 4 — a Business Analyst framing: lanes, backlog, KPIs

The fourth external input, and the first written from a product rather than an
engineering perspective. Most of it is process discipline the repo already
follows; **three things are new, one KPI is contradicted by our own artifacts,
and one recommendation converges with a measured engine gap from the opposite
direction.**

### 10.1 Adopt: the rule that is already the architecture

> *"The LLM may recommend content and scene structure, but deterministic
> validators decide whether the content is renderable and publishable."*

This is the engine's existing ruling, arrived at from the opposite direction —
`_render_blocking_problems` is "Deterministic only (no LLM)" by contract, and
`_ensure_technical_visuals` exists so enrichment "can never invent a fact the
way a model-written 'worked example' would". **Adopt as stated; nothing to
build.** It is also the correct answer to §1's blocker: the narration gate is the
missing half of a rule we already wrote down.

> *"Generate and approve a structured storyboard before generating the video."*

Also already the architecture — `plan_lesson` → `guard_plan` review loop → media,
with up to 5 samples. **But the engine has machine approval and no human
approval**, and that distinction is the whole of §10.3.

### 10.2 New and adopt

| item | what it is | why it matters |
|---|---|---|
| **Prompt injection as a threat class** | `util.load_documents` reads untrusted text and it reaches the planner prompt verbatim. A document saying "ignore all previous instructions" is a live input, not a hypothetical | **absent from every document in this repo**, and it is the one risk on this list with no existing control. Cheapest fix is to delimit source text and treat it as data, never as instructions |
| **Per-scene artifact independence** | `scene_01/scene_plan.json`, `narration.mp3`, `slide.png`, `source_evidence.json`, `scene_preview.mp4` — regenerate scene 4 without re-rendering ten minutes | **does not exist.** `verify --out` repairs the **whole plan**; `render` re-renders the whole video. Confirmed by absence of any per-scene subcommand |
| **Provenance as a standard, not a feature** | NIST AI 600-1 content-provenance framing, and W3C captions as synchronised text carrying non-speech information | makes `claim_id` (§9.6) a compliance-shaped requirement rather than a nice-to-have, and makes the `.vtt` an accessibility obligation |

### 10.3 The convergence worth noting

The input's own diagnosis: *"One thing most teams get wrong — they over-invest in
the generate step and under-invest in the edit/regenerate loop."*

That is exactly the gap §9.2 and §9.6 measured from the other direction: the
repair chain operates on the **whole plan** (`_repair_unsafe_narrations`,
`_repair_thin_narrations`, `verify --out`), there is no per-scene address, and
`tts_script.json` / `word_timings.json` / `.vtt` trace to their plan by
**filename and title string only**.

A BA reading the workflow and a code reviewer reading the repair chain converged
on the same missing feature without sharing a word. **Ruling: per-scene
regeneration is the highest-value unbuilt item in the entire engagement** — it
serves the edit loop, it is the prerequisite for the channel fan-out, and it is
the only proposal that makes iteration cheap rather than merely possible.

### 10.4 Contradicted by our own artifacts

| claim | measured |
|---|---|
| "Target narration **500–580 words**; target 225–240 s; hard max 240 s" | **Already rejected (D2), and this input repeats it.** Measured 107.276 wpm + 37.36 s silence → a 240 s MP4 holds **362 words**. 500–580 words is 289–373 s. |
| "Valid storyboard JSON on first attempt **≥ 95%**" | Of 26 builds that persisted samples, **18 took one sample** — first-attempt acceptance **69%**. *Caveat: the reason for a resample is not persisted, so this bounds first-attempt acceptance generally; it cannot distinguish invalid JSON from valid JSON that failed a gate.* Either way the stated KPI is not currently met |
| audience matrix: 3–6 = **0–8 words per scene**; 70+ = **8–20 words per scene** | Both ends are **below `NARRATION_WORDS_MIN_FAIL = 20`**, which is hard-blocking. Same collision as §8.1, now from a second direction |
| "Do not initially promise 'all ages' with one shared output style" | Agreed and already measured: one 14 px body size is 97% of threshold for a 3-year-old's tablet and **37%** for a 70-year-old's TV |
| FR-21 "Whisper-based transcription" | Unnecessary for this corpus — all 18 files are **already text**, and Whisper is absent, and 4 cores / 1.9 GiB makes it slow. It also contradicts Phase 2's "three-hour transcript" premise that D5 already rejected |
| FR-13 "16:9 and 9:16" | `assemble_video` is the only consumer of `render_scenes`, so **vertical MP4 only** is cheap; the deck half is a separate, larger job and is not needed for Shorts |
| "Save job state after every stage; retry from the failed stage only" | **Unmet, and it blocks the fan-out.** `build` terminates in `raise SystemExit`, so an in-process multi-video loop dies after the first one. This is the same finding as the missing slice selector (§D13) |

### 10.5 The lane question, ruled

The input's sharpest product point is that *"generate any doc" is four products
wearing one trenchcoat* and a team should pick **one** wedge.

That is right, and it **conflicts with the user's actual ask** — a network of
five content types. The resolution:

**They are not one product, and they are not five engines.** They are five
*lanes* — separate channels, separate audiences, separate quality bars, separate
licences — sharing **one engine and one evidence model**. The shared parts are
exactly the parts that are already built and already correct: ingestion, the
adapter, `TopicProfile`, provenance, and the deterministic gate suite. The parts
that must differ are the ones §9 measured as missing: scene primitives, the word
bands, the visual density, and the narration register.

So: **one engine, five lanes, one lane shipping at a time.** Starting with
documentary + teaching, because documentary is the one type that passes every
gate unchanged today. Song is refused outright and should not appear on any
roadmap.

---

## 11. Video in, script in — the two input modes, measured

The user asked two questions. Both have answers, and one of them invalidates the
cheapest fix proposed in the same round.

- **Mode A — "I already have a teaching video. Can you add audio and put visuals
  in it?"**
- **Mode B — "Or I give you a flow/script, and you make the visuals, like real,
  with audio."**

### 11.1 Mode B is what exists. Mode A's blocker is not audio.

| | verdict |
|---|---|
| **Mode B** (script → visuals + audio) | **Already the pipeline.** Its only gap is "like real" = real footage, and §6 already rules how far that goes |
| **Mode A** (caller's video in) | **Blocked — but not by audio plumbing.** There is no ingestion path for the user's own files |

Mode A's measured blockers, in order:

1. **The pipeline cannot open the corpus.** `util.py:155` sends every non-`.pptx`
   input to `p.read_text(encoding="utf-8")`. A `.docx` raises
   `UnicodeDecodeError` — **0 of the 18 transcript files are loadable today.**
2. **A 90-minute transcript is silently truncated.** The read window is
   `max_chars=12000` with **no CLI flag**; 90 minutes is ~74,000 chars, so ~84%
   would vanish with nothing recorded.
3. **No format gate at all.** `README.md:119` documents a format list that
   *nothing enforces*, and `.ppt` is accepted at `util.py:152` but unopenable at
   `util.py:163-166`. `LLD:51` already commits to "fail loudly and early"; a
   `UnicodeDecodeError` after the LLM call is the opposite.

**The audio half is small.** `--audio-dir DIR` holding exactly
`clip_count(N)` files in scene order is **~33 lines**, zero schema change
(`SlideScene` is `extra="ignore"`). Keep `strict=True` — measured, it raises
rather than truncates, and it is the correct **count** tripwire. One trap:
`_normalize_loudness` is **destructive in place** (`shutil.move`), so caller files
must be copied into the work dir first or the user's originals are overwritten.

### 11.2 The three findings that decide whether Mode A is safe

**1. Every narration gate reads TEXT, not audio.** `audit_tts_script(clips,
voice, plan)` has no audio parameter. Measured: all 9 clips replaced with
audio re-encoded `atempo=0.5` (224.281 s → **447.983 s**, every clip ~2.0×), and
the audit returned the **identical** single `WARN tts_long_sentence`;
`review` still exited **0 / PASS**. The word band is a *text-volume* proxy that
only behaved like a duration proxy because the pipeline owned the clock — and it
is already wrong per clip by **−22.2% to +14.0%**, with the sum error only
−3.4% because the errors cancel.

Consequence, stated precisely: `tts_voice_unset`, `tts_slide_meta_leak` and the
entire 20/90-word duration band become **meaningless rather than inaccurate**,
and ~9 further codes rest on an untestable premise — *that the caller's audio
faithfully renders the plan's `spoken` text*. Nothing in the pipeline can test
that premise.

**2. Supplied audio is never normalised, and the miss is recorded without being
enforced.** `_normalize_loudness` has exactly one call site, inside
`synth_scenes`, over files it just wrote. Measured: a supplied clip at
**−22.3 LUFS** stays at −22.3; the function *would* take it to **−16.1 LUFS**
(−16.0 target, ±2) if it were ever reached. `measure_delivery` **does** read the
delivered MP4 and records `−22.3 LUFS` — a real reading, sitting beside the
*configured* `−16.0 / −1.5` — but `_write_verify_artifact` has no loudness branch,
so the verdict is unaffected. **A −22.3 LUFS MP4 ships under a PASS.** There is
already precedent in a shipped artifact: `verdict: PASS` with `band: LONG`.

**3. There is no time primitive at all.** `source_assignment[].section_index` is
an int into `_markdown_sections`, which requires ATX headings `^#{1,3}`. It
cannot carry a time. A heading-less transcript collapses to a single
`("", content[:1200])` pair, so **1 scene is assigned and the rest are
unassigned**. The minimum field is `source_in` / `source_out` in seconds — a
**parallel model**, not a reuse.

### 11.3 The compositing fix that was measured and **disproved**

The first specialist recommended a ~15-line ffmpeg `overlay` behind the frame.
The pixel reviewer tested it and it **does not work**:

- **`overlay` behind the frame is a pixel no-op.** Probing (600,600): footage
  `(64,84,126)` → frame `(16,23,37)` → output `(15,22,36)`. Lossless re-run,
  max deviation 34/255, all YUV round-trip. **0 footage pixels visible.** The
  frame is opaque (`Image.new("RGB", …, color=BG)`) and flattens to black.
- **Full-bleed with a scrim collapses every chrome element.** Title **1.05:1**,
  body **1.05:1**, eyebrow 1.02:1, footer 1.50:1, counter 1.36:1 — against a
  baseline of 11.00 / 10.69 / 8.48. WCAG AA is 4.5:1 and the 3.0:1 large-text
  allowance never applies, because 10px body and 22px title are both under 18pt.
- **The scrim that would make footage visible makes it invisible.** Minimum
  passing scrim is s=0.95 (s=0.93 fails at 4.36:1). At s=0.95 the footage's luma
  σ collapses **51.7 → 2.6** — 5% of its range. The render shows a faint window
  and a faint head; it is indistinguishable from no footage.
- **The layout audit is structurally blind to this.** Full-bleed still reports
  *no findings* while the delivered image sits at 1.05:1. No existing check can
  ever see this class.

**The answer that works: a picture box, no scrim.** Carve one rect per scene out
of the body budget (y500–660 measured free), keep the entire flat-background
area opaque, composite downstream at `assemble_video` where it is already
strictly after all PNG rendering — so the **reserved-space invariant is
untouched**. Measured: every contrast ratio identical to the shipped frame; the
box is a reserved rect in the same coordinate system as `BODY_MAX`, so "box
intersects a text bbox" is a check of the *existing* geometry class. The
side-panel variant breaks geometry — measured **15px overlap** with card 4, and
the gold rule and counter cross it.

**Bonus, and it is the best news in this section: a real frame from the user's
own lecture solves the thumbnail problem.** Measured at 210px — the current
composition gives 12 text elements with a title cap of **2.6px** and body cap
**1.2px** (grey mush); a single 63px-bold element over a real frame measures
**7.4px cap, 21.52:1**, 2.8× the cap and one element instead of twelve. That was
previously recorded as *impossible from the current composition*.

### 11.4 ASR is unnecessary, and there is a free path to captions

Every aligner is absent (measured: `whisper`, `faster_whisper`, `stable_whisper`,
`whisperx`, `vosk`, `torchaudio`, `aeneas`, `speech_recognition`, `pocketsphinx`
— only `numpy` present) and 4 cores / 1.9 GiB makes it slow. It is also
unnecessary, for two measured reasons:

- **The 522 existing timestamps are the alignment.** The transcripts already
  carry `HH:MM:SS - HH:MM:SS` per segment. A transcript-driven cutter is **~70
  lines**: a `.docx` branch (12), `--read-window` (3), a time-carrying section
  splitter (20), and an `atrim` cutter producing the N+1 files (35).
- **Captions can be had free.** ffmpeg `silencedetect=n=-40dB:d=0.35` found **9
  boundaries in a 61.57s caller clip** — ≈7.6 words/cue, against the existing
  `_VTT_CUE_WORDS = 8`. It restores captions, **not** reveal sync.
- **For full alignment, ask the caller for the word timings their own TTS
  already emitted** (edge-tts / Azure / DAW export). That is a metadata request
  and reuses the existing `WordBoundary` contract unchanged.

What is lost without alignment, measured: **captions go 55 → 0 and no `.vtt` is
written at all**, silently, because of the `if vtt_cues:` guard. **Reveal sync
degrades 8/8 scenes** to an even split — scene 2's final bullet holds 16.76 s
instead of 4.66 s, a **12.1 s / 72% error**. And word-synced kinetic text, the
best value-per-line item in the project, is unreachable.

### 11.5 Provenance: an extension, not a parallel scheme

The join chain **breaks at leg 1**. `source_sections[].digest` reproduces 12/12
byte-exactly — but only by brute-forcing 17,976 offsets, because the artifact
records `chars_read` and **not the offset it actually cut at**. The source file
itself is **not content-addressed**: `source_files[0]` is a bare path string.

The minimum, and it is an extension:

1. `source_files` → objects with `sha256`, `kind`, `duration_ms`.
2. `source_sections[]` keeps `digest` **over transcript text, not media bytes** —
   a media digest fires a false contradiction on any re-encode, whereas a
   transcript-text digest survives re-encode as long as the words match — and
   gains `start_ms` / `end_ms`.
3. `source_assignment[]` gains `source_file_index` + `start_ms` / `end_ms`.
4. Replace the coverage **count** with a coverage **list** of every segment with
   an unclaimed *reason*. Measured: 37.0% of characters never read, 4 of 12
   numbered concepts lost, and `concepts_total: 12` is itself measured on
   already-truncated content — the full file parses to **18 sections**, so the
   denominator hides a further 6.
5. **`claim_id` on assertions** — the same field as §9.6, granularity-
   independent. Only the *address* changes: `(take_id, start_ms, end_ms,
   claim_id)`.

**`source_refs` must be deleted or renamed.** It is model-authored, **wrong in
2 of 8 scenes** — citing `doc/task/03_regression_gates.md`, a real file that was
never read — and it **contradicts its own `source_assignment`** on those same 2
scenes. It is also the only human-readable provenance a reader would trust, which
is exactly why it is dangerous. In the caller-supplied flow the trust inverts:
today the model asserts provenance and the pipeline records it; with a caller's
flow the caller asserts and the pipeline must **verify**.

### 11.6 The rights position — restated after the §9.7a correction

**Superseded in its premise.** This section was written when I believed 18
recordings existed. There are **18 text transcripts and 0 recordings**, so the
likeness/voice surface does not exist yet and the requirement is an
**attestation**, not a clearance exercise. The rest of this section stands:
there is still no `LICENSE`, no `NOTICE`, no `license` field, and still zero
consent/licence text in the engine's doc tree (`LLD:1013` about DejaVu is the
only grant in the whole repository).

What is needed, in order:

1. **An attestation for the transcripts** — a sentence stating the user's right to
   publish them. Cheapest and first; it unblocks the whole lecture lane.
2. **A voice-consent record** when he records narration (`DECISIONS.md` §14.4).
3. **The TTS voice terms**, if `tts_standard_voice` is ever used.
4. **A decision on `BRAND_NAME = PACKAGE_NAME`**, which puts a third party's name
   in every published frame.

### 11.6 (superseded) The rights position, which is not a build option

Eighteen third-party recordings is a **distribution surface**. Measured: `grep`
for `consent|copyright|redistribut|terms of use|privacy|gdpr` across the whole
doc tree returns **0 hits** — every "redistribution" match is about moving *words
between scenes*. No `LICENSE`, no `NOTICE`, no `license` field, and the only
grant in the tree is `LLD:1013` about DejaVu fonts.

Unstated and required: consent where students or third parties are audible or
identifiable; the licence of the source material the sessions discuss;
redistribution rights over the recordings. The LLD has no section for it — it
needs a new one, plus a row in §18.

### 11.7 What the contract asserts that would become false

Five statements assume a plan → script → clip → timing chain. With caller audio
all five become premises rather than measurements: `LLD:433` *"`build_tts_script`
is the only producer of spoken text"* (false), `LLD:664`, `LLD:665`, `LLD:660`,
and `LLD:608`'s "pre-audio gate" label. The input contract itself —
`LLD:66` "document files (.md/.txt/.pptx)" — is a **closed set**, so accepting
video is a **new contract, amended deliberately**, not an extension.

And the duration contract needs a **precedence rule**: two call sites already
exist (pre-audio `predicted` at `cli.py:313`, post-audio measured at
`cli.py:241`), so a caller-audio build can satisfy one and fail the other with
nothing saying which wins. Measured: the post-audio band is correct — 261.281 s
predicted vs 261.643 s shipped (0.14%) — and it correctly flagged a 2× caller
set as **202.1% LONG**. The pre-audio band still printed **112.7% OK** beside
that same 202% deliverable.

---

## 12. Input 5 — practical tutorial / screen-recording channels

Two inputs this round, both from a video-production and training perspective, and
both landing on the same answer: **use real screen recording, not generated
visuals.** That is the first proposal in five rounds that is *measured
compatible* with the engine's duration contract, and it converges with three
separate findings we already have.

### 12.1 The structure fits. Verified.

The proposal is 8–10 scenes over 4–6 minutes. Run through the engine's own
`word_budget`:

| scenes | target | clips | silence | per clip | feasible |
|---:|---:|---:|---:|---:|---|
| 8 | 300 s | 9 | 37.0 s (12.3%) | 50.2 | **1** |
| 9 | 300 s | 10 | 40.0 s (13.3%) | 44.6 | **1** |
| 10 | 300 s | 11 | 43.0 s (14.3%) | 40.1 | **1** |
| 9 | 360 s | 10 | 40.0 s (11.1%) | 54.9 | **1** |
| 10 | 360 s | 11 | 43.0 s (11.9%) | 49.5 | **1** |

All comfortably inside the enforced 20–90 word band. For contrast, Perplexity's
earlier *14 scenes at 240 s* returns **`feasible: 0`**. So this is the first
proposal that does not fight the contract — and it does so **without a word
budget being invented**, because it never states one.

**That is the lesson worth carrying: a proposal that specifies structure instead
of word counts does not collide with the measurement. Every proposal that stated
a word count did.**

### 12.2 Three convergences

| this input says | we had already measured, from a different direction |
|---|---|
| "Use screen recording as the main visual" | §11.3: the **picture box** — one reserved rect per scene, opaque panels elsewhere, composited at `assemble_video`. Full-bleed is a measured pixel no-op; with a scrim every chrome element collapses to 1.05:1 |
| "Record in small clips — one per step, not one long session — to support scene-level regeneration" | **A13**, the highest-value unbuilt item, which the BA input reached independently and which a code reviewer measured as absent |
| "Keep narration separate from on-screen command text: screen shows `uv --version`, TTS gets a speech-friendly version" | the engine already has exactly this split, and `_flatten_parentheses` / `speech_expand` exist to serve it |

Three products, three authors, three directions, one answer. That is as much
corroboration as this project has produced.

### 12.3 The most important rule in either document

> *"Never invent a command. Mark commands as verified, unverified, or
> placeholders."* And: *"retrieve or accept the official current installation
> command rather than hardcoding it into the model prompt… treat commands as
> verified source data, not LLM creativity."*

This outranks everything else in both inputs, because **a command in a tutorial
is a factual claim the viewer will type.** §1 of `DESIGN.md` established that no
gate reads the narration for truth — a fabricated date passes `grounding: clean`.
A fabricated *command* is the same defect with a user-visible consequence: it
fails on the viewer's machine, in public, on the recorded video.

**Adopt verbatim, and make it structural rather than advisory:** a `command`
field that is *source data with a `claim_id`*, verified against the official
documentation, never model output. That is §9.6's missing field applied to the
one content type where the stakes are highest.

### 12.4 The 10 scene types, and why it is cheaper than it looks

Word-boundary counts: **9 of the 10 have zero presence** in `schema.py`,
`slides.py` and `pptx.py`. But the right framing is not "7 new renderers":

| proposed | actually is |
|---|---|
| `recap` | `takeaways` — exists |
| `concept_diagram` | `visual_diagram` — exists as a linear chain |
| `checklist` | `bullets` with a tick glyph — exists |
| `hook_result` | the **picture box**, holding a terminal still |
| `command_callout`, `terminal_output`, `file_tree` | the **picture box**, holding a different asset |
| `prerequisite_checklist` | `bullets`, check-marker variant |
| `error_fix` | two-column `value_table` — exists, with the `_boundary_rows` caveat |
| `screen_recording` | the **picture box**, holding video |
| `checkpoint_quiz` | needs a timer — a per-frame mutation channel that does not exist |

So: **one new primitive (a media box that accepts a still, a clip, or a file
tree) plus content templates**, not seven renderers. That is the same
profile-plus-template seam as §4.1, and the fourth input to arrive at it.

### 12.5 Adopt, and one rejection

**Adopt.** OBS as the recorder (free, correct tool, not currently installed);
screen-capture hygiene — "hide notifications, unrelated folders, passwords,
bookmarks, and personal files"; the Why / What to type / Expected result / If it
fails pattern per command; and burning in captions always.

**The secrets rule is a genuinely new risk class.** A recorded terminal is
precisely where API keys, usernames, home paths and private filenames leak. It
is the mirror image of the untrusted-input risk in A14, and it appears in
**neither** of the five inputs' risk sections as a gate — only as a checklist
line. It should be a candidate gate, and it belongs with §11.6's rights question
because a leaked key in a published video is a disclosure, not a blemish.

**Reject: "cut narration 20% because people read faster than they listen."**
The conclusion is right *for us* and the reason is backwards. Narration sets the
pace; viewers do not read narration. Our own measurement says the same thing with
a number: **401 words → 261.643 s against a 240 s target = 109%**, so ~20% is
about right — because we are over target, not because of how fast people read.
Adopt the trim; reject the rationale and do not let it propagate into a rule.

**Also reject: Remotion** — which this input itself advises against. It is a
React/Node stack for a Python/ffmpeg pipeline, and §6 already ruled the
generative path optional rather than required. **Manim** is absent, needs an
install, and earns its place only for mathematical or algorithmic scenes.
Those two tools — OBS, and optionally Manim — are the entire install list.

### 12.6 A lane that dissolves the project's blocker

The proposal is a **tutorial channel**: build a thing on camera, explain it, fix
its errors. Its source material is the terminal and the code.

That matters more than it looks. The project's hardest blocker is that **no
narrative document exists on this machine** (`DESIGN.md` § *Open decisions* 1),
and every lane we scoped is downstream of it. A tutorial channel's source is the
work itself, so it is the one lane that can start **today**, with no missing
document and no external content licence — the user's own screen and their own
voice, which is also the cleanest rights position in the project (§11.6).

It is self-demonstrating: the tool teaches the tool.

---

## 13. Input 6 — "stop calling it video generation"

The sixth input reframes the project rather than extending it, and its single
most useful sentence is a framing correction:

> *"Stop thinking of your project as 'video generation.' Think of it as a
> reliable AI teaching-production system. Your real product quality will come
> from what happens **before rendering**."*

**That is already where five rounds of measurement landed** — independently, from
five specialists and four external proposals. §1 (the narration gate), §7
(animation is a rendering-loop problem we already own), §11.3 (the only working
compositing path), §12 (real footage beats generated footage), and now this. The
project stopped being a video problem several reviews ago.

### 13.1 The priority table is ours, arrived at independently

| their priority | our ledger |
|---|---|
| 1 stable structured scene plan | exists — but `schema.py` drops 3 rendered fields on round-trip (a landmine) |
| 2 source grounding + evidence links | **A1/A2 + `claim_id` (§9.6)** — our #1 blocker |
| 3 natural narration scripts | exists |
| 4 deterministic quality gates | exists — **and is the thing §1 says is insufficient** |
| 5 real practical-demo assets | **A19/A21** — the picture box |
| 6 reusable scene-template library | **§4.1 `TopicProfile`** — the seam |
| 7 per-scene editing/regeneration | **A13** — highest-value unbuilt |
| 8 viewer feedback and metrics | **§9.9** — unknowable locally |
| 9 advanced visuals / AI clips | **§6 T2/T3** — optional, correctly last |

Nine for nine. Two corrections:

- **#2 and #4 are one item, not two.** Gates that do not read the narration are
  not "deterministic quality gates", they are deterministic checks on a
  different field. A gate is worth what it can fail on.
- **The rights blocker (§11.6) sits *prior* to all nine.** Eighteen third-party
  recordings is a distribution surface, and `grep` for
  `consent|copyright|redistribut` across the doc tree returns 0 hits. It is not
  item 10; it is the thing that must be true before any of the nine is worth
  doing.

### 13.2 Two things in it that are blocked or wrong

**Its Milestone 2 cannot run.** The roadmap says *"Generate Hindi and Marathi
narration from the same approved storyboard."* §9.2 measured both languages
**forbidden outright** on the default profile — the pure-English gate counts 21
*romanised Latin* markers, so Devanagari scores 0 and is reported as pure
English — and the `english` profile returns "pure English legal" **before reading
a token**. The fix is small and known (`_has_non_latin_script` already exists in
`text.py`; make the script gate script-aware), but Milestone 2 as written
presumes a capability that does not exist.

**"Shorten plan automatically" is a B3 violation shipped as a default button.**
The wizard mock-up's over-target state reads `⚠ Plan exceeds target by 27
seconds` and offers `[ Shorten plan automatically ]` as the suggested action.
Engine ledger **§B3** rules: *"Deterministic repair may not remove teaching
material to satisfy a length or layout preference."* A one-click shorten button
is exactly the banned shape, made easier. The correct UI is the three options
`DESIGN.md` already lists — a concise overview, a multi-part series, or a longer
duration with the user's approval — and the user picks.

### 13.3 New, and worth adopting

**1. `needs_user_input` as an output channel.**
> *"If information is missing, output a `needs_user_input` item rather than
> guessing."*

This is the cheapest available mitigation for the §1 blocker. Today the LLM fills
gaps silently, which is why a fabricated date measures `grounding: clean`. A
declared gap is a routed question instead of an unmeasured assertion, and it is
one output field plus one gate check.

**2. Demo-first inverts the architecture order.** Three production modes are
proposed — demo-first, text-first, hybrid — with **hybrid as the default**, and
the important part is who goes first. Today the engine is *LLM-first*: plan, then
render. Demo-first is **the user records first and the LLM plans around what
exists.** That makes A22 structural rather than advisory, because the recording
*is* the verification: a command the viewer will type has already been run on
camera. The LLM's job shrinks from "decide what is true" to "decide what to
explain about what has been shown."

**3. Three text channels, not two.** `display_command` / `narration_text` /
`caption_text` as separate fields. The engine has two (slide text vs `spoken`)
and **derives** the third — and the derivation is precisely what fails for a
command: `uv --version` is not speakable, which is why §11.4 measured captions
collapsing to zero without word timings. An explicit caption field is a third
independent channel, and it is the one a terminal tutorial cannot do without.

**4. "Does the asset exist" as a gate.** The input's responsibility table puts
it under *"your code decides"*, and no other input proposed it. It is not
hypothetical: there is a **measured precedent for exactly this failure** —
caller-preplaced files in `output/<name>_audio/` are **silently overwritten**
(`video.py:818-821`) and the build reports PASS on its own TTS. The moment A21
lands and scenes can reference assets, this gate is what stops the same silence
recurring one layer up.

### 13.4 The 1080p question, measured

The proposal specifies 1920×1080 / 30 fps; we render 1280×720 / 24 fps. Both
halves of that are worth a number rather than an opinion.

| measured | 720p | 1080p | ratio |
|---|---:|---:|---:|
| Pillow draw + PNG encode, same content | 76.5 ms/frame | 138.2 ms/frame | **1.81×** |
| ffmpeg libx264 CBR 700k, 10 s @24fps | 4.81 s | 15.54 s | **3.23×** |
| output size at the same bitrate | 0.9 MB | 0.9 MB | 1.00× |

**Pillow is not the bottleneck.** ~45 frames per video × 76.5 ms = **3.4 s, which
is 0.4% of the 828 s render leg.** Going to 1080p would add **2.8 s**, or 0.3% of
the leg. The cost is entirely in the encode, at **3.23×**.

Extrapolating that 10 s encode across a 261.6 s video gives ~125 s at 720p versus
~406 s at 1080p — so **1080p would add roughly 281 s to an 828 s leg, taking the
build from ~911 s to ~1190 s (+31%) for a 1.5× linear legibility gain.**
*Labelled as an extrapolation: the 3.23× ratio and the 0.4% share are measured;
the whole-leg figure assumes the encode dominates the leg, which I did not
isolate.*

**Ruling: the legibility gain is real and the cost is bounded and known, so this
is a decision rather than a rejection** — and it should be decided *after* A21,
because more text in the frame is worth more legibility, and after the template's
type scale is fixed, since graphic-reviewer measured that one font size serves the
youngest band at 97% of threshold and the oldest at 37%. Raising resolution
without fixing type scale buys sharpness nobody can read.

### 13.5 The first vertical slice is fully specified — and buildable

One Markdown lesson, four recorded terminal clips, one verified-command JSON
file, beginner audience, English, 3–4 minutes, ten scenes, manual storyboard
review, then title / checklist / command overlays / recap plus the clips, with
captions and a quality report.

That is 4 clips and 10 scenes, so **6 scenes are graphics-only** — which is
exactly the §12.4 shape: one media box plus templates, not ten renderers. And the
"manual storyboard review" step is the human-approval gate that §10.1 identified
as the one thing the engine has a machine version of and no human version of.

**This is the smallest thing in the whole engagement that proves the architecture
end to end, and it needs nothing we do not already have** — no GPU, no cloud, no
missing document, no external licence.

---

## 14. Input 7 — narration modes, and the voice-clone question

A detailed treatment of the audio side, following the ruling that narration is
the user's own recorded voice. **Adopted substantially; three things need adding
and one needs stating as a rule.**

### 14.1 Adopt

| item | note |
|---|---|
| **Three narration modes** — `recorded_voice` · `tts_standard_voice` · `cloned_voice` | one field on the plan. The engine already has `voice.py` as a profile registry, so this is an extension, not a new subsystem |
| **Record scene-by-scene, not one long file** | this *is* the per-scene regeneration gap (`A13`) expressed as a recording convention. The two are the same requirement seen from the audio side |
| **Recording settings** — WAV, 48 kHz, **mono**, 16/24-bit, 10–15 cm, pop filter | mono matters: our measured rate is 1.788 words/s and a stereo pair doubles the decode for no gain |
| **A per-scene script, never raw JSON** | target duration, tone, pause points, narration, and the screen action separately. Consistent with the display/speech split below |
| **Five speech fields** — `display_text` · `caption_text` · `speech_text_{en,hi,mr}` | the **third** input to propose separating on-screen text from spoken text. Already in the ledger as `A26`; now with the field list |
| **Consent rules and a voice-profile record** | see §14.4 — this is a new *class* of artefact |
| **Per-scene regeneration with fallbacks for a failed clone** | a revised script, a different base voice, slower speed, a new reference, or the real recording. Exactly `A13` applied to audio |
| **"Narration is always the priority; music is none or extremely low during commands"** | correct, and one addition below |

### 14.2 Captions are a **gate**, not a pipeline step

The proposed pipeline lists *"generate captions from the final narration"* as
though it were free. With a recorded voice **it is not**, and the failure is
silent.

Measured: a recorded clip has no `WordBoundary` stream, so `_write_webvtt` returns
0 and **writes no `.vtt` at all** — and because of the `if vtt_cues:` guard the
build log simply omits the captions line. Captions go **55 → 0** with no
complaint. Every audio filter the proposed pipeline needs is present (verified:
`silencedetect`, `silenceremove`, `loudnorm`, `acompressor`, `afftdn`, `afade`,
`highpass`, `lowpass`, `aresample`, `volume`, `amix`).

**Two ways out, and the second is better:**

1. **Free, and good enough.** ffmpeg `silencedetect` measured on a real caller
   clip: **9 boundaries over 61.57 s = 6.84 s mean segment, 7.6 words/cue against
   the engine's `_VTT_CUE_WORDS = 8` — within 6%.** It restores caption *text*
   and sync. It does not restore reveal sync.
2. **Authored, and better.** Because `caption_text` is an explicit field, the
   text never needs inferring — only the timing does. This is the argument for
   `A26` being on the critical path rather than a nicety.

**A third route, and the cheapest of all:** the caller may hand over the word
timings their own recording tool emitted. For a phone or USB microphone it will
not have them, so route 1 is the default and route 3 is the upgrade.

### 14.3 A rule, from the third instance of the same pattern

The input supplies the licence split that this project has now hit three times:

| instance | tool's licence | artefact's licence |
|---|---|---|
| fonts (§9.7) | `Arial` named, nothing embedded | DejaVu outlines **rasterised into every MP4 frame** — Bitstream-Vera terms genuinely apply, while the `.pptx` has no font exposure at all |
| TTS voices (§9.7) | edge-tts is MIT-ish code wrapping a **consumer endpoint** | the *voice model's* commercial terms, which the code licence says nothing about |
| **cloning (here)** | Coqui TTS framework is **MPL-2.0** | **XTTS-v2 weights are under the Coqui Public Model License** — a different licence, on the same page |

> **Rule: check the licence of the artefact, the weights and the data separately
> from the licence of the tool that ships it.** A permissive licence on the code
> is the one thing that tells you nothing about what you may publish.

And the specific point this input gets right for the wrong reason: OpenVoice's
MIT licence covers **the code**. It says nothing about whether a particular
person's voice may be cloned. Those are separate questions — one is a software
licence, the other is personality and likeness. For a monetised channel the second
is the one that matters, and no repository README answers it.

**The input's own consent section is the correct answer to that**, and it is
better than its licence table.

### 14.4 The consent record is a new artefact class

Everything the pipeline emits is a build artefact. A voice profile is a **legal
record**, and it needs different properties: an owner, a timestamped consent, an
explicit allow-list of uses and languages, deletable reference audio, a named
clone engine, and a flag that a human must review before publication.

The proposed record is well-shaped. Two additions:

- **Reference audio must be deletable and provably so.** The clone engine may
  retain derived embeddings; the record needs a field saying whether deletion
  propagates, and if not, saying so plainly.
- **A visible disclosure option** — *"Narration generated using the creator's
  consented AI voice"* — is the right default for a public channel, and it is a
  render-time decision, so it belongs on the plan, not in a settings file.

Store it beside the plan and bind it into `plan_sha256` alongside `claim_id`, or
it will drift from the video it governs.

### 14.5 Two small corrections

**Duration target vs recorded duration.** The per-scene script states a *target*
duration; the recording will differ. Measured, the engine's no-timings fallback is
an **even split, which degrades 8 of 8 scenes** — one scene's final bullet held
16.76 s instead of 4.66 s, a **72% error**. With recorded audio, slide-to-audio
sync must be *planned per scene*, not inferred, and the remedy for a too-long
recording is **re-record, not trim** — trimming narration is a content change.

**Music gain needs a named reference.** "Extremely low" is not a specification.
Our loudness target is **−16.0 LUFS integrated** (absolute, measured by ebur128),
while a music bed is normally specified as **dB relative to the voice** — a
different quantity. The repo's rule applies: state which one, and measure it
rather than configuring it. §6 already rules music optional and open-licensed
only.

**On the hardware claim:** the machine is not "8 GB" — it is **4.8 GiB total,
1.9 GiB available, 4 cores of a 2017 i5, no GPU**. The conclusion is right and
understated: cloning is **infeasible** locally, not slow. Cloud or a later
machine, as the input says.

---

## 16. The net position

The three inputs, taken together, reduce to one change and one question.

**The change:** the engine cannot tell a true video from a false one, so stop and
fix that before anything else. `narration` is not gated; scene order is not read;
a fabricated `1998` and a fabricated `Congress` both measure `grounding: clean,
render-blocking: clean`. That is A1 + A2, and it is smaller than any proposal
above.

**The question:** is 4 minutes a target or a ceiling? Every duration
recommendation in all three inputs is downstream of it, and the engine's own
recorded position is that the target is advisory and the ceiling does not exist.
Until a human answers that, D1, D2, D3 and D11 cannot be re-litigated, and
E3/E4 cannot be sized.

**What none of the inputs changed:** the profile seam. `NarrationVoice` is
already exactly the right abstraction for one of three layers, with a registry
and a CLI flag. Planning and rendering never got the same treatment. That is why
the project is configuration and not a rewrite — and no external proposal
noticed it.
