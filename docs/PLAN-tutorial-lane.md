# PLAN — the tutorial lane

Written 2026-09-28. Companion to [`PLAN.md`](PLAN.md), which stays the whole-project
plan. This file is the **lane-specific build order** and exists for one reason
recorded below: **`PLAN.md` §7 Wave 1 is scoped to a lane we are not building first.**

**Every number here was re-derived on 2026-09-28.** Basis is marked per
`DOCS.md` rule 2. Symbols, not lines, per rule 3.

---

## 1. Why this file exists

`PLAN.md` §2 chose the tutorial lane, and `DECISIONS.md` §12 ruled it is *"the
one lane that can start **today**"*. But `PLAN.md` §7 Wave 1 is *"the blocker"* —
and the blocker it names is not this lane's blocker.

`DESIGN.md` §1 settles the narration gate (**A1/A2**: entity + temporal grounding
on `scenes[*].narration`, non-decreasing date order) as unnecessary for a domain
pipeline, on the stated reason that *"an LLD's scenes are unordered capabilities,
and swapping two gate definitions is not a wrong video."*

That reason is the **LLD** lane, not ours. A `uv install` video's scenes are
strictly ordered: install → verify → first project. So we surveyed the two lanes'
truth risks and they are **disjoint**:

| failure | narrative lane | **tutorial lane (ours)** |
|---|---|---|
| fabricated **date** (`1998`, `BCE`) | fatal — the dates *are* the value | **unreachable** — no dates in a tool tutorial |
| fabricated **command / flag** | moderate | **fatal** — the commands *are* the video |

**Ruling: the tutorial lane's Wave 1 blocker is command provenance
(`A22` / `A32` / `FR-016`), not date grounding (`A1` / `A2`).**

`A1`/`A2` is **deferred, not dropped** — it is still required before any
narrative or history lane. It is recorded here so its absence from Wave 1 is a
decision with a date on it, not an oversight. `PLAN.md` §7 Wave 1 keeps both;
this file sequences them.

---

## 2. Source of truth for the content — ruled

**RULING (2026-09-28): the publishable source is the owner's own notes and
verified commands.** `RIGHTS.md` §0 *What replaces it* already reached this
conclusion for the project; this file adopts it for the first video.

Consequences, each of which is a *simplification*:

- No clearance, no attribution, no licence research (`RIGHTS.md` §0).
- `RIGHTS.md` §0's 18 course transcripts stay **excluded from publication** and
  remain a **local parser fixture only**. `FR-028` makes the build enforce it.
- The 3–6 screen recordings are the owner's own screen — the cleanest rights
  position in the project (`DECISIONS.md` §12).

We explicitly rejected grounding the first video on uv's official documentation:
it is not present on this machine (measured: 0 local copies), it adds a
source-drift surface — the docs change under a published video — and it makes an
attribution decision necessary that the own-notes route does not.

---

## 3. Video #1 — the topic, and why it is the right one

**Topic: a practical session — install `uv` on the system, verify it, create a
first project.**

Chosen because it is the only topic that satisfies the whole lane table in
`PLAN.md` §2 at once, and the docs had already argued for it three times:

| requirement | why `uv install` clears it |
|---|---|
| source document | the owner's notes; commands are run and captured by him |
| AI video generation | **none** — real screen recording |
| external content licence | **none** — his own screen and voice (`RIGHTS.md` §0) |
| GPU | **none** |

`DECISIONS.md` §12: *"It is self-demonstrating: the tool teaches the tool."* This
project is `uv`-managed end to end, so the toolchain shown in the video is the
same toolchain that produced the video.

**The environment is already real and checkable** (measured 2026-09-28), which is
precisely what `A22` requires — commands as verified source data, never model
output:

```
uv      0.12.2 (x86_64-unknown-linux-gnu)
python  3.12.13
ffmpeg  8.0.1-3ubuntu2
```

---

## 4. Build order

Four phases. Each has a done-when that is a reading, not a configuration.

### Phase 0 — make the project runnable

*Nothing below can be verified until this is done.*

| item | what | why |
|---|---|---|
| **P0-a** | make the entry point real: accept `argv`, print usage | `main()` **exists** and runs today (measured — `doc-to-video-channel --help` exits 0), but it **ignores `argv`**, so `--help` prints a greeting instead of usage. v001 of the LLD called this "broken"; it is unfinished, not broken. |
| **P0-b** | add the four missing `[tool.*]` blocks: `tool.ruff`, `tool.mypy`, `tool.pytest.ini_options`, `tool.coverage.run` | all four are **absent** (measured). Six dev tools are installed and none configured: `ruff check .` reported `All checks passed!` and `pytest --co` reported `no tests collected` over a 66-byte file. That is a green gate over nothing — the failure class `docs/scratch.md` §1 records. |
| **P0-c** | ~~path-depend on the engine~~ **CANCELLED 2026-09-28** — the owner ruled the baseline is a *reference only*. Nothing here imports, installs or pins `doc-to-video-tutor`; `uv.lock` holds **0** references to it. The pipeline is vendored into this package instead, which is what makes §4's seam reachable at all. |
| **P0-d** | **one** build entry point in this package, taking `argv` | the baseline keeps a second, deprecated console-script shim. Since nothing here invokes a console script by name, that second path **does not exist** in the channel — which is the outcome, and it is reached by construction rather than by a convention the baseline's own comment shows has already failed once. |

### Phase 1 — the seam

`DESIGN.md` §4.1 calls `TopicProfile` *"the load-bearing evidence for this whole
record"* and says it *"plugs at `plan_lesson`"*. **Measured: `TopicProfile`,
`topic_profile`, `scene_labels`, `decision_prompt_rule` and `source_shape` return
0 occurrences across the baseline's `src/`.** The seam does not exist yet; §4.1
describes it as though it does. That claim is corrected in
[`LLD-tutorial-lane.md`](LLD-tutorial-lane.md) §2, and the seam is specified there
in §4.

**Revised after review: this is 250–350 lines of source plus two fixtures, not a
39-site sweep.** The 39 is a grep hit count over five names, and
`LLD-tutorial-lane.md` §2 **deliberately does not decompose it** — every split
attempted (16, 18, 19, 26) disagreed on re-measurement, so only the total is
published, with the command that produces it. What *is* solid is the other
direction: **at least six behaviour-carrying sites lie outside those 39** that no
constant-sweep can find, including a taxonomy re-stated inside a prompt string and
the two `reject_non_latin_*` validators. The class is **open**, so the acceptance
criterion is a **behavioural differential**, not a site count.

| item | what |
|---|---|
| **P1-a** | `TopicProfile` with **five** fields: `section_policy`, `scene_counts`, `enrichments`, `script_policy`, `voice`. Not the six `DESIGN.md` §4.1 names — `decision_prompt_rule` is **deleted**, its stated default being a `NarrationVoice` field with no referent of its own |
| **P1-b** | absorb every read of the five named constants **and reach the six prose/validator sites outside them** — which means parameterising `_planner_prompt` / `NARRATION_PROMPT` and teaching both `reject_non_latin_*` validators to read a context, since neither takes one today. **This is the bulk of the work** |
| **P1-c** | the ingestion adapter — `AdapterResult` **carries** the copy's existing `LoadedSource` (5 dataclass fields plus 1 `@property`) rather than re-declaring them, and adds only `concepts`, `concepts_total`, `concepts_in_window`, `topics`, `source_files`. The access path matters: the spec's `content` is reached as `result.source.text` |
| **P1-d** | add the hook `LLD-tutorial-lane.md` §7 needs: `plan["_extra_gates"]` in `plan.py` — a file in this package, so no upstream coordination — invoked beside `_render_blocking_problems` at **all four** call sites |
| **P1-e** | **check both reachable renderers** on every change: `slides.py` (758 lines) and `pptx.py` (1,022) — measured. `create_video` / `_make_slide_image` are **excluded**: 0 callers, so asserting against them would be asserting against dead code |
| **P1-f** | **the two `LLD-tutorial-lane.md` §12 fixtures**: a canned plan payload and a source document, so `plan_lesson` can run without the 7B endpoint. A reviewer built and ran this in **~25 lines, under a second** — two fixtures, not a subsystem. **Gated on §5.6**: it must also produce a *passing* plan, and the unstable-stub falsifier must then fail. Without that, the differential measures the repair path, not the success path |
*Done when:* a defaults-only profile reproduces today's normalised `plan.json`,
every renderer's output and `*.verify.json` — and a profile with one deliberately
wrong value produces a **different** plan, which is what proves the differential
measures something.

### Phase 2 — the front door

**`A5` (the `.docx` reader) leaves Wave 0.** `DECISIONS.md`'s `A33` row states the
owner's notes are Markdown, which `load_documents` already reads; and measured,
`A5` is one dispatch arm, not a parser — `.pptx` goes to `_load_pptx` and
everything else to `read_text(utf-8)`, and **`python-docx>=1.2.0` is already a
declared dependency of **this package** imported nowhere**. A phase spent on a parser this lane
never exercises is `AGENTS.md`'s stored-numbers failure in costume.

Wave 0 keeps two items, both on the path to video #1:

**`A15` hard format gate** at the door, before any LLM call — an unsupported file
is refused in one line instead of becoming a traceback. **`A6` paragraph-boundary
fallback** in `_markdown_sections` — **~12 lines, the best value in the record**,
and *required for this lane* because the input is prose notes with no headings
(1 of 6 scenes gets a `source_chunk` today; 6 of 6 after — restated from
`DESIGN.md` §4.3).

*Done when:* an unsupported file is refused in one line at the door, before any
LLM call, and a prose source yields a `source_chunk` on **6 of 6** scenes.

**`A5`'s done-when is deferred, not written, and its population was wrong first.**
Three numbers were in play: FR-001's **18** (one directory), this machine's **30**
file paths, and video #1's **0**. Measured 2026-09-28, those 30 paths resolve to
**18 unique documents** by md5 — six files are byte-identical copies in two
*sibling* repositories — so "30" was 18 checks run 30 times. The rulings are in
`LLD-tutorial-lane.md` §14.4 (wire the parser, do not announce the format) and
§14.6 (adopt the 18-document corpus, canonical root
`rag-apidriven-pipeline/data/transcripts/`). The done-when is deferred to the time
it is needed, when it will name the population then.

**The denominator, for the record (measured 2026-09-28).** `RIGHTS.md` §0 and
`PLAN.md` §7 both say **18** transcripts. The 18 is a *true count of a true
population* — `rag-apidriven-pipeline/data/transcripts` — but it is not the
population a parser meets:

```
18  rag-apidriven-pipeline/data/transcripts
 6  rag-pipeline-testing/data/transcripts
 6  rag-eval-framework/data/transcripts
30  total; all 30 open under python-docx, 0 failures
```

**This is now a deferred measurement, not a done-when.** v001 of this file
concluded "`A5`'s done-when should read **30**". That was wrong in the same way:
correcting 18 to 30 makes the document more accurate and equally useless, because
this lane parses **0** `.docx` files on the way to video #1. The 30 is recorded so
the next person does not re-derive it, and the done-when is deferred to
`LLD-tutorial-lane.md` §14.4 and §14.6, where the rulings and their measurements
now live.

### Phase 3 — the gate that means something (rescoped Wave 1)

`A22` **and** `A32` command provenance — three requirements, not one: the
`claim_id` record, binding the command to its admitted source span, and making a
*deleted* command blocking rather than a count. Plus `A17` `--audio-dir`, and
**`A18`** (not `A19` — that is a picture-box compositing path) audio-contract gate
**and** a caption gate that fails loudly.

*Done when:* **a fabricated command is rejected**, and it is rejected by a test
that fed the fabricated command in first.

*Measured today:* `claim_id` returns 0 occurrences across the baseline's `src/`
**and** `tests/`. There is a deterministic gate at the plan stage, but
`claim_id`, `verification_status`, `verified_command` and `shell_cmd` are all
unimplemented. The renderer labels the panel `COMMAND CONTEXT` while the schema
field is `code_snippet` — a vocabulary mismatch, which is how `DOCS.md` §5 records
a grep closing a check that had been reported open.

**The gate needs a hook that does not exist.** Pre-render lives in
`cli.main` calling `validate._render_blocking_problems`. A channel-side gate is
unreachable without a change to `plan.py` — a file in this package — so **P1-d** carries it. A `provenance.py` +
`gates.py` split is also dropped: they are one concern, and `validate.py` keeps
record and check together in `validate.py`.

`A17` is also unimplemented: `--audio-dir` returns **0** occurrences. The copy's
`video.py` and `cli.py` each compute an `audio_dir`, but that is an **output**
staging directory — the caller-supplied input flag does not exist. Do not read
those two hits as A17 being done.

### Phase 4 — the first video

1. Owner writes the notes and **runs every command**, capturing 3–6 clips.
2. Record per-scene narration, **one WAV per scene** — never one long file
   (`PLAN.md` §4).
3. Build → gates → MP4 + captions + storyboard + quality report.
4. Settle the four pre-publication items in writing (`DECISIONS.md` §9.7) before
   anything ships.

*Done when:* `REQUIREMENTS.md` §4's seven release-gate items are all true, and
the rights attestation in `RIGHTS.md` §0 is written.

**Two of the four pre-publication items dissolve under `recorded_voice`, two do
not.** TTS endpoint terms (`DECISIONS.md` §9.7 item 1) and LLM-output narration
rights (item 4) are about *synthesised* speech we are not producing in v1. The
**DejaVu glyph redistribution** (item 2) and **`BRAND_NAME = PACKAGE_NAME` in
every published frame** (item 3, fixed by `A3`) are about the render itself and
apply to every video regardless of narration mode.

---

## 5. New dependencies

**None.** The remaining work is code, not packages.

The dev group was reduced to the six that have a consumer in this project's own
design — `hypothesis` is a **Phase 3** tool, justified by two properties this
project's docs already name (`PLAN.md` §4's duration formula, and NFR-009's
`abs(sum(parts) − total) < 1.0`). `pyright`, the four notebook packages,
`pytest-asyncio` and `pytest-mock` were removed. The grounds, stated so they can
be re-checked: **0** occurrences of `async` / `await` / `concurren` in the channel
doc tree **excluding this paragraph**, and no notebook workflow anywhere in
`docs/` outside the sentences that say so. Both counts are self-referential
and are flagged as such rather than quoted as clean.

A previous draft of this file claimed "0 notebook mentions in `docs/`" and "0
occurrences of `async`" while the sentence making both claims was itself one of
the matches. `grep -riow notebook docs/` returns **8** occurrences across the two
tutorial-lane files. On `.ipynb`: **0** in this project and in the baseline, but
**78 elsewhere under `/home/dipak`**, so "zero on this machine" was never true and
is not claimed.

---

## 6. Honest limits of this plan

- **`RISKS.md` R-18 is untouched by this plan.** No document and no local
  measurement can say whether viewers will watch. Until publication, every reach
  assumption is a **bet**. `DECISIONS.md` §12 and `RISKS.md` R-18 both answer the
  same way: *a small published pilot, not a larger unbuilt one.*
- **`A1` / `A2` are deferred, not proven unnecessary.** The argument in §1 rests
  on this lane's content shape. A lane that teaches dated history needs it back.
- **No timeline is given.** This plan orders work; it does not estimate it.
