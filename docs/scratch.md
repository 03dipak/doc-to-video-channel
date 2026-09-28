# Scratch — what we got wrong, and the pattern behind it

A retrospective on `doc-to-video-tutor` as of `a7d63e0`, written while scoping
the channel work in `docs/DESIGN.md`. It exists because the channel effort will
otherwise repeat every mistake below, and because two of them are the reason the
engine cannot be pointed at a paying audience yet.

Ranked by consequence, not by how long ago they happened. Every claim carries its
evidence; several were found in this session and were not previously known.

---

## 1. The one that matters: the gates were never asked what they would do when wrong

`_grounding_issues` (`plan.py:870`) is bag-of-ngrams against the whole document
and **does not read `narration`** — the field the viewer hears. It reads `title`,
`bullets`, `takeaways`, `visual_diagram`, `code_snippet`. It fires only at *zero*
lexical overlap, so two recycled long words launder an invented claim. And **no
function in `guard_plan` or `_render_blocking_problems` reads scene order.**

Measured, injecting one falsehood at a time into a real non-technical plan:

| injected | result |
|---|---|
| "Prior authorization was invented by **Congress in 1998**…" → `scenes[0].narration` | `grounding: clean`, `render-blocking: clean` |
| the same sentence → `scenes[0].bullets` | `grounding: clean` — bigram `prior authorization` hits |
| `scenes[1]` ↔ `scenes[2]` **swapped** | identical verdict |

`1998` and `Congress` appear nowhere in the source.

**There is an entire gate suite — 315 tests, a hard pre-render gate, a pre-audio
gate, a coverage gate, a repeat gate — and not one of them had ever been handed a
lie.** Every one was validated by feeding it *correct* content and confirming it
passed. The suite measures "does this look like what we produce", never "would
this catch what we must not produce". A gate that has only ever been shown a true
statement is an untested gate.

**The fix in one line of practice:** for every gate, write the *wrong* input
first and confirm it fails, before writing the right input and confirming it
passes. A gate with no adversarial test is a gate that reports on style.

---

## 2. Measurement and provenance

### 2.1 Citations rot, and I rot them faster by writing them in bulk

In one documentation pass I wrote ~40 new citations. A reviewer resolved 31 of
the code anchors mechanically: **28 exact**. Its full tally was **12 wrong or
stale citations in that one pass**, of which four were code anchors —
`__init__.py:20` → 21, `pptx.py:280-289` → 299-305, `plan.py:1941` → 2397,
`video.py:786` → 815 — and the rest were a wrong line count
(`quality_review-history.md` claimed 2296, is 2313), a wrong section number, and
three text errors where I paraphrased a literal as a quotation.

`docs/CALL-FLOW.md` is the standing proof of the class: it presents itself as the
file:line reference and has **0 of 21** symbol anchors resolving, median drift
−813 lines, `plan_lesson` off by 558. It has been wrong for most of its life and
nobody noticed, because nobody was citing it to check anything.

**Rules now in force, from having broken all of them:**
- Name a **symbol**; a line number is a search hint with a shelf life.
- When several anchors go in at once, resolve **all** of them, not a sample.
- Never cite a line you have not opened in this session.

### 2.2 A count published without its denominator is a lie that reads as a pass

`verify.json` on the shipped build publishes `source_sections: 12`,
`unclaimed_source_sections: 0`, `verdict: PASS`. A reviewer computes 12/12 and
concludes 100% coverage.

Both halves are true and together they mean nothing. `source_sections` n=12 is
*title + 3 framing sections + concepts 1–8*. `concepts_total` n=12 is *concepts
1–12*. **Two different 12s.** `unclaimed: 0` is arithmetically true over a
denominator of 8, and is 0 because 4 sections were made *ineligible by a heading
regex*, not because they were taught. Three agents found this independently; the
field is pinned by a test — the test pins it to the function, so the field cannot
drift from its own meaning while still being false about the document.

### 2.3 37% of the only document we have ever ingested was never read, silently

`util.load_documents(max_chars=12000)` (`util.py:138`) — a default argument with
no CLI flag, over a join capped at `max_chars * 4`. On
`modules/08_concepts_mod03_gates.md`: `chars_read 11345 / chars_total 18019`.
Concepts 9–12 begin at char 11,310 and beyond, so they appear in **no**
`source_sections` entry and **no gate can report them unclaimed**.

The cut *is* recorded — `source_read.doc_truncated` — and that field is read by
**no other module**. It is printed once to stdout. This is a founding defect, not
a recent one, and it was documented nowhere until this session
(`LLD-narration-voice.md` §10.6, now written).

`chars_read` (11,345) is not `read_window` (12,000): the cut landed on a section
boundary just past concept 8. **A limit is not a reading**, and nothing recorded
which one this was.

### 2.4 `source_refs` is model-authored, so it is not provenance

Scenes 1–2 of the shipped plan cite `doc/task/03_regression_gates.md` — a file
that was never read. `source_files` holds the real path. No gate reconciles them.
Meanwhile `chunk_digest` and `section_digest` *are* real and verified — so the
provenance substrate is good and one field in front of it is fiction.

### 2.5 Twenty measurements that were true once and were never re-measured

`docs/quality_review.md` carried 20 banners claiming "213–228 tests pass". The
collected count was **315**. Nobody noticed for the life of the file, because a
plausible number in a document is indistinguishable from a true one.

The standing rule — *a configured value is not a reading* — was written after
this same class of error (a build printed `config.py` constants under a
`loudness :` label) and then violated twenty times in the documentation.

---

## 3. The contract

### 3.1 `design_decision` has three jobs and no gate

It is required by `STUDIO_PROMPT` as MANDATORY. `validate.py` **never reads it**
(zero hits). It is simultaneously the narration spine (`narration.py:549` rebuilds
thin narration as `opener + dd lead + bullet`), 58–68pt of reserved slide
(`pptx.py:444`), and framed by seven `dd_leads` that all say *reason / design
choice*. It is also a **software-review term** — "X not Y because Z" — with no
meaning in a history or biology lesson, where it silently fills 0 cards.

A field that is load-bearing, unenforced, and misnamed for its own domain.

### 3.2 `section` is a validation enum, rendered chrome, and a fallback generator

That triple duty is why a forest-growth video labels a scene `EXAMPLE`:
`_infer_section` (`plan.py:818`) falls back to `spread[(idx-2)%4]`, pure scene
position. One field doing three unrelated jobs cannot be fixed by editing the
vocabulary, and no prompt change reaches it because it is enforced in a post-pass.

### 3.3 Two renderers, and every fix had to be made twice

`pptx.py` and `slides.py` are separate layout implementations of the same plan.
Four instances of a fix landing in one and missing the other: `_shorter_column`,
the `(cont. N)` marker, the diagram fit, the two-column takeaway layout. The
diagram clip survived because `_audit_layout` guarded the deck and **the video
path had no geometry audit at all** — the asymmetry was the defect.

`LLD §23.7` rules the deck becomes the single layout authority, staged. Stage 1
done. Stage 2 not started.

### 3.4 A file that cannot detect the defect class it exists for

`_unspoken_visual_claims` checked `status_badges` and `json_snippet` only. The
`design_decision` card is the largest thing a slide can claim without the
narration saying it, and was **structurally invisible** — which is why the one
live instance went unnoticed. Closed with a coverage-fraction test.

### 3.5 A detector that could not see its own defect class

The TTS residue regex matched `[{}[]_=]` and `\d+/\d+`. `±`, `·`, `≤`, `≥`, `≠`
and `\d+/\(` were all invisible — and `1/(n+1)` is digit-slash-paren, so the one
expression under discussion never matched either.

### 3.6 A check that cannot tell right from nonsense

`mhe-mix`'s pure-English gate returns the **identical verdict and the identical
reason string** on `"Let's understand what happened at Versailles in 1919"` and on
`"Blorptastic zibblewump frimble dromp quuxen frobnitz 1919 Versailles treaty"`:
`0 marker hit(s), < 3 required`. It counts 21 romanised Devanagari markers. It is
a 7B-contamination detector that got promoted to a language gate by proximity.

### 3.7 Dead code that reads as live

`NARRATION_WORDS_PROMPT_MIN/MAX` — zero references outside their own definition.
`_concept_groups`' n>12 branch — unreachable from the CLI, which already caps at
12; only a test reaches it. `_POINTER_KEYS_RE` matches one literal
`{schema_version, baseline_id, path}` and then writes a **hard-coded** payload, so
it is grounded by coincidence and is a wrong-artifact generator the moment the
regex is widened.

---

## 4. Mine, this session

Recorded because they are the mistakes I can still repeat, and one of them
invalidated a ruling I gave with confidence.

1. **I generalised about a class of input before I had the input.** I ruled
   *"timestamps are inapplicable — there is no ASR, and the evidence layer is
   already built under other names"*, reasoning from an LLD. The actual corpus is
   timestamped, titled transcripts, and the `segment_id` / `start_time` layer
   both external reviewers asked for is **free from the source format**. The
   ruling was wrong, and confidently so.
2. **I answered an unstated corpus question with a stated one.** Before seeing
   the transcripts I said *"a series is not needed — all 12 concepts is 6.5
   minutes, one video."* The real corpus is 18 documents and 426,596 words. The
   entire 4-minute-versus-full-coverage debate was conducted against a corpus
   nobody had shown me.
3. **A doc flagged its own change as pre-existing.** I wrote an entry stating the
   LLD had "no disposition" for §20.2 #8 — in the same pass where my LLD edit
   gave it one. A document that tracks another document must be re-read after
   editing that document.
4. **A forward reference to a section that did not exist.** I wrote "see §10.6"
   into the LLD configuration table and never wrote §10.6. (Now written.)
5. **An edit destroyed a path in `opencode.json`** — it ate `docs/archive/LLD`
   and joined two scope entries. Caught by the reviewer. Edits to JSON-as-text
   need a parse check in the same command.
6. **A roadmap item repeated a stale "start here tomorrow"** because I checked
   whether sections were *marked* done rather than whether the work *was* done.
   `todolist.md` still heads Stage 4 "ALL CLOSED" while two of its own
   subsections are open. Header now corrected.
7. **I cited my own measurements as if they were the code's.** Fixing the test
   baseline required knowing the difference between "315 collected" and "315
   passed", and between a config constant and a reading — a distinction this
   project has been burned by twice already.

---

## 5. The pattern

Almost every item above is one sentence:

> **A check that was never asked what it would do when it was wrong.**

It shows up as: gates validated only on correct input (§1); a coverage number
validated only for self-consistency, not against the document (§2.2); a detector
that could not see its own defect class (§3.5); a language gate that could not
tell English from gibberish (§3.6); a field rendered as chrome from a validation
enum with no fallback other than scene position (§3.2); a provenance field nobody
reconciles with the file that was actually read (§2.4); and a doc whose twenty
test counts nobody ever re-measured (§2.5).

The second pattern, underneath it:

> **Anything that is true once and stored is a claim, not a measurement.**

Line numbers, test counts, coverage percentages, the 61% under-fill figure, the
"134 runs" and "0 findings at 150/100 DPI" in the doc I wrote today — all were
true when written, and the reviewer could not verify two of them from any source.
A stored number without a way to re-derive it is a rumour.

**What follows, as practice:**

1. Every gate gets an adversarial test before a happy-path test.
2. Every published count ships with the population it was counted over.
3. Name symbols, not lines. Resolve all citations in a batch, not a sample.
4. A number in a document is re-derived or it is deleted.
5. When a check cannot distinguish right from wrong, it is not a check — prove
   that with one example of each, in the same test.

Item 5 is the one that would have caught §1, §3.5 and §3.6 in a single sitting.
