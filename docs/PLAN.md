# PLAN — how we start

**Status: ready to execute.** Six review rounds, four external proposals, six
specialist passes, all measurements in [`DECISIONS.md`](DECISIONS.md) §1–§13. This
file is the plan of record: the lane, the use case, the contract, the
architecture, the build order, and what we are refusing to build.

| | |
|---|---|
| Engine | `../doc-to-video-tutor` at `a7d63e0`, 315 tests, ruff + mypy clean |
| Machine | 4.8 GiB RAM (1.9 free), 4 cores i5-7200U, **no GPU**, 860 GB disk |
| Corpus | 18 `.docx` transcripts, 522 timestamped + titled segments, 426,596 words — **local test fixture only, never a publishable source** (`RIGHTS.md` §0) |
| Ledger | 27 build items, all assigned to a wave below |
| Not committed | nothing in either repo |

---

## 1. The product, in one sentence

> **Turn the user's own recorded teaching and their own documents into narrated,
> source-traceable tutorial videos, where every command shown was verified and
> every frame is deterministic.**

Not a video generator. The quality lives before the render — that is the one
conclusion six rounds agreed on, reached independently five times.

## 2. The lane we start with, and why

**A practical software-tutorial channel. Demo-first.**

Not chosen for taste. It is the only lane that needs **nothing we do not have**:

| requirement | tutorial lane | other lanes |
|---|---|---|
| a source document | the code and the official docs | **a narrative document, which does not exist on this machine** |
| AI video generation | none — real screen recording | required |
| external content licence | none — the user's own screen and voice | unresearched, and `docs/quality_review.md` §B12 records the risk |
| GPU | none | required for anything "real-looking" |

It is also **self-demonstrating** — the tool teaches the tool — and the format
was the first proposal in four rounds that is *measured compatible* with the
duration contract: 8–10 scenes over 4–6 minutes returns `feasible: 1` from the
engine's own `word_budget`, because it specifies structure and never invents a
word count.

## 3. Use case

**Primary — the working tutorial**

> **Actor:** a developer or trainer who knows the tool and cannot spare the hours
> a video takes. **Trigger:** they have a topic and have already recorded 3–6
> short terminal clips. **Preconditions:** a Markdown or text lesson, a verified
> command list, the recordings. **Main flow:** plan → **human review** → per-scene
> render → gates → MP4 + captions + storyboard + quality report. **Value:** a
> publishable, accurate, editable lesson in minutes instead of a day.

**Secondary — the lecture repackaged**

> **Actor:** a course creator with recorded sessions. **Trigger:** the 18
> transcripts. **Flow:** transcript → segments (already timestamped and titled) →
> lesson plan → video. **Blocked on:** Wave 0 only (`.docx` is unreadable today).

**Explicitly not v1:** cinematic generation · songs and lyrics · 9:16 Shorts ·
vertical · audiences under 13 or over 60 · five content types at once.

## 4. Input / output contract

**In (v1):** `.md` · `.txt` · `.docx` · text `.pdf` (after an install) · `.pptx` ·
a text transcript · **3–6 user-recorded `.mp4` clips** · a verified-command list ·
**per-scene recorded narration, one WAV per scene** (mono, 48 kHz, 16/24-bit).

**Narration mode is one plan field:** `recorded_voice` (v1) · `tts_standard_voice`
(fallback, already exists) · `cloned_voice` (**later, not v1** — `DECISIONS.md` §14.3:
a permissive licence on the code says nothing about whose voice may be cloned).

**Record per scene, never one long file** — that convention *is* `A13` seen from the
audio side. It is also why captions must be a **gate**: a recording carries no
`WordBoundary` stream, so measured captions go **55 → 0 with no log line**. ffmpeg
`silencedetect` restores them at **7.6 words/cue against a target of 8 (within 6%)**,
and an authored `caption_text` field removes the need to infer the text at all.

**Five text channels, per language:** `display_text` · `caption_text` ·
`speech_text_en` · `speech_text_hi` · `speech_text_mr`. The command stays exact on
screen; each language gets its own speakable form.

**Out (v1):** `final.mp4` (16:9) · `.srt` captions · `transcript.txt` ·
`storyboard.json` · `source_map.json` · `quality_report.json` · `thumbnail.png` ·
an editable `scene_NN/` folder per scene.

**The rule that makes it trustworthy:** the LLM decides *what to explain*. Code
decides *whether JSON is valid, whether text fits, whether duration fits, whether
assets exist, and whether commands are verified.* No exceptions.

**Duration is derived, not declared.** RULED 2026-09-27. It is neither a target
nor a ceiling — it falls out of how much explanation the source actually carries:

```
duration = (admitted_words × 0.5825 s) + structural_silence_seconds(clips)
```

`--minutes` stops being a control and becomes an **optional cap, default off**; the
real duration is **reported**. If it lands in the band, ship. If over, the user
picks one of three options — a concise overview, split into parts, or longer — and
**never** a one-click shorten, which is engine-ledger §B3. If under, the engine's
own recorded remedy applies: add source-grounded teaching.

This closes D1, D2, D3 and D11 permanently. **Stop asking the question.**

**Narration is the user's own recorded voice.** RULED 2026-09-27, with a fixed
channel intro. Three consequences, all measured:

- **`--audio-dir` is now on the critical path**, not an optional wave. With caller
  audio, the word-count gates stop measuring duration at all, so they must be
  re-expressed as **seconds** (20 words = 11.7 s, 90 words = 52.4 s at the
  engine's 103 wpm) and an audio-contract gate must exist. Today a supplied clip
  at **−22.3 LUFS ships under `verdict: PASS`**.
- **The language blocker disappears.** The `mhe-mix` pure-English gate that
  forbids Devanagari Hindi and Marathi exists to police *synthesised* speech. If
  the user records, that gate has nothing legitimate to say about the spoken
  track.
- **The intro is one reusable asset, rendered once.** ~18 words ≈ **10.1 s** of
  speech, ≈13.1 s with a pause; a 12-word outro ≈ 6.7 s. A 9-scene video becomes
  **12 clips** and structural silence goes 40.0 → **46.0 s**. That is the honest
  planning number, and the intro file is byte-identical in every video, so it is
  copied rather than re-recorded.

## 5. Solution architecture

```
INPUT            ADAPTER              PLANNING            PROVENANCE
.md .txt .docx ─► load_documents ─► _markdown_sections ─► source_sections[]
.pdf .pptx         (format gate)      paragraph fallback   section_digest
transcript      ─► segmenter          (A6)                 chunk_digests
.mp4 clips     ─► asset register                           source_assignment[]
                     │                                        claim_id  ◄── A22
                     ▼                                          │
                  TopicProfile ──► plan_lesson ──► guard_plan ──┤
                  (A10)           scene plan      (A1, A2, A24)  │
                     │                │                          │
                     ▼                ▼                          ▼
                  RENDER          GATES                    *.verify.json
            slides.py  pptx.py   _render_blocking          (the evidence)
            media box  (A21)     pre-audio gate
            2 renderers         audio contract (A18)
                     │
                     ▼
            assemble_video ──► ffmpeg ──► MP4 + SRT + captions + chapters
```

**Two invariants that constrain everything:**

1. **Two renderers.** `pptx.py` and `slides.py` are separate layout
   implementations. A fix has landed in one and missed the other **four times**.
   Every layout change ships in both, or in neither.
2. **Reserved, not reflowed.** The row stack reserves space for every bullet
   whether or not it is drawn, so reveal variants are pixel-identical. Any
   per-frame element (a timer, a kinetic caption) must be **chrome in a fixed
   slot**, never content that re-lays-out.

## 6. Free sources — the honest answer

For **this lane there is almost nothing to license**, and that is a design
property, not luck:

| need | source | status |
|---|---|---|
| screen recordings | **the user's own** | cleanest rights position in the project |
| narration | **the user's own voice**, or edge-tts | TTS commercial terms are **unresolved** — `pyproject.toml:13-16` calls it a consumer endpoint |
| commands & docs | official tool documentation | a **citation**, not an asset |
| diagrams | generated from the plan, deterministically | no licence |
| terminal stills | extracted from the user's own recordings | no licence |
| fonts | DejaVu, rasterised into the MP4 | permissive, **verify before publishing** — `LLD:1013` is the only grant in the tree |
| music | optional | **the only external content question in v1.** Open-licensed only, and the *model's* licence if generated |

**What is not free and not cleared:** nothing has a `LICENSE`, a `NOTICE`, or a
`license` field anywhere. Before any public release, four things must be settled
in writing: the TTS voice terms, the DejaVu/glyph terms for the MP4, the
`BRAND_NAME = PACKAGE_NAME` decision (a third party's name is currently burned
into every frame), and the LLM-output terms.

**Tools to add — two, both small:**

| tool | why | cost |
|---|---|---|
| `python-docx` | **0 of 18 corpus files are readable today**; `.docx` raises `UnicodeDecodeError` | 1 package |
| OBS Studio | the recorder. Free, correct, and the format demands real footage | 1 install |

Optional later: `PyMuPDF` (text PDF), `matplotlib` (charts — a blocked block
type), `tesseract` (scans), `Manim` (math scenes only). **Not** Remotion — a
React/Node stack for a Python/ffmpeg pipeline.

## 7. Build order

Five waves. Each has a **done-when** that can be checked, and no wave starts
before the previous one passes.

### Wave 0 — the front door · ~45 lines · *nothing exists without this*

| item | what |
|---|---|
| A5 | `.docx` reader (a zip; `word/document.xml`, `</w:p>` → newline) |
| A6 | paragraph-boundary fallback in `_markdown_sections` — **12 lines, the best value in the ledger** |
| A15 | hard input-format gate: allow-list and `raise` at the door, before any LLM call |
| A16 | `--read-window`, and report the omitted fraction beside coverage |
| A30 | fix the 8 dangling `doc/design/03_lld_tests.md` references — the README's headline example points at a file that does not exist |
| A11 | standing header on `CALL-FLOW.md` (51 unique anchors, symbol→line pairs do not resolve) + the LLD §17 criteria — **before** any fix cites it |

**Done when:** all 18 test-fixture transcripts parse; a 90-minute transcript is not silently
truncated; an unsupported file is refused in one line at the door.
*A6 measured: today 1 of 6 scenes gets a `source_chunk` on prose; after, 6 of 6.*

### Wave 1 — a gate that means something · the blocker

| item | what |
|---|---|
| A1 | grounding reads `narration` — the field the viewer hears |
| A2 | entity + temporal grounding on narration, and non-decreasing date order. **Reject, never repair** |
| A17 | **`--audio-dir`** — caller-supplied per-scene audio, exactly `clip_count(N)` files, **copied** into the work dir (the normaliser is destructive in place) |
| A19 | **audio-contract gate** — per-clip ffprobe (count, duration, codec) + ebur128 vs target, the 20/90-word band re-expressed in **seconds**, **and a caption gate that fails loudly** rather than silently writing no `.vtt` |
| A24 | `needs_user_input` — the LLM declares a gap instead of filling it |
| A28 | **prompt + model provenance in the plan** — `llm.model` and a prompt fingerprint |
| A20 | delete or rename `source_refs` (model-authored, **wrong in 2/8 scenes**) |
| A7, A8 | coverage publishes **the population it was counted over**; the count becomes a list with reasons |

**Done when:** a fabricated date and a fabricated command are both **rejected**,
with a test that feeds each as a wrong input first. *Measured today: a fabricated
`1998` and a fabricated `Congress` both return `grounding: clean,
render-blocking: clean`.*

### Wave 2 — publishable output

| item | what |
|---|---|
| A3 | three on-screen leaks: the literal word `opening`; `BRAND_NAME = PACKAGE_NAME`; the positional eyebrow enum |
| A21 | the media box — one reserved rect per scene taking a still, a clip, or a file tree |
| A27 | asset-existence gate |
| A32 | bind `code_snippet` to its source span; a deleted command becomes blocking, not a count |
| A34 | `graphic-reviewer` reads frames from the MP4 via `ffmpeg`, not the PPTX via `soffice` — 4.6× and the correct medium |
| A40 | prompt-injection tests against a measured raw-concat path — a malicious fixture proves the gate, not a benign one |
| A35 | unconditional `*.verify.json`; run L1 gates first so a bad build aborts before visual review |
| A36 | `--skip-deck` — stop paying for a PPTX the video lane does not need |
| A33 | **source allow-list** — a build from an excluded path fails loudly; `--test-fixture` stamps the plan non-publishable (`FR-028`) |
| A29 | make `_BANNED_EXAMPLE` extraction fail loudly instead of silently disabling itself |
| A23 | screen-capture secret hygiene — no keys, usernames, home paths in frame |
| A22 | commands as verified source data, never model output |
| A4 | chapters artifact (`0:00 Title`, **0.00 in** of body budget) |
| A12 | disclosure line for a partial cut — 4.880 in of an 8.50 in footer, free |

**Done when:** a real frame plus one text element makes a **legible 210px
thumbnail** (measured: 7.4px cap, 21.5:1 — the current composition gives 2.6px);
no JSON key and no package name on any frame; a scene referencing a missing asset
fails loudly.

### Wave 3 — iteration

| item | what |
|---|---|
| **A13** | **per-scene artifacts + regeneration** — the highest-value unbuilt item; three inputs reached it independently |
| A26 | `caption_text` as a third explicit channel, not derived |
| A14 | treat document text as untrusted data, never instructions |

**Done when:** scene 4 can be re-rendered without touching scenes 1–3, and the
whole-plan repair chain has a per-scene address.

| A25 | **demo-first ordering** — the user records, then the LLM plans around what exists. This is the default workflow, and it is what makes A22 structural rather than advisory |

> **Promoted into Wave 1.** Open decision 2 was answered *yes* — narration is the
> user's own voice — so A17 and A19 are no longer an optional wave. Wave 3b is
> removed.

### Wave 4 — the channel

`corpus manifest` → `video manifest row` → `channel index`, plus `claim_id` and
`source_segment_ids[]`. **The load-bearing field is `source_segment_ids[]`** —
without it there is no edge from a video to the corpus, and cross-part overlap is
undetectable.

**Done when:** "which source material has no video yet" is a **query**, not a
claim a build writes about itself.

### Wave 5 — the seam · *only after a second lane is proven*

`TopicProfile` (A9/A10), the adapter interface, audience profiles, vertical MP4.
Defer all of it. `narration.py` and `voice.py` need **zero** changes for any of
it, which is the proof that this is configuration and not a rewrite.

## 8. What we refuse to build, and why

| refused | the number |
|---|---|
| cinematic / text-to-video | $5,071 for 65 videos at Gen-4.5 rates, and it would replace the information layer with decoration |
| local video generation | 4.8 GiB total, 1.9 free, no GPU — not slow, **impossible** |
| song / lyric | **forbidden outright.** 78 of 87 chorus sentences deleted; the deleting pass has no `protected` parameter; no external-audio path |
| 9:16 / Shorts | usable width −46.7% against body budget **+112%** — a second layout, and the deck half is unnecessary |
| audiences 3–6 and 70+ | the 20-word floor forces a ≥11.19 s scene, so 240 s admits at most 15. **8 of 12 band × rhythm combinations are infeasible** |
| a 4-minute hard cap | would reject three builds the engine itself calls `OK` inside its own 220.8–276.0 s zone |
| scoring / ranking for selection | 2 of 6 axes deterministic, neither carries weight, and no gate can check a self-rating |
| map-reduce front end | moves the ceiling one call instead of removing it; a median segment is 1,200 chars against a 12,000-char window |
| `python3` as an interpreter | cannot import the package; fails with a misleading `ModuleNotFoundError` |

## 9. Decisions — three taken, one open

**"What is a lane?"** It means only: *which kind of channel do the first videos
belong to.* One lane = one kind of content, done properly. The alternative is
building five content types at once, which is the documented scope-explosion trap
— and the measurement says four of the five are blocked anyway.

**Taken 2026-09-27:**

| # | decision | effect on the plan |
|---|---|---|
| 1 | **Duration is derived from the source** — neither a target nor a ceiling | D1/D2/D3/D11 closed permanently. `--minutes` becomes an optional cap, default off. §4 |
| 2 | **Narration is the user's own recorded male voice**, with a fixed channel intro | A17 + A19 promoted into **Wave 1**; the language blocker disappears; the intro becomes one reusable asset |
| 3 | **Lane = practical software tutorial, demo-first** — `uv` install, and a plain `.md` lesson taught as a teacher | §2, §3 |

**Still open — one:**

4. **1080p — decide after Wave 2.** Measured: +31% build time for a 1.5× linear
   legibility gain, and worth nothing until the type scale is fixed (one font size
   measures 97% of threshold for a 3-year-old and 37% for a 70-year-old).

**Later, not v1: a voice sample for TTS.** If the user supplies an audio sample to
train a voice, that is a *different* thing from supplying audio files, and it
carries its own questions — the model's licence, and whether a synthesised clone of
a real person's voice is acceptable on a monetised channel. Worth noting: the 522
existing transcript timestamps are recordings of *this* presenter, so the lecture
lane already has a real voice paired to real text.

## 10. Where everything is

| file | what |
|---|---|
| `docs/DOCS.md` | which documents we write, and the fifteen we refuse |
| `docs/DECISIONS.md` | the ledger: 6 inputs, 27 build items, adopted / already-true / rejected-with-the-number / undecided |
| `docs/DESIGN.md` | the design record, phases, and the per-type verdicts |
| `docs/SLIDE-DESIGN.md` | the slide-type proposal, assessed |
| `docs/scratch.md` | the retrospective, and the pattern behind the mistakes |
| `AGENTS.md` | the working rules, incl. **rule 8: a check only ever shown a true statement is untested** |
| `opencode.json` | six agents, scopes and evidence types repaired for this tree |
