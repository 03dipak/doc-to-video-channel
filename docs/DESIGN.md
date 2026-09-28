# Design record — any document to a YouTube channel

Status: **decided, not built.** Consolidates the mentor rulings from the
2026-09-27 session. Every number below was measured; the method is named.

Anchors are `symbol (file:line)` in
`../doc-to-video-tutor/src/doc_to_video_tutor/studio/`, verified at `a7d63e0`.
**Re-resolve before citing** — that advice is not optional, see
[`scratch.md`](scratch.md) §2.1.

---

## 0. The aim, stated so it can be falsified

Many documents in, many publishable videos out, across arbitrary topics, for a
viewer who watches along. Not "one document to one lesson".

An external reviewer proposed six acceptance criteria for the LLD, and the first
is the one that matters:

> A document class is **declared supported** only when a named profile exists
> for it, the profile's format allowlist admits the file, and a real build of a
> real document in that class reaches `VERDICT: PASS` with **zero** open
> findings. A class with no profile is *unsupported*, and the build must say so.

Without that, "any document" is a slogan.

---

## 1. The blocker

**The engine cannot tell a true video from a false one for narrative content.**

`_grounding_issues` (`plan.py:870`) is bag-of-ngrams against the whole document
and **does not read `narration` at all** — it reads `title`, `bullets`,
`takeaways`, `visual_diagram`, `code_snippet`. `narration` is the field the
viewer hears. It also fires only at *zero* lexical overlap, so two recycled long
words launder a wholly invented causal claim. And **no function in `guard_plan`
or `_render_blocking_problems` reads scene order at all.**

Measured — three injections, one at a time, into a real non-technical plan:

| injected | `guard_plan` | `_render_blocking_problems` | grounding |
|---|---|---|---|
| "Prior authorization was invented by **Congress in 1998**…" into `scenes[0].narration` | only pre-existing findings | **clean** | **clean** |
| the same sentence into `scenes[0].bullets` | only pre-existing findings | **clean** | **clean** (bigram `prior authorization`) |
| `scenes[1]` ↔ `scenes[2]` swapped | only pre-existing findings | **clean** | **clean** |

`1998` and `Congress` appear nowhere in the source (dated January 1, 2026; names
no legislative body).

A History or Forest-growth video's entire value is its dates, its order and its
causation. None of the three is checked. This is the only item that cannot be
fixed after publication.

**The gate it needs** — entity + temporal grounding on `scenes[*].narration`,
plus a non-decreasing date sequence across scenes:

```
E(x) = { \d{3,4}( AD| BC| BCE| CE)?  |  \d+(\.\d+)?\s*(%|km|miles|tons|m|feet|ft|kg|litres)
         ∪ every capitalised proper-noun bigram }
REQUIRE  E(narration) ⊆ E(source_content)      # surplus -> HARD reject
AND      the per-scene date sequence is non-decreasing across scenes
```

**Reject, never repair.** The engine already repairs grounding for slide text
(`_drop_ungrounded_slide_text`, `plan.py:2397`); extending that to narration
would silently delete a date, manufacturing a wrong-but-passing video. A domain
pipeline does not need this gate: an LLD's scenes are unordered capabilities,
and swapping two gate definitions is not a wrong video.

---

## 2. What else blocks publishing

Ranked by evidence strength. All measured from rendered pixels or from running
the real functions.

| # | Finding | Evidence |
|---|---|---|
| 1 | The section eyebrow is a **5-item software enum assigned by scene index** — `_infer_section` (`plan.py:818`) falls back to `spread[(idx-2)%4]`. A scene titled "Old Growth: Two Centuries" is labelled **`EXAMPLE`**; "Gothic Wars and the Divide" gets **`HOW DOES IT WORK?`** | ran the real functions on History and Forest-growth plans. Not fixable by prompt — the enum is enforced in a post-pass. **One field is doing three jobs**: validation enum, rendered chrome, positional fallback generator. That triple duty is the defect, not the vocabulary size. |
| 2 | The literal word **`opening`** is burned into the title card: `'Chaliye verification samajh ke shuruwat karte hai. opening'`. `_sanitize_opening` (`plan.py:849`) cleans the *spoken* string only | on screen 7 s. `script.txt:7` documents the leak as accepted. A JSON key name is the first thing a viewer reads. |
| 3 | **`doc-to-video-tutor v0.1.0 — learn by listening`** on every frame — `BRAND_NAME = PACKAGE_NAME` (`config.py:352-356`) | 100% of runtime, 10/10 slides, 9/9 scenes |
| 4 | **The thumbnail cannot be made from this composition.** Rendered at 210 px display width: title 4 px, body text **zero** surviving pixels, eyebrow 1 px. Reaching an 8 px cap height needs **48.8 px** in-frame = **2.1×** the current 23 px title, one line ≤4 words, centred in the top 45% — and the eyebrow (0.4×) and body (0.35×) must be **deleted**, not shrunk | downscale-and-measure, LANCZOS, ink-row extent; reproduced at two scales |
| 5 | **28 s of 261 s (11%) is near-black.** 3.8% mean ink-pixel density over 65 frames; worst frame 0.4% (one rule line). Body region 3.71 in unused on slide 5 | band taken from pptx geometry (divider 1.28 in → footer 7.01 in), not eyeballed. Bounding-box extent reads 69% — that is a *ceiling*, not a fill; 3.8% is the density |
| 6 | `MIN_SCENES = 5` is **RENDER-BLOCKING on a 1-scene and a 3-scene source**, firing before any content is judged. Meanwhile `_unspoken_visual_claims`, `_slide_text_language_problems`, `_source_coverage_gaps` and all three enrichment triggers pass with **nothing to look at** (0/3, 0/1, 0/1 populated) | ran the suite against a converted transcript segment and a policy document |
| 7 | `mhe-mix` returns the **identical verdict on correct English and on `Blorptastic zibblewump frimble dromp`** — "0 marker hit(s), < 3 required" | it counts 21 romanised Devanagari markers. It is a 7B-contamination detector, not a language gate, and must not be reused as one |
| 8 | `_POINTER_KEYS_RE` can stamp a **hard-coded `eval/baselines/v1.2.0.json`** payload onto a history slide when the source contains `{schema_version, baseline_id, path}` | read from source; a latent wrong-artifact generator that is grounded today only by coincidence |
| 9 | Two different burned-in denominators for one deck: deck `8 / 10`, video `4 / 9`, same scene. Two renderers, two brand systems | deck callouts are amber boxes; video callouts are blue left-bars |

---

## 3. The corpus, measured

`../rag-apidriven-pipeline/data/transcripts/`, three modules of six `.docx`
sessions each.

| | chars | words | timestamped segments | words/segment |
|---|---:|---:|---:|---:|
| module1 | 718,388 | 126,480 | 124 | 1,020 |
| module2 | 928,145 | 161,402 | 182 | 887 |
| module3 | 776,546 | 138,714 | 216 | 642 |
| **all** | **2,423,079** | **426,596** | **522** | median **191** |

Each segment is already structured:

```
00:13:08 - 00:14:55
Introduction to Parameter Efficient Fine Tuning
Hello, good morning. So hope I'm audible. ...
```

**522 timestamp ranges, 97.1% (507) followed by a title-like paragraph**
(median 42 chars). The 15 that are not are segments where no heading was written;
the fallback is the first sentence. That is a regex, not a heuristic problem.

**`.docx` is not a supported input.** `cli.py:359` advertises `.md, .txt, .pptx`;
`util.py:152` special-cases only `.pptx`/`.ppt`. Zero of the 18 files are
loadable today. The extractor is ~30 lines — a `.docx` is a zip, and
`word/document.xml` with `</w:p>` → newline is the whole of it. No new
dependency.

**What this kills from the external proposals:** the read window is irrelevant
here (a median segment is ~1,200 chars against a 12,000-char window), the
map-reduce front end is unnecessary, the scoring formula has nothing to select,
and a 4-minute cap is moot (the median segment is *half* a 4-minute video).
Nothing needs cutting. The instructor already selected, by writing the titles.

---

## 4. The design

### 4.1 The seam is a per-domain profile, and the precedent already exists

`NarrationVoice` (`voice.py:146`) is a frozen dataclass with a registry
(`_VOICES`, `voice.py:265`) and a CLI flag (`--narr-voice`, `cli.py:365`).
Planning and rendering never got the same treatment.

**Consequence, and it is the load-bearing evidence for this whole record:**
`narration.py` + `voice.py` (1,448 lines) need **ZERO** changes for a general
engine. One of three layers is already a profile. This is a configuration
problem wearing a rewrite's clothing.

`TopicProfile` plugs at `plan_lesson` (`plan.py:2082`) and carries six things:

| field | replaces |
|---|---|
| `scene_labels` | `_SECTIONS` (`config.py:234`), `_ENUM_HINTS`, `_infer_section`'s positional spread |
| `scene_counts` | `MIN_SCENES` / `TARGET_MAX_SCENES` / `AUTO_TRIM_MAX_SCENES` |
| `enrichments` | the hard-wired pair at `plan.py:618-619` |
| `voice` | already exists — reuse |
| `decision_prompt_rule` | the INTERVIEW FRAMING rules at `config.py:131-137` (**not** the field name: `design_decision` has 27 read sites; renaming it is 27 edits for zero gain) |
| `source_shape` | provenance only |

A **`narrative` profile is required**, not optional. The `english` profile's
`dd_leads` (`Reason:`, `Design choice:`, `The real reason:`) and `bullet_leads`
(`A practical way to put it is`) assert *mechanism plus use-case*, which pushes
the narrator toward a causal structure a history video does not have — it
manufactures the exact defect §1 says nothing catches.

### 4.2 The adapter

Ingestion dispatches on source shape. An adapter returns exactly:

```
content, concepts, concepts_total, concepts_in_window,
topics, full_text, truncated, source_files
```

- **concept doc** — reuse everything; `_concept_headers` (`plan.py:1233`) *is*
  this adapter already and should move into the adapter rather than be called
  from `cli.py`.
- **transcript** — new: a `.docx` branch, a `HH:MM:SS - HH:MM:SS` segmenter, and
  segment titles as `concepts`. Two breaks shape-A does not have: 522 segments
  into a 12-slot cap that `_concept_groups` then merges into `" & "`-joined
  labels which hit `_TITLE_CAP`; and ~15 segments with no body, whose score falls
  under `_CHUNK_MIN_CONFIDENCE` (0.18) into `low_confidence`. Needs a
  per-segment assignment, not the exclusive one-per-scene greedy at
  `plan.py:1639`.
- **narrative prose** — new: segmentation only.

### 4.3 The highest value-per-line change in this record

`_markdown_sections` (`plan.py:1525-1526`) returns a single
`("", content[:1200])` pair when the source has no `^#{1,3}` heading.

**Measured on a prose source: 1 of 6 scenes got a `source_chunk`; scenes 2–6 got
`None`, `status: "unassigned"`.** That kills re-hydration and thin-repair for
N−1 scenes. The grounding substrate is simply absent.

A `\n\n+` paragraph-boundary fallback — **~12 lines, one function, both renderers
unaffected** — makes it 6 of 6 and lets the existing exclusive assignment work
unchanged. Do this first.

### 4.4 There are five genuinely distinct content shapes

Rendering vocabulary is 9 blocks. Domain-neutral: `bullets`, `steps`,
`takeaways`. ML-gate-only (measured never to fire elsewhere): `status_badges`,
`value_table`, `json_snippet`. Process-only: `flow`, `visual_diagram`.
Teaching-only: `analogy`.

| shape | topics | needs |
|---|---|---|
| timeline | car evolution, history | a **rendered date axis** — nothing exists; `flow` is unordered by date |
| time series | forest growth | numeric-over-time. `value_table` is nearest but `_boundary_rows` **rejects** any pair without a decimal or unit, so a growth curve can never become a row |
| causality | history | a **new field**. `design_decision`'s "X not Y because Z" is the wrong shape — measured `_contrast_sentences` → `[]`, 0 cards filled |
| decision ledger | product development | the one domain `design_decision` genuinely fits |
| mechanism | AI-model development | what `flow` / `visual_diagram` were built for, and the only topic where `--->` is a truthful metaphor |

**One profile is not enough**: timeline and time series need a new primitive in
**both** renderers, and causality needs a new *field*, not a new profile.

An external slide-design proposal, assessed against the source in
[`SLIDE-DESIGN.md`](SLIDE-DESIGN.md), reached **the same five shapes by a
completely different method** — two unrelated analyses, one answer, which is why
the shape count here is treated as settled. That document also finds the
eyebrow vocabulary is a three-label extension rather than a redesign.

**But do not start there.** Two blocks × two renderers, unvalidatable until a
shape-D document exists, and none does.

---

## 5. Four phases

| phase | content | size |
|---|---|---|
| **0 — safe to publish** | grounding reads `narration`; the entity+temporal gate of §1; remove the three on-screen leaks (§2 items 1–3); emit `0:00 Title` chapter markers | 1 gate + 3 one-liners |
| **1 — one real non-technical topic, end to end** | the 12-line paragraph fallback; a `narrative` profile; one real document | ~150 lines |
| **2 — the profile seam + adapters** | `TopicProfile`, the adapter interface, `.docx` | ~70 + ~30 lines |
| **3 — the channel** | three artifacts, below | new artifacts only |

### Phase 3 needs three artifacts, not one

1. **corpus manifest** — one row per segment: `segment_id` (= `text_sha256`),
   `doc_id`, `ordinal`, `char_start/end`, `heading`, `word_count`. Written
   independently of any build, **before** the planner's read window, so
   truncation is detectable rather than invisible.
2. **video manifest row** — `video_id`, `playlist_id`, `doc_ids[]`,
   `source_segment_ids[]`, `scene_count`, `word_count`, `duration_s`,
   `toolchain_version`, `plan_sha256`.
3. **channel index** — `playlist_id → ordered [video_id]`, plus
   `segments_total / segments_claimed / segments_with_video`, computed by
   joining (1) and (2) on `segment_id`.

**The load-bearing field is `source_segment_ids[]`.** Without it there is no edge
from a video to the corpus at any scope, so cross-video overlap is undetectable
and no restructuring can be checked rather than asserted. `chunk_digest` is
per-scene and `section_digest` is per-section; neither is emitted at corpus
scope nor compared across builds.

The playlist reads (3); the coverage claim is a **query over (1)⋈(2)**, never a
field a build writes about itself — which is exactly what
`unclaimed_source_sections: 0` currently is.

---

## 6. "Interactive" — measured per meaning

Nothing the engine emits is reachable from a YouTube watch page.
`grep -rn "chapter" src/doc_to_video_tutor/studio/*.py` returns **zero hits**;
there is no chapters artifact. The viewer interacts only with YouTube's own
player.

| meaning | verdict | cost |
|---|---|---|
| (a) clickable chapters | **0.00 in** — the eyebrow band is 84% empty; a `PART 2 / 6 · 00:42:10` string renders ≈1.98 in of a 10.00 in box. **No code exists** | tiny |
| (b) companion transcript | **feasible now** — `.vtt` is well-formed (55 cues, 7.29 words/cue) | 0 |
| (c) on-screen questions | new block in **both** renderers | 0.60–0.90 in |
| (d) viewer feedback loop | **out of reach** — needs the YouTube API; no pixel can produce it | — |
| (e) follow-up links | `plan['topics']` already exists; must be in the description to be clickable | 0.90 in end-card |

**Recommendation: (a) + (b).** Near-free, and they are what "watch along"
actually means.

---

## 7. Channel economics

Per video, from `output/mod03_gates_v_0002`:

| axis | measured | 100 videos | 500 videos |
|---|---:|---:|---:|
| planner samples | 2 | 200 | 1,000 |
| TTS calls (= clips) | 9 | 900 | 4,500 |
| scenes | 8 | 800 | 4,000 |
| wall clock (**mtime proxy**) | 911.6 s | 25.3 h serial | 126.6 h serial |

The 911.6 s is **91% render leg**, not the LLM (planner 50.4 s, TTS 21.9 s).
Wall clock is a proxy: no artifact records elapsed time, and attempts are not
persisted, so a rejected third sample would be invisible.

- 522 segments ÷ 8 per video = **65 videos** for one pass of coverage.
- 426,596 words ÷ 401 spoken words = **1,064 videos** for verbatim restatement.

The gap between 65 and 1,064 *is* the abstraction budget — and §1 is why the
current gate cannot govern it.

**Duration, for reference.** Measured rate 107.276 wpm, structural silence
37.36 s (title hold 4.0 + 3.0 × 9 clips + end hold 6.0), so a 240 s MP4 holds
**362 words**. A published word budget of 450–600 is +24% to +66% over that
ceiling; 540 words is a **5 min 39 s** lesson here. The build's own
`--minutes 4.0` is advisory — the shipped artifact is 261.643 s = **109.0%** and
`duration_verdict` returns `OK` with no finding.

---

## 8. The contract is false, not narrow

Four statements say the **opposite** of this aim:

| where | says |
|---|---|
| `README.md:115` | multiple input files "are merged into one lesson" |
| `README.md:121` | rewrites content as a "3-part classroom lesson (What / Why / How)" |
| `README.md:119` | the format list `.md` / `.txt` / `.pptx` — but `util.py:152` routes only `.pptx` there and **everything else** to `read_text()`. A PDF is not rejected, it raises `UnicodeDecodeError` *mid-build, after the LLM call*. There is no format gate at all |
| `../doc-to-video-tutor/docs/LLD-narration-voice.md:645` | the 12,000-char cap, as a fixed property |

`../doc-to-video-tutor/docs/CALL-FLOW.md` presents itself as the file:line reference and has **0 of 21**
symbol anchors resolving (median drift −813 lines; `plan_lesson` off by 558). It
needs a standing header, not a rewrite — it already says at `:7-9` to treat its
lines as a search index, and that disclaimer was never promoted.

**The ingestion contract is now written** — `../doc-to-video-tutor/docs/LLD-narration-voice.md` §10.6, added
this session, recording the measured 37% silent loss and the rule that a build
which silently drops source may not claim to cover the document.

---

## Open decisions

Three, and only the user can answer them.

1. **Supply one real narrative document.** A history chapter, a book section on
   car evolution, a science explainer — anything that is *not* a spec.
   `find -iname "*histor*" -o -iname "*narrativ*"` across 24 sibling repos
   returns **0 hits**. Every shape-D verdict in this record is static read plus
   transcript/policy measurement; the agent testing generality had to write its
   own synthetic Ford excerpt. **This is the hardest blocker.**
2. **Which "interactive"?** Recommendation: chapters + transcript.
3. **Channel shape** — 65 videos at 8 segments each, ~174 at ~6 min, ~104 at
   ~11 min, or ~500 one per segment.

---

## Rejected, with reasons

**The full ledger across all three external inputs is [`DECISIONS.md`](DECISIONS.md) §4 — this table is the summary.** Kept so they are not re-proposed.

| proposal | verdict |
|---|---|
| map-reduce front end (chunk → summary → master outline → scored selection) | **Unnecessary here.** A median segment is ~1,200 chars against a 12,000-char window. The instructor already selected by writing the titles. As specified it also *moves* the ceiling one call rather than removing it — it sits downstream of the cut — and its 15–30 s chunk overlap is architecturally impossible, since assignment is globally exclusive by design and that fixed three defects. |
| a weighted scoring formula over importance / audience value / novelty / evidence / visual potential | **Unverifiable by construction.** 2 of 6 axes have a deterministic analogue and neither carries weight. Every gate works by comparing two independently computed artifacts; these scores have no second computation to differ from. A new *assertion*, which is worse than a new measurement. |
| "fail the build if estimated duration > 240 s" | **A target change dressed as a gate.** `duration.py:261-267` records why the bands are advisory: *"the remedy is source-grounded teaching, which no mechanical step can supply."* It would reject all three recent builds (253.6 / 254.6 / 261.6 s) that the engine itself labels `OK` inside its own 220.8–276.0 s zone. If a hard ceiling is ever wanted it belongs at the **top of the band**, on **measured MP4 seconds** — never per clip, whose rate scatter is 1.466× (CV 11.6%) while the lesson total is stable to 1.63%. |
| `segment_id` / `start_time` evidence layer | **Already satisfied, by the source format.** I ruled this "inapplicable, no ASR" while reasoning from an LLD; it is false for a transcript corpus. The transcripts *are* timestamped, titled segments. |
| keep both renderers plus an agreement test | **Rejected.** It detects today's drift, not tomorrow's, and there are already four instances of a fix landing in one renderer and missing the other. |
