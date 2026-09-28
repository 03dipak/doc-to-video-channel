# Input under evaluation — slide-type and visual-design proposal

**Status: an input on the table, not a decision.** Recorded 2026-09-27, before
any solution work, at the user's instruction. Nothing here has been built, and
§5 records a verdict per item rather than a plan.

The proposal argues: do not use one slide design everywhere; identify the content
type first, then choose the visual format; use **8–14 visual scenes** for a
4-minute educational video; it supplies a 12-type vocabulary, a topic→type table,
a design-system JSON, and a storyboard schema for the LLM to emit.

Two of its load-bearing numbers do not survive contact with the engine's own
arithmetic (§1), five of its twelve types do not exist in any form (§2), and two
of its recommendations conflict with a deliberate ruling or with the measured
constraint that gates reach (§3). One part of it independently corroborates
[`DESIGN.md`](DESIGN.md) §4.4 (§4).

---

## 1. "8–14 scenes for a 4-minute video" is not buildable at the top of that range

The engine's own `duration.word_budget(scenes, 240.0)` — called with the declared
4.0-minute target. `word_budget` returns `clips = scenes + 1` (the final Key
Takeaways clip is a clip), and `per_clip_min` is floored at
`NARRATION_WORDS_MIN_FAIL = 20`:

| scenes | clips | silence (s) | total words | per clip | against the enforced bands |
|---:|---:|---:|---:|---:|---|
| 8 | 9 | 37.0 | 343.3 | 34.3 | comfortable |
| 9 | 10 | 40.0 | 338.2 | 30.7 | comfortable |
| 10 | 11 | 43.0 | 333.0 | 27.8 | ok |
| **11** | 12 | 46.0 | 327.9 | **25.2** | **exactly at the 25-word WARN line** |
| 12 | 13 | 49.0 | 322.7 | 23.1 | **under WARN** |
| 13 | 14 | 52.0 | 317.6 | 21.2 | under WARN, 0.8 above the 20-word hard floor |
| **14** | 15 | 55.0 | 312.4 | **19.5** | **`feasible: 0` — below the 20-word hard floor** |

`word_budget` computes with `LOUDNESS_WPM = 103.0`. The **measured** rate is
107.276 wpm, so every per-clip figure above is ~4% optimistic; at the measured
rate 13 scenes is ~20.2 words/clip, i.e. on the floor rather than above it.

The cause is arithmetic, not editorial: every extra scene adds a **3.0 s
inter-scene pause** *and* divides the same fixed word budget. Silence at 14 scenes
is 55.0 s of a 240 s target — **23%**.

**So the top third of the recommended range is unreachable** without changing
something the engine treats as fixed: the pause default (a product decision, per
the engine's ledger §AA3) or the 20-word hard floor (a contract, per
`config.py:335`). At 4 minutes the buildable range is **8–11 scenes**, with 11
sitting exactly on the warn line.

For a channel this is mostly moot — per DESIGN.md §7 a segment produces a
2–3 minute video — but the proposal states its range *for a 4-minute video*, and
in that frame it is wrong.

---

## 2. Block by block: what the engine already has

Word-boundary counts across `schema.py` (scene field), `slides.py` (video
renderer) and `pptx.py` (deck renderer). A naive substring search reported 20
`graph` hits in `pptx.py`; all 20 were the word **"paragraph"**. A naive search
also reported `before`/`after` hits in `slides.py`; all were prose in comments
("before calling `_slide_variants`"). Both were disproved before reporting.

| # | proposed type | `schema.py` | `slides.py` | `pptx.py` | verdict |
|---:|---|---:|---:|---:|---|
| 1 | hook slide | 0 | 0 | 0 | **partial** — the cover card exists (`TITLE_HOLD` 4.0 s) but is the emptiest frame in the build: 7.1% body fill, 4.51 in of a 4.86 in budget unused |
| 2 | hero visual | 0 | 0 | 0 | **absent** — no image field, no asset pipeline, nothing |
| 3 | labeled diagram | 2¹ | 1 | 2 | **partial** — `visual_diagram` is `[A] ---> [B]`, a linear chain. No parts-and-labels form, and its "reveal each label as mentioned" is not a capability |
| 4 | step-by-step | 3 | 5 | 2 | **exists** — `steps` |
| 5 | before-and-after | 0 | 0 | 0 | **absent** |
| 6 | comparison | 0 | 5 | 8 | **partial** — `value_table` is a 2-column string table, and `_boundary_rows` **rejects** any pair without a decimal or unit: `7.0%` is accepted, `1200 men` and `1815` are not |
| 7 | process / flow | 3 | 7 | 2 | **exists** — `flow`. Note: `flow` and `visual_diagram` are one grammar with two renderers, and only one is validated |
| 8 | timeline | 0 | 0 | 0 | **absent** — DESIGN.md §4.4 shape 1. Nothing renders a date axis |
| 9 | data visualization | 0 | 0 | 0 | **absent** — `value_table` and `status_badges` are the only numeric blocks and neither is a chart |
| 10 | concept analogy | 2 | 5 | 6 | **exists** — `analogy` |
| 11 | myth-versus-fact | 0 | 0 | 0 | **absent, but it is a relabel** — MYTH/FACT is the same shape as `design_decision` ("X not Y because Z"). That field exists, is unenforced (`validate.py` never reads it), and filled **0 cards** on a narrative source |
| 12 | summary / takeaway | 0 | 6 | 11 | **exists** — `takeaways`, two columns, `(cont. N)` |

¹ `schema.py` count for `visual_diagram` is the field declaration.

**Six exist, one is a relabel of an existing field, five have zero presence in
the schema, the video renderer and the deck renderer.**

The five absent ones are also the five that need work in **both** renderers —
which is the failure mode the engine's ledger §A records four times.

---

## 3. Two conflicts

### 3.1 The design-system JSON fights a deliberate palette rule and the measured thumbnail constraint

The proposal's JSON specifies `background_color #F7F9FC` (near-white),
`text_color #172033`, `heading_size 42`, `body_size 26`, `max_bullets 4`, plus
per-topic themes ("Forests: green, brown"; "Cars: dark blue, electric cyan").

**The palette is semantically constrained, on purpose.** `config.py:322-323`:

```
GREEN = (76, 175, 80)
RED   = (234, 67, 53)  # FAIL semantics only; see LLD B2.2 exception
```

The contract reserves red for FAIL semantics, never for body text, and never
paired with green so no red-on-green contrast pair can occur. A forest theme
repurposing green, or a before/after slide using red for "bad", collides with a
documented accessibility rule rather than merely restyling.

**The sizes fight the constraint that gates reach.** Measured: at YouTube's
~210 px display width the current 23 px title is a **4 px** smear and body text
has **zero** surviving pixels. The measured fix is a title **2.1×** larger, one
line, ≤4 words, centred in the top 45%, with the eyebrow and body **deleted** —
0.4× and 0.35× cannot be shrunk to survive 210 px. The proposal adds element
types, per-topic themes and animation, and specifies a *smaller* body size
(26 pt on a 13.33 in slide ≈ 17 px at 960×540). It optimises for a different
artifact than the one that decides whether anyone clicks.

**Not a rejection of theming** — a rejection of theming *before* the thumbnail
exists, and of a near-white inversion of a dark theme whose contrast was
deliberately chosen.

### 3.2 "The LLM should choose the slide type" — half adopt, half refuse

The proposal's closing principle: *"the LLM should choose the slide type based
on the information structure"*.

The engine has a ruling pointing the other way, and it is a good one:
`_ensure_technical_visuals` exists precisely "so they can never invent a fact the
way a model-written 'worked example' would" (`plan.py:709-711`), and
`_render_blocking_problems` is *"Deterministic only (no LLM)"* by contract
(`validate.py:412`).

**Ruling: template selection is safe to delegate; content is not.** Choosing
among a *closed set* of layouts is a layout decision, not a factual claim, so it
can be model-chosen. The strings and numbers that fill the chosen layout must
remain deterministically grounded — that is the line the existing ruling
protects, and it is unaffected.

This dovetails with `TopicProfile` (DESIGN.md §4.1): the profile supplies the
**allowed set** of types per topic family, and the LLM picks within it. The
proposal's instinct is right; its scope is one level too wide.

---

## 4. What corroborates DESIGN.md §4.4

`code-reviewer`, reading only the source, independently derived **five** content
shapes: timeline, time series, causality, decision ledger, mechanism. The
proposal's topic→type table maps onto the same five — cars/history → timeline,
forests → time series + cycle, business → comparison + data, technology →
process, plus a definition/analogy family for science.

Two unrelated methods, one answer. That raises confidence in the shape count,
and it means the **profile** in DESIGN.md §4.1 is the right seam rather than a
single generalised scene model.

One more useful finding: the proposal's 8-scene default and the engine's existing
`_SECTIONS` vocabulary **overlap by three**.

| proposal's 8 | engine's `_SECTIONS` |
|---|---|
| question hook | — (the cover card does this) |
| topic introduction | *what is this* |
| parts or concepts | — |
| how it works | *how does it work* |
| example | *example* |
| comparison or data | — |
| limitation or surprising fact | — |
| three-point takeaway | *takeaway* |
| — | *why do we need it* (no counterpart) |

So the eyebrow enum needs **three labels added and one removed**, and its
positional fallback (`spread[(idx-2)%4]`, `plan.py:818`) deleted — it is a
vocabulary extension, not a redesign. That is materially smaller than the
proposal implies.

---

## 5. Verdicts

**Also indexed in [`DECISIONS.md`](DECISIONS.md) §2 and §4, with the reasoning for the items that came from the other two inputs.** This section covers the slide-design proposal only.

| item | verdict |
|---|---|
| 8–14 scenes for 4 minutes | **reject as stated.** Buildable range is 8–11; 14 returns `feasible: 0` from the engine's own function. |
| Change the visual treatment every 10–25 s | **already exceeded.** The engine emits one reveal variant per bullet, so a 3-bullet scene is 4 frames — at 8–11 scenes and 240 s that is a change every 4–7 s. Correlates with the measured 28 s / 11% near-black runtime, so it is a symptom worth keeping, not a target. |
| Six existing types (steps, flow, analogy, takeaway, value_table, status_badges) | **adopt as-is** — no change, they are the vocabulary |
| `myth-versus-fact` | **adopt as a relabel** of `design_decision`; do **not** add a field |
| `labeled diagram` | **undecided** — `visual_diagram` is a linear chain, not parts-and-labels. Needs its own assessment, both renderers. |
| hero image, before/after, timeline, chart | **undecided, and blocked** on having a real narrative document and a thumbnail that exists. Do not start here (DESIGN.md §5 phase ordering). |
| near-white background, per-topic palettes | **reject for now** — collides with the documented red/green semantics rule; defer to after the thumbnail problem is solved |
| `body_size 26`, `max_bullets 4` | **reject** — moves away from the measured 2.1×-title direction |
| LLM chooses `slide_type` | **adopt, narrowed** — within a profile's allowed set; never the content |
| storyboard JSON (`scene_id`, `slide_type`, `duration_seconds`, `source_segments`) | **adopt the shape.** `slide_type` and `source_segments` map onto DESIGN.md §3 and §5's `source_segment_ids[]`. `duration_seconds` is **suspect** — it invites the model to assert a duration, and this project's §1 blocker is exactly that kind of unverified assertion. Prefer a measured or derived value. |
| `SLIDE_TEMPLATES` dispatch dict | **adopt in principle.** Note the engine already has a per-shape dispatch problem: `visual_pattern` dispatch is an open, unstarted item in the engine's own backlog. |

---

## 6. What is not decided here

- No block is added, renamed or removed by this document.
- The `narrative` profile's `scene_labels` is still unspecified; §4 narrows it to
  "three additions, one deletion" but does not name them.
- Whether a thumbnail template is a new renderer or a variant of the cover card
  is open, and depends on a design decision nobody has made yet.
- The one real document the project is blocked on is still missing
  (DESIGN.md § *Open decisions*).
