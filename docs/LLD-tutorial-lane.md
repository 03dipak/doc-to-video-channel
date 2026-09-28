# LLD — the tutorial-lane seam and its gates

Version: **v009** — six internal review rounds, then two external reviews, then a
seventh round run by four agents carrying an injected project-knowledge block.
Every round returned NOT GREEN. Every change and its reason is in §15, by round.
**Acceptance criteria 17 → 33; §12 rows 16 → 31.**
Status: **Not started** — `src/doc_to_video_channel/` is 1 file, 66 bytes
(measured 2026-09-28)
Scope: the `TopicProfile` seam, the ingestion adapter, the command-provenance
gate, and the front door. Build order and lane scoping are in
[`PLAN-tutorial-lane.md`](PLAN-tutorial-lane.md).

**On this document's existence.** [`DOCS.md`](DOCS.md) §3 assigns the LLD to the
*baseline* and §6 rules that *"Wave 0 is unblocked and needs no new document."*
That ruling is followed for everything it covers. This file is the **narrow
exception**, and it earns its place against `DOCS.md` §1's three-question test:
a change would falsify it; it is not derivable from `PLAN.md` §5; and Phase 1 and
Phase 3 read it. Its scope is correspondingly narrow — canvas, colour, type
scale, orchestration and the layout contract stay where `DOCS.md` §3 put them.

**On the numbers** (`DOCS.md` rule 2). Two bases, not interchangeable.
**Measured** — re-derived on this machine, 2026-09-28. **Restated** — quoted from
another document and *not* re-measured here: the 1-of-6 to 6-of-6 grounding
result (`DESIGN.md` §4.3), the 20/90-word seconds, the −22.3 LUFS clip, and the
55→0 caption collapse (`PLAN.md` §4).

---

## 1. Purpose

`doc-to-video-channel` produces narrated, source-traceable tutorial videos. It
contains **no pipeline of its own**. It is a thin package that supplies a domain
profile and a provenance gate to `doc-to-video-tutor`, which does the work.

`PLAN.md` §4's rule governs everything below: *"The LLM decides **what** to
explain. Code decides **whether** JSON is valid, whether text fits, whether
duration fits, whether assets exist, and whether commands are verified."*

---

## 2. Problem statement

v001 claimed the seam was a configuration change, citing `DESIGN.md` §4.1: the
baseline's domain assumptions are hard-wired in **39 places**, and
`narration.py` + `voice.py` (1,448 lines, measured) *"need **zero** changes."*

**Both halves of that were wrong, and the reviewers found it independently.**

**The count is a grep hit count over five names, and nothing finer.**
`grep -rEow 'AUTO_TRIM_MAX_SCENES|MIN_SCENES|TARGET_MAX_SCENES|_SECTIONS|_ENUM_HINTS' src/`
returns **exactly 39 occurrences** — *note the `-E`.* Without it `grep` BRE treats
each `\|` as a literal and the command returns **0**. That defect was published in
v001-v003 and survived three review rounds, because two reviewers verified the
**number** by per-name counting and never ran the **command**. It is the clearest
instance in this document of its own rule: a number a reader is told to reproduce
is only as good as the command printed beside it. (14 / 8 / 8 / 5 / 4, measured over `src/`
alone). It is **not** stable across `src/` and `tests/`: `tests/` contributes 8 more,
so a reader who widens the command gets 47 and should not call that a contradiction.

**This document deliberately does not decompose that 39 into definitions, imports,
reads and prose.** Three independent methods returned three different splits, and
per `DOCS.md` rule 2 a number that cannot be re-derived is deleted rather than
asserted. The split is not load-bearing; what is load-bearing is the next
paragraph.

**And the class is not closed — it is open.** Behaviour-carrying sites lie
*outside* those 39, and **no grep for a named constant can ever find them**:

| missed site | why no grep finds it | what it does |
|---|---|---|
| `_infer_section` (`plan.py`, function `_infer_section`) | a literal 4-tuple plus `return "What Is This?"` | a **second** copy of the section taxonomy, rotating on `(idx - 2) % len(spread)`, re-typed to title case against `_SECTIONS` |
| `config.STUDIO_PROMPT` | the five section names re-stated **inside a prompt string** | the taxonomy the model is *asked* for |
| `schema.SlideScene.reject_non_latin_slide_text`, `schema.LessonPlan.reject_non_latin_plan_text` | validators, not constants | the script policy, which `SlideScene` applies to a field set that **includes `section`** |
| `cli.main` | a bare literal `5` where `MIN_SCENES` belongs, and a printed *"5-scene floor … 6-scene drill"* message | a further hard-wired scene count, in code **and** in user-facing text |
| `_MAX_PATCH_SCENES` (`plan.py`, module constant, read once) | a **sixth** name, not in the original five | a scene-count cap that a sweep of the first five misses |
| `NARRATION_PROMPT` | the number **46** in a prose string | asserts a closing-recap word count that **no code computes** — the fabricated-value failure mode, relocated into a constant |

**Ten sites are currently unowned by §4**, listed here because the seam's
completeness is the whole point and a partial one is a silent partial: the on-screen
`"Key Takeaways"` label `slides.py` injects (a sixth taxonomy copy, and it is **not**
one of `_SECTIONS`); the printed message in `cli.main` that reads *"below the
5-scene floor - falling back to the classic 6-scene "* (verbatim, truncated in the
source, and user-facing); the **four** `import-time default-argument` bindings across
**three** functions —
`_concept_headers`, `_trim_scene_overflow` and `_overflow_audit`; `TUTOR_PROMPT`'s
`"5-8 sections"`; and `value_table` / `status_badges`, which write **keys no `SlideScene` field
declares** — and that is a *schema* defect, not an invisible-output one: measured,
`slides.py` draws `value_table` as a "NUMBERS" card and `pptx.py` draws it as a
table and `status_badges` as a "VERDICT CODES" chip row. **v008 said "the renderer
cannot draw", which is false**; the correct claim is that nothing in the schema can
address them, so no gate validates them.

**Two of the eight were discharged, and how matters more than how many.** The
count was ten. The baseline's `studio/__init__.py` re-exports are **not fixed by a
change; they disappear**, because §5.1 row 18 excludes that file rather than
deleting it (§14.7) — and that same exclusion discharges a **second** site, because
`TUTOR_PROMPT`'s `"5-8 sections"` lives in the *root* `__init__.py` that row 17
drops. Both are recorded as resolutions so they do not stay open forever against
files this package will never contain.

**Consequence, and it is the load-bearing one:** a symbol-counting probe is
**structurally blind to the class of defect this seam exists to prevent.** It
would report clean while the prompt asked for a taxonomy the profile does not own.
§3 goal 4 says a silent zero is a defect, not a pass — and a probe with the wrong
question manufactures silent zeros by construction. **§12 replaces it with three
checks that are not greps**, and v001's site-count criterion is deleted rather
than repaired.

**So the seam is not a 19-line change.** It is **250–350 lines of source, plus
two test fixtures** (§3 goal 1; §12 has the measurement): the function the
differential must exercise, `plan_lesson`, is
**never executed by the existing suite** — of 20 test references, 5 are
`inspect.getsource` string assertions and **0** are calls, and
`test_build_regressions.py` says so outright. Producing two plans to diff requires a way to run planning without the
7B endpoint, and that harness does not exist yet.

`DESIGN.md` §4.1 is right that this is *"a configuration problem wearing a
rewrite's clothing"* — but the clothing does not come off for free.

---

## 3. Design goals and non-goals

**Goals**

1. Two profiles, one vendored pipeline. **Estimated 250–350 lines of source, plus a replay
   two fixtures** (§12) — v001's
   "39 sites" understated this by more than an order of magnitude.
2. A command shown on screen is either verified against a recorded source span or
   the build is blocked. Never model output, never silently retained.
3. **Behaviour preservation, proven by differential rather than by a site count.**
   A profile whose defaults are today's behaviour must produce today's artifacts,
   byte for byte after normalisation.
4. Every gate fails **loudly**. A silent zero is a defect, not a pass.
5. No behaviour-carrying value may live in a place the profile cannot reach —
   including a prompt string and a validator. **Two values currently violate this
   and have no home in §4**: `NARRATION_PROMPT`'s **46**-word recap figure, and
   the 30/55-word band (`NARRATION_WORDS_PROMPT_MIN`/`MAX`). Neither is named in
   §2's unowned-site list, so goal 5 is false for them as the document stands. The
   band is **production-dead** — both constants are read only by a test — so the
   cheaper resolution is to delete them; the 46 needs a home or an explicit
   statement that the recap is not profile-varying.

**Non-goals**

- Not re-implementing planning, rendering, media assembly, or TTS.
- Not the `A1`/`A2` date-grounding gate. Deferred with reasons in
  `PLAN-tutorial-lane.md` §1; required before any dated lane.
- Not the state model, layout contract, or prompt *contracts*.
- Not a notebook. 0 `.ipynb` files in this project and in the engine (measured);
  the 8 `notebook` mentions in `docs/` are all sentences asserting the absence.

---

## 4. The seam

`TopicProfile` is a **frozen dataclass whose defaults equal today's behaviour.**
That is the behaviour-preservation requirement, not a style choice: the `tutorial`
profile must reproduce today's artifacts exactly, or §3 goal 3 is unprovable.

**v008 changes two field types and deletes one, on the strength of two external
reviews** (external review 1 and external review 2; triages since folded into
this section and removed). Both findings
were about the *same* defect — a string label that reaches the artifact under two
spellings, in one renderer and not the other — and both are better answered by a
type than by a policy.

| field | type | replaces | note |
|---|---|---|---|
| `section_policy` | `SectionPolicy` over a **`SectionKind` enum** | `_SECTIONS` **and** `_ENUM_HINTS` **and** `_infer_section`'s 4-tuple **and** the labels in `STUDIO_PROMPT` | **not strings.** See §4.3 |
| `scene_counts` | `SceneCounts` | `MIN_SCENES`, `TARGET_MAX_SCENES`, `AUTO_TRIM_MAX_SCENES`, `_MAX_PATCH_SCENES`, the `>= 10` slack, the `6` in `_plan_scene_target`, the bare `5` in `cli.main` | **seven** behaviours across **five** named constants plus one literal |
| `enrichments` | `tuple[Enrichment, ...]` | four hard-wired mechanisms across `_populate_concrete_values`, `_populate_status_badges` and `_ensure_technical_visuals` | **per-mechanism, not a list of strings.** One fabricates content — see §14.3. *v008 argued this type in prose while omitting the row, and §4.4 then listed the field; corrected here* |
| `script_policy` | `ScriptPolicy` | the two `reject_non_latin_*` validators **and** the script rule inside both prompts | the largest single item; mechanism in §4.1 |
| `voice` | `NarrationVoice` | — | **stays**, and keeps only what is *spoken*; prompt-level and slide-level language moved out (§4.2) |

**Three field types earlier drafts got wrong.**

*`section_policy` cannot be a tuple of strings.* `_infer_section` re-types the
taxonomy in title case with an `idx == 1` special case, then rotates the rest on
`(idx - 2) % len(spread)`. A 5-tuple cannot express *"index 1 is special"*, which
is why the second copy exists. The honest shape is a **rotation policy** — a
first-scene override plus a cycle — over a canonical label set, with the keyword
hints attached. Splitting the tuple from the hints is worse than the status quo:
one function's two coupled mechanisms, and one object owns both or the seam has
not fixed anything.

*`scene_counts` needs seven behaviours, not three.* With three, the design's own
behaviour-preservation criterion is unsatisfiable: `_scene_count_problem` applies
a **fourth** threshold (`>= 10`) with a ±1 slack, `_plan_scene_target` returns a
**fifth** value (6), `cli.main` hard-codes a **sixth** and a **seventh** (two bare
`5` literals), and `_MAX_PATCH_SCENES` is a **sixth named constant** a sweep of the
original five names never sees.

*`enrichments` is not a list of strings.* It is four mechanisms with **different
correctness properties**, and one of them — the `json_snippet` enrichment —
**fabricates content**: it fires a regex on `{schema_version, baseline_id, path}`
in the source and writes a hard-coded literal payload (`v1.2.0`,
`eval/baselines/v1.2.0.json`) that is **not read from the match**. See §14.3.

**A fifth field is DELETED: `decision_prompt_rule`.** Its stated default
(`dd_leads` / `bullet_leads`) is not prompt framing at all — those are
`NarrationVoice` fields consumed by the speech layer. A field whose stated default
lives in another object has no referent. If the framing is prompt-level it belongs
to the prompt policy; if voice-level, `voice` carries it. **A field with two
possible homes and no named consumer is dead**, and dead fields are how the wrong
field type got here.

### 4.1 How `script_policy` actually reaches a Pydantic validator

Stated because the obvious mechanism is wrong, and the wrong one is silent.

`SlideScene` and `LessonPlan` are `BaseModel`s whose validators run at
construction. The channel cannot pass a constructor argument to a nested model
field, and a module-level global would be exactly the unreachability §2 is about.
**The mechanism is Pydantic's validation context** — `plan_lesson` reaches
`LessonPlan.model_validate(plan)`, and that is the **only** construction site in
the vendored tree (measured), so one kwarg is enough *in principle*.

**Measured, and it does not work yet: this is a change to a file we own, not a
keyword.** Both validators are `(cls, v)` — neither takes `ValidationInfo`, so
`info.context` reaches nothing as the code stands. A Devanagari `section` **raises
in all three context states**, because the reject branch is unconditional. Two
consequences the implementation must honour:

- **The context argument is only load-bearing once the validators read it.**
  Until then, `ScriptPolicy` is unreachable and the field is decorative.
- **The default must be today's behaviour, not "no policy".** A no-context
  fallback that *passes* would make the only production call site silently stop
  rejecting non-Latin plans — the exact behaviour change §4's "defaults are the
  contract" rule forbids. The fallback has to be the current policy.

**The trap, which is real and was measured:** `Model(x=..., context=...)` does not
raise — under the models' `ConfigDict(extra="ignore")` the kwarg is swallowed and
never arrives. The context must go through `model_validate(..., context=...)`,
and a test must fail when it does not.

### 4.2 `voice` keeps the spoken language, and nothing else

v007 said `voice` *"grows prompt-level and schema-level consequences"* without
naming either — which is the exact failure diagnosed nine lines below it. v008
splits the three places a language contract is currently decided, and gives each
one an owner:

| decision | owner | today |
|---|---|---|
| what the model is **asked** for | the two prompt formatters | neither takes a `voice` argument, so choosing a voice does not change what is asked for |
| what is **spoken** | `NarrationVoice` | works: `narration_matches_voice_policy` in `narration.py`, **0** direct hits in `tests/`, covered only transitively via `_render_blocking_problems` |
| what may appear **on a slide** | the two validators, via `ScriptPolicy` | raises, but the branch is untested (§12) |
| what appears in the **source** | immutable | `full_text` |
| what appears as a **caption** | `caption_text`, planned in `PLAN.md` §4 | not in the LLD until v008; see §4.4 |

**`voice` itself is not dropped.** It is the one field with a working, tested
implementation and a live consumer; removing it makes the document shorter and the
lane worse.

### 4.3 Section kinds are a type, not a string — and the schema enforces it

The v007 design was string-based, which is *why* one label reaches the artifact
under two spellings and why a fix landed in one renderer. Measured: `_SECTIONS` and
`_ENUM_HINTS` are lowercase; `_infer_section`'s `spread` is title-case and holds
only **4** labels plus a separate `return "What Is This?"`; `STUDIO_PROMPT` is
sentence-case prose; and `slides.py` **and** `pptx.py` both inject `"Key Takeaways"`,
which is **in no enum at all**. Worse, one label reaches the artifact under **two
spellings**: `_normalize_sections` writes `section.title()` → `"What Is This"`,
while `_infer_section` returns `"What Is This?"` **with** the question mark.

```
class SectionKind(StrEnum):
    OVERVIEW / MECHANISM / EXAMPLE / TAKEAWAY   # the engine's four rotated labels
    # + the tutorial lane's own kinds, added by this lane, not by the engine

class SectionPolicy:                            # frozen
    kinds: tuple[SectionKind, ...]             # canonical, no strings
    first_scene_override: SectionKind           # the `idx == 1` special case
    cycle: tuple[SectionKind, ...]              # the `(idx-2) % n` rotation
    hints: tuple[tuple[SectionKind, tuple[str, ...]], ...]
    def label_for(self, kind: SectionKind) -> str: ...
```

**Both renderers call `profile.label_for(scene.kind)` and neither accepts a
`str`.** That is what makes "the fix landed in one renderer and not the other"
*unrepresentable* rather than merely reviewed. `SlideScene.section` becomes
`SectionKind`, so a post-pass is not needed to enforce the enum.

Enforcement, in order of strength: the `StrEnum` type; schema rejection of an
unknown kind; the single `label_for` accessor; and one render assertion per
`(renderer × SectionKind)`.

**Two corrections, because a blacklist here is the wrong instrument.** v008 said
*"no renderer-owned title strings **at all**"* and simultaneously kept
`"Key Takeaways"` in both renderers — those two sentences contradict. And the AST
check v008 proposed fails only on a **known** label, which is a blacklist over
2026-09-28's strings: **a new renderer title would pass it**, which is exactly how
`"Key Takeaways"` got there in the first place. **The check is an allow-list** —
every string constant in the two renderer modules must be on an enumerated list, so
a new literal fails — and `"Key Takeaways"` is the one sanctioned exception, named.

**`label_for` is declared on `SectionPolicy` and called as `profile.label_for`.**
Say which: it is a re-export, not a second home. A method with two spellings is how
`decision_prompt_rule` happened.

**`"Key Takeaways"` is a renderer label, not a kind**, and it stays excluded **by
name** — the two renderers keep drawing it, and the profile does not own it.

### 4.4 Runtime and environment facts are not content policy

`TopicProfile` is for *content* decisions. Runtime and environment facts are a
different object, and folding them in would recreate the two-homes defect §4
already deleted one field for. The project already owns two of these; this adds
one and splits one.

| object | holds | status |
|---|---|---|
| `TopicProfile` | section kinds, scene counts, script policy, enrichments | §4 above |
| `NarrationVoice` | language, voice id, speed, pronunciation pack | **exists**, tested |
| `RenderProfile` | canvas, font, caption safe zone, renderer settings, transitions | **exists** in the vendored `config.py` as `BRAND_*` + render constants; promoting it to a named object is optional |
| **`TutorialEnvironmentManifest`** | target OS, shell, tool + version policy, prerequisites, **expected success condition**, **source freshness** | **NEW** — §6.4 |

`TutorialEnvironmentManifest` exists because a command can be genuine,
source-backed, correctly ordered, and still **unusable**: a Windows PowerShell
lesson running a Linux installer, or a PATH change with no "reopen the terminal"
step, leaves a beginner unable to diagnose *command not found*. Provenance valid,
verbatim in source, correctly ordered, and wrong. **Verified command ≠ correct
practical tutorial.**

### 4.5 The "no dates to fabricate" argument was too broad — and is replaced

v007 deferred the entity + temporal gate (`A1`/`A2`) partly on the reasoning that
*"there are no dates to fabricate"* in a tool tutorial. An external review found
that **too broad**, and it is right: a tool tutorial is full of temporal facts —
tool versions, supported Python versions, OS assumptions, deprecations, and output
that differs by release.

**The deferral stands, on a narrower and correct argument:** the failure mode that
makes date grounding fatal — a history video's value *is* its dates and its order —
is unreachable here, while `TutorialEnvironmentManifest` covers the temporal facts
this lane actually has. §14.2 records the corrected reasoning.

## 5. System context, vendoring, and the module map

**This package does not depend on `doc-to-video-tutor`.** That project is a
**baseline reference** — read for its measurements, its gate structure and its
failure records. Nothing here imports it, installs it, or pins its version
(`uv.lock`: **0** references, measured 2026-09-28), and the two trees move
independently. The pipeline is **vendored into this package**.

Three consequences, and they are the reason this architecture was chosen:

1. **§7's hook is local.** `_extra_gates` is a function in `plan.py`, not a
   proposal to another team's pipeline.
2. **The 39 occurrences and the six missed sites are ours to fix.** They are
   inventory of *our* `config.py` and *our* `plan.py`, so §12's audit can require
   every one, and declining to fix one is a decline rather than a waiting game.
3. **"No edit outside §4" is now trivially true** — every edit is inside this
   package.

### 5.1 What is vendored

**The v005 map named 8 modules and was not buildable.** Measured by import
closure, the 8 it named pull in **16**: `plan` imports `config`, `duration`, `llm`,
`narration`, `text`, `topics`, `util`, `voice`; `validate` imports 8 more;
`video` imports `pptx` and `slides`. **Eight modules were missing** — `duration`,
`llm`, `narration`, `speech`, `text`, `topics`, `voice`, `schema` — each a hard
import from a module the map *did* list.

*Closure measured two ways, and the difference is why the number is stated
carefully.* A module-level walk gives **15**, because `plan` reaches `schema` and
`validate` through **function-local** imports. Those are still hard requirements,
and the copy must carry them. **The table below is the full closure, 16 copied
modules.**

| # | module | lines | take | why |
|---|---|---:|---|---|
| 1 | `plan.py` | 2,505 | copy | planner; hosts the `_extra_gates` registry; carries the bulk of the constant reads |
| 2 | `pptx.py` | 1,022 | copy | reachable renderer 2 of 2; **injects the same `"Key Takeaways"` label as `slides.py`** — 2 write sites per renderer across 2 modules, not 1 |
| 3 | `cli.py` | 875 | copy | **the build path**; 5 subcommands; **3 of the 4** `_render_blocking_problems` call sites (the 4th is in `plan.py`) |
| 4 | `video.py` | 855 | copy | reachable renderer 1 of 2; TTS + moviepy assembly |
| 5 | `narration.py` | 1,107 | copy | narration contract; holds the **second** `_ask_llm_stable` binding (§5.6) |
| 6 | `speech.py` | 765 | copy | TTS, `contains_corrupt_text`, `spoken_token_set` |
| 7 | `slides.py` | 758 | copy | reachable renderer; injects `"Key Takeaways"`, which no enum declares |
| 8 | `validate.py` | 530 | copy | `_render_blocking_problems`, `guard_plan` |
| 9 | `text.py` | 369 | copy | `_has_non_latin_script`, `_nar_tokens`; zero internal imports |
| 10 | `config.py` | 356 | copy | `_SECTIONS`, `_ENUM_HINTS`, both prompts, `_SOFT_PREFIXES`, `BRAND_*` |
| 11 | `voice.py` | 341 | copy | `NarrationVoice` + registry — the one field with a working consumer |
| 12 | `duration.py` | 285 | copy | the duration formula and `duration_verdict` |
| 13 | `llm.py` | 283 | copy | `_ask_llm_stable`; the module both bindings resolve through |
| 14 | `util.py` | 230 | copy | `LoadedSource`, `load_documents`; zero internal imports |
| 15 | `schema.py` | 123 | copy | `SlideScene`, `LessonPlan` — the only two Pydantic models |
| 16 | `topics.py` | 88 | copy | `_BANNED_NGRAMS` consumers |
| 17 | package-root `__init__.py` | 280 | **drop** | every symbol is dead or is the deprecated shim: `TUTOR_PROMPT`, `generate_lesson`, `text_to_audio`, `_split_sections`, `_make_slide_image`, `create_video`, `main`. **Nothing imports the root from inside the package** (0 hits) |
| 18 | `studio/__init__.py` | 218 | **drop** | a re-export façade only. §5 creates **no** `studio/` subpackage, so there is nothing for it to front. Its re-exports are **5 of the 39** and each carries `# noqa: F401` — a suppression that would hide a *second* binding of exactly the constants §4 exists to reach |
| 19 | `studio/__main__.py` | 7 | **drop** | exists only to serve `python -m`. §5 creates one entry point, `main(argv)`, and a `__main__` would be a second door |

**16 copied = 10,492 lines · 3 dropped = 505 · total 10,997 = the whole tree.**
With the 7 test files (7,097 lines) the copy is **23 files / 17,589 lines**.

**The test suite is 64.5% of the source and was absent from the map** (7,097 test
lines ÷ 10,997 lines across the 19 modules — a module denominator, not the 23-file
copy). Every test file's imports change on the copy, because every one of them
names the package root. **Two earlier statements of this were wrong, and both are corrected here rather
than deleted.** v007 claimed **0** private names are reachable through row 18's
façade, and that its 11 exports are module names. Measured: the façade binds
**193** imported names of which **146** are underscore-private, and `__all__` holds
**11 entries which are function names** (`assemble_video`, `build_pptx`,
`build_tts_script`, `guard_plan`, …) with **0** module names. The *tests* reach
**48 distinct private names over 261 `S._…` sites** through it.

So both halves were false, and the consequence is worse than the error: **v008
deleted the `48` as "not reproducible", and it is reproducible** — 48 distinct
names over 261 sites, by the obvious measurement. The earlier deletions that
produced 89/191, 25/70 and 0/0 were counting a different population and were
never the right question. **The number is restored, with its population stated:
48 distinct private names, 261 sites, reached through the façade.**

**"Closed population" is a claim about a commit, not about the world.** It is
**closed relative to reference commit `VENDOR_REF`**, and if the reference gains a
module the copy silently stops being the whole tree. `vendor_manifest.json`
(§5.3) records what was taken and what was left, per file, with a hash. **There
is no drift-detection mechanism and this document does not claim one** — a CI job
would need network access to a repository this project has deliberately cancelled
any relationship with.

**Not vendored, and the population is closed:** the reference's `output/` (368
entries), `.env` (untracked and gitignored), its docs, `opencode.json`,
`.opencode/`, its two 4.2 MB moviepy temporaries, and its two plan documents.
`pyproject.toml` is **not copied** — merged by hand, and two conflicts need
resolving rather than diffing: the channel's `[tool.coverage.report]` deliberately
has **no `fail_under`**, and the reference sets `fail_under = 58` over a different
`source`.

### 5.2 The `.docx` reader: wired, reachable, and unannounced — and not behind a gate that excludes it

Ruled 2026-09-28 (§14.4). The parser ships; the format is **not announced**.
Measured: `.docx` appears **0 times** in the vendored `src/`, and the only format
claim is one argparse help string naming `.md, .txt, .pptx`. There is nothing to
un-publish.

**But `A15` and `A33` currently contradict each other, and that is now a named
gap rather than an accident.** `A33` makes the reader an *"optional import"* while
`A15` is a hard extension allow-list — so the reader is unreachable behind a gate
that does not list `.docx`. **They are resolved together or not at all:** either
`A15`'s allow-list carries `.docx` and the reader is ordinary code, or the reader
and the corpus both stay deferred. Splitting them produced the current
contradiction, and splitting them again would hide it.

**The door is not `.docx`-shaped; it is unbounded.** A `.rtf` whose bytes decode
as UTF-8 **loads silently** (measured: no exception, no refusal), and a `.docx` —
a zip — raises `UnicodeDecodeError` *after* the LLM call. So `A15`'s allowlist is a
**correctness gate**, not a UX affordance, and it is what makes "unannounced"
implementable: the set of accepted inputs becomes a fact rather than an accident
of encoding.

**The corpus is referenced, never vendored.** The 18 documents are read from an
external path (environment variable), the tests skip when it is absent, the path is
gitignored, and **synthetic `.docx` are generated for CI.** This is what keeps
`RIGHTS.md` §0's *"read on this machine, never uploaded, never narrated into a video, never published"* true of
the repository as well as of the machine. Measured: **30 paths, 18 unique
documents** — and **12 byte-identical copies of six of them sit outside the
excluded path** (§8.4).

### 5.3 `VENDOR_REF` and `vendor_manifest.json`

`VENDOR_REF` is a **module constant in the copy** — `config.VENDOR_REF` — carrying
the reference commit the copy came from, and it is also written into
`*.verify.json` (§6.3) so a shipped artifact can name its own origin.

**`VENDOR_REF` is created at V0; it does not exist yet.** Measured 2026-09-28: **0
occurrences** across the whole baseline repository — `src/`, `tests/`, `docs/`,
`pyproject.toml` — while this document mentions it 15 times, and a real
`*.verify.json` carries `counts, duration, gates, layout, media, plan_path,
plan_sha256, schema_version, target_minutes, verdict` with **no** `vendor_ref`,
`ref` or `commit`. So v009's three present-tense claims above were **forward
references to components V0 has not created, written as descriptions of things
that exist** — which is `DOCS.md` rule 8 inverted. Until V0 lands, the ref is
literally **`a7d63e0`** (`git -C ../doc-to-video-tutor rev-parse --short HEAD`), and
§5.4's V-1 step uses that value.

**This is what makes §4's central rule mean something after vendoring.** As
written, *"a field's default is what the engine does today"* is a **wall-clock**
reference in a document whose own rule is that stored claims rot — and after
vendoring it has **two** referents which already differ. So:

> *Defaults are the contract.* A field's default is what **the vendored copy does
> at `VENDOR_REF`** — a named commit, not "today". The reference may keep changing;
> the contract is the copy in this tree. If a default cannot be written as *"what
> the copy at `VENDOR_REF` does"*, the seam is not yet understood — stop and
> measure, do not guess.

**Code provenance is strictly weaker than command provenance, and must therefore
be embedded rather than referenced.** A command's `claim_id` binds a runtime
artifact to a source span and is verifiable **now, on this machine**. Copied-code
provenance binds a file to a tree we have cancelled any dependency on, so it is
verifiable only by re-fetching a repository this project deliberately does not
track. A `claim_id` we can check beats a commit hash we cannot.

`vendor_manifest.json` is the record, one row per artefact:

```
reference_repository, reference_commit (= VENDOR_REF), imported_at
files[]:            source_path, source_hash, vendored_path, vendored_hash_at_import
excluded_files[]:   path, reason        # the three rows of §5.1, by name
```

**It is a manifest, not a tripwire.** Nothing re-checks it (§5.1), and the LLD
does not claim otherwise.

### 5.4 Order of operations — with a render spike first, and a gate on every step

**v007 vendored 17,589 lines across V0–V6 before any render, and V7 was the seam.**
An external review found that wrong, and it is: the largest user-facing risks —
terminal font unreadable, captions over output, audio/visual drift, a mispronounced
command name, renderer differences across environments — cannot be tested until
after the whole copy, and never before. **So a spike comes first.**

| step | unit | gate before the next step lands |
|---|---|---|
| **V-1** | **the spike.** Render the **minimum legal plan — 5 scenes**, one of them the `uv --version` scene. *"One scene" is unreachable and the blocker is the baseline's own gate: `MIN_SCENES`/`TARGET_MAX_SCENES` are **5/8** and `_scene_count_problem` refuses fewer in **both** branches; and a 1-scene plan yields **2** TTS clips, so `assemble_video`'s `zip(strict=True)` needs 2 slide groups anyway.* No seam, no profile, no gate. **Throwaway by design — its output is evidence, not a deliverable.** It runs against the **baseline tree at `VENDOR_REF`**, which §5.5 makes legitimate, because the channel's own tree is one 66-byte file and has nothing to render. **`VENDOR_REF` is `a7d63e0` today** — the constant is created at V0 (§5.3). **It calls the renderer API directly, not the CLI:** `render`/`build` run `_render_blocking_problems`, and a spike with *no gate* must not go through it. Measured: through the CLI a 5-scene plan passes `verify` (exit 0) and is then **BLOCKED** by `render`; the direct route — `render_slide`, `build_tts_script`, `synth_scenes`, `assemble_video` — produces media, is **model-free**, and needs no endpoint. **It must call `video._write_webvtt` itself:** that function is reached only from `_render_media`, which is behind the gate the spike skips, and without it the artefact carries **no `.vtt` at all** | **measurable forms, not adjectives:** minimum caption glyph height at 720p; **disjoint** bounding boxes for the caption and the command panel; `ebur128` within the `A18` target ± a stated tolerance; the narration transcript contains the tool name **and** a matching `WordBoundary` token. "Legible", "intelligible" and "pronounced correctly" have no instrument and cannot fail — which is why §12's row for this states the instruments |
| **V0** | the §5.1 table + `vendor_manifest.json` + the tree's **first commit** | `uv sync` resolves from a fresh clone; the manifest's hashes match the tree |
| **V1** | `util.py` + `text.py` + `config.py` — **955 lines** | the three zero-internal-import modules import and their tests pass. `config.py` is in this step because it has **zero** internal imports too (v007 said "the only two" and was wrong), which also gives `VENDOR_REF` a file that exists at V1. **`AC#17`(a) is a V1
criterion, not a reader criterion:** `_truncate_on_boundary` is a `str → str`
function in this step's `util.py`, and its two properties — the cut never ends
mid-token, and the cut uses at least half the window it was given — are falsifiable
on a synthetic source today. **This step also carries `A5`, the `.docx` reader**,
and *v010 left that unplaced* — this row and `AC#17`(b) both said "the step that
carries `A5`" and **no step in this table did**: a forward reference to a step
with no number, which is `DOCS.md` rule 8 inverted. It is **V1** because
`load_documents` arrives here (§5.1 row 14) and `A5` extends that same function,
so placing it later would mean shipping a reader that raises
`UnicodeDecodeError` on `.docx` and calling the tree green. **`AC#17`(b)
therefore unblocks at V1**, and its measured population is below |
| **V2** | `topics.py`, `schema.py` — 211 lines | the two Pydantic models validate; `AC#6`'s Devanagari case reaches the validator |
| **V3** | `BRAND_NAME` / `BRAND_FOOTER` — **2 lines** | one scene rendered, frames sampled, old brand absent and new brand present. `PACKAGE_NAME` renders on **100% of runtime frames**, so copying it verbatim is *correct* per §5.5 and invisible in a 17k-line diff — which is why it is its own commit |
| **V4** | `plan.py` — 2,505 lines, alone | **carries §5.6's harness in the same commit**, not after it: the harness's purpose is to run `plan_lesson`, and `plan_lesson` arrives *with* V4, so gating V4 on the harness is circular |
| **V5** | the remaining **10** modules (`cli`, `duration`, `llm`, `narration`, `pptx`, `slides`, `speech`, `validate`, `video`, `voice` — **6,821** lines, *not the 9,326 v010 stated: measured, and the build order is now checked by `test_the_build_order_accounts_for_every_line`*) | all 315 vendored tests pass; the audio gate and caption gate are reachable; **`write_media` exists and both `_render_media` call sites route through it** — the media chokepoint §8.3 creates here, and `AC#26` is a V5 criterion because the component it gates does not exist before this step. *v008 said 8; 16 − V1(3) − V2(2) − V4(1) = 10* |
| **V6** | the 7 test files, import-rename only | the collection report shows the expected count **and** the run count |
| **V7** | the seam (Phase 1) | the behavioural differential, the ownership audit, the two renderers × every `SectionKind` |

**Every step runs the vendored tests before the next lands.** v007 gave an order
with no test gate between steps, and the design had never been exercised end to
end; a V0–V7 list without gates is seven hopeful commits, not seven reviewable
ones.

**The copy arrives `src`-green, and the `tests/` half does not — measured, because
the difference decides what the gate can say.** `mypy` under this package's
*stricter* settings reports **`Success: no issues found in 19 source files`** for
`src` — and **74 errors in 7 files** for `tests`, 84 combined. The error-code split
matters, because the rationale for excluding `tests/` was built on it and it was
wrong: **43** `no-untyped-def`, 21 `[index]`, 4 `[no-any-return]`, 3
`[attr-defined]`, 3 others. **So "all `no-untyped-def`" was false in kind, not just
count — 31 of the 74 are not annotation debt at all.** The gate stays `mypy src`
by decision, and the honest reason is that the vendored tests are type-dirty in
several ways at once. *(No count of untyped helpers is published: four populations
returned 43, 24, 43 and 36.)*

**No exemption is needed and none should be taken** — the 10k-line mypy debt this
document once worried about does not exist.

**The coverage denominator is a decision, and it is currently unwritten.**
`source = ["doc_to_video_channel"]` and the vendored modules land **inside that
package**, so after V5 the denominator is **97%+ vendored code the channel did not
author** — against a seam of 250–350 lines. A single total over that is close to
meaningless: it averages deterministic gate logic against provider-bound
orchestration, which is the same objection the reference's own config records about
itself. **So the floor keys to the channel's own code, and the exclusion is
generated from `vendor_manifest.json`'s `files[]` rather than typed by hand** — that
is the one job the manifest's shape is already exactly right for. The floor is set
at V7 against a measured baseline over that population, as a ratchet, and until
then the deliberate absence of `fail_under` stands.

### 5.5 Verbatim on arrival, with three named exceptions

A behaviour-preservation claim cannot be made about code that changed on the way
in. The copy is **byte-identical modulo the import root**, with exactly three
exceptions: the import root rename; rows 17–19 dropped; and `BRAND_*` — which is
**not part of the copy commit**, being V3, so the copy commit is provably a move.

### 5.6 Precondition: the replay harness, and what it must prove

`plan_lesson` is **never executed by the existing suite** — of 20 test references,
5 are `inspect.getsource` string assertions and **0** are calls. So §12's
behavioural differential needs a way to run planning without a model, and the
harness has one trap that cost this document two review rounds:

**`_ask_llm_stable` is bound twice.** `plan.py` and `narration.py` each hold their
own module-level binding of the same `llm` function. A harness that patches only
`plan`'s binding measures the plan chain and is **structurally blind to the
narration chain**.

**Measured 2026-09-28, with both bindings patched and a deterministic stub: 1
distinct plan digest over 6 runs.** The repair chain *is* deterministic. An earlier
"8 of 8 distinct" reading was a harness artefact — one unpatched binding — and is
withdrawn.

**The hole is narrower and worse than "the fixture is not passing yet".** A
deliberately unstable stub that *varies* produces **6 distinct digests over 6
runs**. But a stub that varies **only the narration response** produces **1 digest
over 6 runs**, and the narration is byte-identical in all six — the stub's
narration never reaches the plan dict. **So the plan-digest check is structurally
blind to the narration chain**, which is the sole reason §5.6 patches two bindings.
Patching both is **necessary and not sufficient**, and a passing fixture will not
fix it.

**So the precondition is: vary within a run, and digest an artifact that carries
the narration — the written `*.tts_script.json`, not the plan dict.** If an
alternating stub still produces one narration digest once the fixture passes, the
harness is not measuring what it claims and the differential is not a check.

## 6. Data contracts

Five contracts, each defined by a gate that consumes it. A type no gate reads is
not a contract, and `DOCS.md` §5 records what inventing types gets us.

### 6.1 `AdapterResult` — the ingestion return value

`DESIGN.md` §4.2 fixes an 8-field shape. **`util.LoadedSource` already carries most
of it** (measured: **five dataclass fields** `text`, `full_text`, `chars_read`,
`chars_total`, `read_window`, plus `truncated` as a **`@property`**). So the
overlap is **two fields by name** (`full_text`, `truncated`), one synonym (`text`
for `content`), and three the 8-tuple does not have.

`AdapterResult` therefore **adds** `concepts`, `concepts_total`,
`concepts_in_window`, `topics` and `source_files`, and **carries** a
`LoadedSource`. It **also carries the `fixture` bit** (§8.1) — a flag living only
in CLI arguments can be dropped by any stage that rebuilds its inputs from paths,
and several do.

**The access path must be named, or this is an unstated rename.** The 8-tuple's
first member is `content`; `LoadedSource`'s field is `text`. `AdapterResult`
exposes the latter, so the spec's `content` is reached as `result.source.text`.

`concepts_total` exists so coverage publishes **the population it was counted
over**. `AGENTS.md` is explicit that a count with no denominator is a lie that
looks like a pass, and the engine's ledger has published
`unclaimed_source_sections: 0` beside `source_sections: 12` — two different 12s,
numerator over 8. The adapter must not be able to produce that pair.

### 6.2 `CommandClaim` — the provenance record, as an event log

`FR-016`, `A22` (the `claim_id` record) and `A32` (binding the command to its
admitted source span, and making a *deleted* command blocking) are **three
requirements, not one**.

| field | type | notes |
|---|---|---|
| `claim_id` | `str` | stable, and the key the report publishes |
| `command` | `str` | the exact text shown on screen |
| `source_span` | `tuple[int, int]` | into the **source file**, never into a model response |
| `source_file` | `str` | must pass **`A41` (source allow-list)**. **`str`, not `Path` — see below** |
| `polarity` | `Literal["positive", "negative"]` | **NEW in v008.** A command appearing verbatim inside a *"do not do this"* example satisfies "appears verbatim within its source span". Only a `positive` claim may be rendered |
| `status` | `Literal["issued", "admitted", "dropped"]` | the drop reason is recorded, never inferred |
| `drop_reason` | `str \| None` | set iff `status == "dropped"` |
| `verification_status` | `Literal["verified", "unverified"]` | no third value; a missing record is `unverified` |
| `issued_at_stage` | `str` | the pass that created it — **the raw model response**, before anything mutates it |

**Every claim record is JSON-safe, and that is not a style note — a `Path` in the
plan dict crashes every build.** Confirmed by execution: the plan is written by
`atomic_json_write`, whose `json.dump` has **no `default=`**, and
`{"claim_source": Path(...)}` raises `TypeError: Object of type PosixPath is not
JSON serializable` on the first write. This is the same failure §7 documents for a
`Callable` and fixes by making `_extra_gate_ids` JSON-safe; the `CommandClaim`
record needs the same treatment. `source_file` is a **`str` in the record** and a
`Path` only at the validator that resolves it.

**`polarity` needs a producer, and the model cannot be one.** A claim is built from
the raw model response, so the model cannot judge its own grounding. `polarity` is
therefore assigned by a **deterministic negation-cue scan over `source_span`** —
prose markers such as *"do not"*, *"avoid"*, *"instead of"*, *"never"* — and a
claim whose span carries a cue and no affirmative context is `negative`. Absent
that scan, the field is decorative and the `AC#24` criterion, which hand-builds a
`negative` claim, proves nothing about assignment. **If the scan is not built, the
field is marked advisory and `AC#24` is withdrawn** — it must not sit in the
lane's only blocker unassigned.

**These are immutable event records, not aggregate counters, and that is the whole
point of v008's change.** Counts derived from records can be audited; counters
written at the end cannot. The report publishes **id lists**, not totals (§6.3).

**`A33` is a live ID collision and is spelled out at every use until it is
resolved.** `DECISIONS.md` §1 defines `A33` as *"Corpus excluded from publication;
the publishable source is the owner's own notes."* `PLAN.md` §7 reuses the same
number for a **source allow-list**. The ledger is not ambiguous and `PLAN.md` is
wrong, so **`A33` keeps the ledger's meaning and the allow-list becomes `A41`**
(§14.2). **The population is 24 sites across 6 files, not "7 in one document"** —
measured, and the earlier figure answered a different question. Until the rename
lands, this document writes **`A33` (corpus excluded)** or **`A41` (source
allow-list)** in full.

**Naming collision, deliberate.** The renderer labels the panel `COMMAND CONTEXT`
while the schema field is `code_snippet`. The channel speaks `command` and
`claim_id`; the vendored vocabulary is unchanged, and the channel's fields sit
**beside** them, not through them.

### 6.3 `VerifyArtifact` — what a gate writes

The engine already writes `*.verify.json`, **including on blocked paths**. The
channel adds no new artifact format, only fields existing readers ignore:

| field | written by | why |
|---|---|---|
| `command_provenance: {presented, issued, admitted, dropped, claims[], rendered[]}` | §7 | **id lists, not totals.** See §6.5 |
| `environment: TutorialEnvironmentManifest` | §4.4 | a published video must name the environment it was made for |
| `vendor_ref: str` | §5.3 | `VENDOR_REF`, so a shipped artifact can name its own origin |
| `audio: {expected, found, ebur128, verdict}` | `A18` | the per-clip contract |
| `captions: {cues, file, verdict}` | `A18` | **fails on zero cues** |
| `disclosure: {llm_host, tts_host, source_bytes_sent, narration_bytes_sent}` | `NFR-006` | data egress is currently undisclosed |
| `fixture: bool` | §8.1 | **and it must reach the media too** — see §8.2 |
| `practical_steps[]: {purpose, action, expected_result, recovery}` | §4.4 | the completeness gate |

A blocked build still writes this file. That is existing behaviour and it is worth
keeping: a failed build is the artifact people actually need.

### 6.4 `TutorialEnvironmentManifest` — what "verified command" does not cover

A command can be genuine, source-backed, correctly ordered, and still **unusable**.
This is the object that closes the gap, and it is **per video, not per profile**.

| field | example for the `uv install` video |
|---|---|
| `target_os` / `target_os_version` | `linux` / the versions actually observed |
| `shell` | `bash` |
| `tool` / `version_policy` | `uv` / `current_official` |
| `prerequisites` | python 3.12+ present; or *not required* — stated either way |
| `expected_success_conditions` | `uv --version` returns a version string; `uv init` creates a project config file |
| `recovery` | *reopen the terminal* if PATH changed; if still unavailable, revisit the install step |
| `source_verified_at` | the date the owner's notes were run |
| `staleness_policy` | warn or block, by command risk (§4.4) |

**The distinction it enforces:** the provenance gate answers *is this command real
and in the source*. It does not answer *does this command work here, now, for this
learner, and will they know whether it worked*. The second question is the one a
tutorial actually fails on.

### 6.5 The two equations, and why one of them is not enough

```
issued    == admitted + dropped                 <- reconciliation, per the ledger
presented == issued                             <- independence, the whole point
rendered  ⊆ admitted
rendered  == [c for c in admitted if c.verification_status == "verified"]
```

**Two errors in v008's first draft of this, both corrected here.** v007 wrote one
equation, `issued + dropped == presented`, which is a relation over the *wrong*
three terms. v008 split it and then justified it with a derivation that **does not
vacuate it**: it claimed that computing `presented := issued − dropped` would make
the first equation "an identity that holds for any values". Executed over all
non-negative triples, that substitution **holds in 10 of 1,000 cases — it fails
loudly, it does not vacuate anything.** The derivation that *is* an identity is
`presented := issued + admitted + dropped`, which satisfies `presented == issued`
for **1,000 of 1,000** inputs.

So the control is right and its proof attacked the wrong vector. Two corrections:

- **`issued` does not appear on both sides.** `status` is single-valued per record,
  so `issued` can only be the empty terminal bucket — a record that is still
  `issued` when the gate runs is a **block**, not a count. Reconciliation is
  therefore `issued == admitted + dropped`, and the independence check is the
  **separate** statement `presented == issued`.
- **The falsifier must attack the derivation that actually vacuates it**: the
  `AC#22` injection raises `presented` and `dropped` by 1 each, which a
  self-summing `presented` cannot do. `AC#22` exists to falsify this, not `AC#21`
  (which is narration determinism).

`presented` is the one term nothing else can produce: it is read off the model's
own output at `issued_at_stage == "raw_model_response"`, before grounding, before
the drop, before the render. **It still needs a named producer** — nothing in the
design writes it yet, and a criterion with no producer is a sentence.

## 7. The command-provenance gate

The lane's blocker. **Reject, never repair** — `DESIGN.md` §1 fixes that rule for
the date gate and the reason transfers: `_drop_ungrounded_slide_text` already
repairs grounding for slide text, and extending repair to a command would
**silently delete it**, producing a video that looks complete and teaches nothing.

```
for each claim in the ledger:                                  # A22 + A32
    REQUIRE claim.source_file passes the A41 allow-list
    REQUIRE claim.polarity == "positive"                      # needs the §6.2 scan
    REQUIRE claim.command appears verbatim within claim.source_span
    ->  missing, ungrounded, or negative-context  =>  RENDER-BLOCKING.  no warning tier.

and, over the rendered set:                                    # v008, previously unenforced
    rendered == [c for c in admitted if c.verification_status == "verified"]
```

**The second clause was asserted in §6.5 and enforced nowhere in §7** — the
algorithm above only ever checked allow-list, polarity and verbatim-ness, so a
command could be rendered while `verification_status == "unverified"`. It is now
part of the gate, and `AC#23` witnesses it.

**The claim set is built BEFORE the drop, not at the gate.** This is the single
most important property in this document, and it is easy to get wrong in a way that
reproduces the project's founding failure. Measured ordering in `plan_lesson`:
`_drop_ungrounded_slide_text` runs at `plan.py:2397`; the gate runs at
`plan.py:2493`. **The drop is first.** So a naive `total` counted at gate time is
over **survivors**: a command the model emitted and grounding discarded is
invisible, and the artifact publishes `verified: N, unverified: 0, total: N` —
**100% over a population smaller than the one that entered.** That is
`unclaimed_source_sections: 0` beside `source_sections: 12`, one layer down, inside
the document that argues against that shape. The drop count is currently a `print`
at `plan.py:2434`; it must reach the artifact, and §6.5's equations are the check.

**The hook is IDs plus a registry, and that is not a stylistic choice — the obvious
design crashes every build.** Measured: the plan dict is embedded in a document
written by `atomic_json_write`, which calls a bare `json.dump`, and the write sits
*outside* the `try/except` around the build. A `Callable` stored in the plan raises
`TypeError: Object of type function is not JSON serializable` on the first sample
of every build, before any gate runs. Confirmed by execution.

```
plan["_extra_gate_ids"]: list[str]     # JSON-safe; the plan dict travels
# and, in plan.py, a module-level ordered registry:
_GATE_REGISTRY: dict[str, Callable[[dict], list[Finding]]]
```

`_extra_gate_ids` names entries; the registry holds the callables. The gate runner
resolves the ids at call time and never serialises a function. **§12's ownership
row reuses the same `plan[...]` channel and therefore inherits this constraint.**

`_render_blocking_problems` is `(plan, voice=None, protected=None) -> list[str]`
and is called from **four** sites: `cli.main`'s `verify`, its `render`-from-plan
path, its `build`, and inside `plan_lesson`. **§13 requires the hook at all four**,
or a build path exists that skips the lane's only blocker.

**How a finding is classified — one statement, because v005 stated it three
incompatible ways.** A channel finding from this hook is **always blocking**. Two
mechanisms make that true, and both must hold:

- **The hook returns a typed finding, not a string.** `_render_blocking_problems`
  returns `list[str]` and the soft/hard split is applied by its *callers*; a bare
  string can therefore be demoted by accident. The channel's findings are marked
  blocking **at the hook**, before any string rendering, so classification is not
  something a caller's prefix table can change.
- **A blocking finding is rendered with the `RENDER-BLOCKING: ` prefix.**

The prefix test runs the other way from what v005 assumed: a finding is demoted
only if its message **starts with** one of the soft prefixes; everything else is
hard, so a channel finding that *omits* the prefix is **promoted, not demoted**.
The residual risk is a message that accidentally begins with a soft prefix. **And
the soft set is not the same at all three filter sites** — two use the eight
`_SOFT_PREFIXES`, while the `review`-before-`build` sample loop widens it with
`_SAMPLE_SOFT_EXTRA` (`"ungrounded slide text"`), the very findings the hook would
return.

### 7.1 Narration command grounding — a THIRD gap, not the deferred one

v007 deferred `A1`/`A2` (entity + temporal grounding on narration) on the argument
that date facts are unreachable in a tool tutorial. That deferral stands (§4.5).
**But a different and unowned gap sits next to it, and six internal rounds missed
it.**

The algorithm above iterates **the commands the scene shows**. If the *narration*
says a command that is on no slide, the gate never sees it — and narration is the
field the viewer **hears**. Measured in the reference: the grounding check reads
`title`, `bullets`, `takeaways`, `visual_diagram`, `code_snippet`, and **does not
read `narration` at all**. That is the project's founding defect reproduced in a
new lane, one level down.

**So there are three distinct things, and conflating them is how it would be lost:**

| # | gap | status |
|---|---|---|
| 1 | fabricated **date / entity** in narration | **deferred**, §4.5 and §14.2, with a trigger for revisiting |
| 2 | fabricated **command** on a slide | **this section.** Implemented, the lane's blocker |
| 3 | fabricated **command spoken in narration** but not shown | **NAMED GAP. No owner, no date, not implemented.** |

Recorded rather than solved: the honest disposition is to declare it with an owner
and a date, or to add it to the lane's scope. **It is not covered by the `A1`/`A2`
deferral and must not be counted as covered by it.**


## 8. The front door, the fixture bit, and the egress chokepoint

Wave 0 is two items — `A15` the format gate, and `A6` the paragraph-boundary
fallback — plus three contracts that arrived with v008, all of which live at the
door because a door is the only place that can refuse.

### 8.1 `--test-fixture` means LOAD AND PARSE ONLY

`FR-028` as written provides two mechanisms and neither is a network control:

1. a **door refusal** — resolved source paths are compared against
   `EXCLUDED_SOURCE_PREFIXES` and the build is refused *unless* `--test-fixture`
   is passed. So the flag is what **permits** a fixture build, not a suppressible
   warning;
2. a **stamp** — the flag is written into the plan and the release report.

**What neither says is the thing that matters: that a fixture build may not call
the model or TTS.** The stamp is advisory to a human reading a report, and there
is no third mechanism making a fixture build network-free. This is not
hypothetical for this project: `NFR-006` is recorded as **VIOLATED** — the
pipeline sends source and full narration to a cloud provider with no disclosure —
so the fixture flag is an unmonitored path into exactly that.

**The flag's meaning is therefore redefined, and the change is the whole fix:**

| stage | on a fixture source |
|---|---|
| load + parse (`.md`, `.txt`, `.pptx`, `.docx`) | **allowed** — this is the point |
| any call to a model endpoint | **refuses** |
| any call to a TTS endpoint | **refuses** |
| any media write (`.mp4`, `_audio/`, `.srt`) | **refuses** |
| any `verify.json` with a non-empty `claims[]` | **refuses** |

The fixture bit is **carried on the loaded document** (§6.1), set at load time, so
a later stage that rebuilds its inputs from paths cannot drop it. A flag that
lives only in `argv` is a flag some stage will forget.

### 8.2 The stamp must reach the media, and the media writer must read it

The stamp reaches the plan and the release report. **It does not reach the `.mp4`
or the `_audio/` directory** — so the artefact that actually gets published is
unstamped, and the stamp is a *record with no control*.

Two requirements, and the second is the one that makes the first worth doing:

- the fixture bit is written into the **media's own manifest**, alongside
  `vendor_ref` (§6.3), so the published file carries its own provenance; and
- **something reads it and refuses a non-publishable artefact.**

**v008 named that something "the release step", and no such step exists.** Measured:
the CLI declares exactly five subcommands — `build`, `review`, `tts-check`,
`verify`, `render`. *v010 wrote `tts`; the parser at `cli.main` registers
`tts-check`, and the difference is load-bearing for any wrapper that shells out —
measured from the parser's own `usage:` line, not from a prose list.* There is no `release` and no `publish`, and `REQUIREMENTS.md` §4's
"release gate" is seven **human** checks that its own text calls *"a reading, not a
configuration"*. A criterion that names a non-existent component is satisfiable by
writing the sentence — which is the defect `FR-028`'s own cell names: *"a
documented rule this repo never enforced is the exact defect class of
CHECK-CMD-001"*.

**RULED 2026-09-28: the control is the media writer, and `publish` is withdrawn
rather than deferred.** A verb nobody is obliged to run gates nothing. Measured:
`_render_media` has exactly **two** call sites — the `build` branch and the
`render` branch — so a gate living in a third, separately invoked verb gates
**neither**, which is the defect `FR-028`'s own cell names. And a verb whose only
content is "re-read a manifest and print a verdict" is `verify` under a second
name; `verify` already binds its verdict to the plan bytes via
`check_audit_binding`. One verb, one job.

| | |
|---|---|
| **location** | `write_media` — the single media chokepoint §8.3 creates at **V5**. Both `_render_media` call sites route through it, so **no path writes media that skips it** |
| **input** | the media manifest being written, carrying `fixture: bool` (from `AdapterResult`, §6.1) and `vendor_ref` (§6.3) |
| **output** | on success: the artefact, its manifest, and the writer's own audit row. On refusal: **no file, no partial file, and a refusal record naming the field and the value** |
| **failure behaviour** | `write_media` **raises**; the caller converts that to **`SystemExit(2)`** — distinct from the **`1`** already meaning *"gated"*, so a wrapper can tell *refused* from *broken* without parsing text |
| **refuses** | exactly one thing today: a `fixture: true` bit |

**Why V5 and not Phase 0 — it is impossible there, not merely undesirable.**
`AC#26` needs a media writer (§8.3 measures **none**), the fixture bit on
`AdapterResult` (§6.1), and `vendor_ref` in a manifest (§6.3). None of the three
exists before V5, so its wrong input **cannot be constructed**, and a gate whose
falsifier cannot be built cannot be built early. §12's row makes the same point
from the other side: the wrong input is a manifest differing only in the bit, so the
check cannot pass on a missing component.

**`REQUIREMENTS.md` §4 is referenced, not enforced.** Three of its seven checks
(*no secret visible in any frame*, *a legible thumbnail*, *the egress disclosure*)
are readings no command can make without first settling what "visible" and
"legible" mean. Mechanising them changes seven product checks, and that is **the
owner's decision**. §4 keeps all seven; what changes is one added line recording
which of them the machine now covers, so a stamp and a reading stop implying the
same kind of control.

### 8.3 One egress chokepoint, and a closed inventory of egress

The LLD closes the **import** population rigorously — 16 of 19 modules, every row
with a reason (§5.1) — and never closed the **network** population. The same
discipline has not been applied to egress, and §8.1 is unenforceable without it.

**Inventory to be written at V5, in the same form as §5.1's table:** every place
that (a) reaches a model endpoint, (b) reaches a TTS endpoint, or (c) writes media
— with its module, its chokepoint, and whether the fixture bit is checked there.
**One chokepoint per egress type**, so the check is a property of the chokepoint
rather than a thing each caller must remember. **Measured, the egress population in
the 16 copied modules is 2 sites, and v008 named 3 chokepoints of which only 1
exists:**

| egress type | real site | state |
|---|---|---|
| model | `llm._ask_llm_stable` | **exists** — one site |
| TTS | `video.py`'s provider call, reached from `synth_scenes` | **exists**, but **not in `speech.py`** — `speech.py` has **zero** network primitives, and v008 attributed TTS to it |
| media write | **none** — there is no media writer | **to be created.** Measured **≥7 write sites across 4 modules**: `video.py` (×4), `slides.py` (×2), `pptx.py`, `cli.py` |

So the inventory's closure check must be written against an **independent
enumeration** — the module list of §5.1, grepped for network primitives and write
calls — and not against the inventory itself, which is what v008's `AC#28` did and
which is therefore satisfiable by writing the table. The byte counts
`source_bytes_sent` claims must also be sourced at the chokepoint, not estimated.

This is the network-side twin of §5.1, and it is what turns §8.1 from a policy
into a control.

### 8.4 The corpus is referenced, never vendored — and the allow-list is not a path

**`RIGHTS.md` §0 excludes a *path*, and the path is not the population.** Measured
2026-09-28:

```
 18 files, 18 unique   rag-apidriven-pipeline/data/transcripts   <- the excluded path
  6 files,  6 unique   rag-eval-framework/data/transcripts      <- OUTSIDE it
  6 files,  6 unique   rag-pipeline-testing/data/transcripts     <- OUTSIDE it
 30 paths, 18 unique documents overall
```

**Twelve byte-identical copies of six of the excluded documents sit outside the
excluded path**, so a path allow-list does not exclude them. Two additions:

- a **content-hash blocklist** — the 18 md5s are safe to commit, being hashes and
  not anyone's material — plus a test that **no tracked file** matches one; and
- the corpus is **referenced by external path** (an environment variable), the
  tests **skip** when it is absent, the path is **gitignored**, and **synthetic
  `.docx` are generated for CI.**

That is what keeps §0's *"read on this machine, never uploaded, never narrated into
a video, never published"*
true of the **repository** as well as of the machine. It also settles the question
(the open question external review 1 raised) — and a reader for the corpus and the corpus itself are
kept apart for exactly this reason.

### 8.5 The two Wave 0 items, and the order they run in

**`A15` — the hard format gate.** An allow-list and `raise` at the door, **before
any LLM call**. An unsupported file is refused in one line instead of becoming a
traceback. Measured, the door today is **unbounded**: a `.rtf` whose bytes decode as
UTF-8 loads silently, and a `.docx` raises *after* the model call. So the
allow-list is a **correctness gate**, not a UX affordance (§5.2).

**`A6` — the paragraph-boundary fallback in `_markdown_sections`.** ~12 lines, one
function. `DESIGN.md` §4.3 measures it: today 1 of 6 scenes gets a `source_chunk`
and scenes 2–6 get `None` / `status: "unassigned"`; after, 6 of 6. **It is required
for this lane**, because the lane's actual input is prose notes with no headings.

**Ordering, and the order is a correctness property, not a preference:**

```
1. RIGHTS gate   (A41 / FR-028)     -- first, so a format error cannot hide it
2. FORMAT gate   (A15)              -- second, and before ANY model call
3. content-hash blocklist (§8.4)    -- third, because it is not path-shaped
4. adapter                        -- then, on validated input
5. A6 paragraph fallback           -- last: a fallback on garbage is garbage
```

**Rights before format** because if format runs first, *"unsupported format"*
**hides** a rights refusal behind a more innocuous error, and the operator never
learns the material was excluded. This extends a principle the project already
holds: `A15`'s own row commits to failing **before the LLM call**.


## 9. The audio path

`PLAN.md` §4 puts caller audio on the critical path. **The gate is `A18`, not
`A19`** — v001 used `A19` in six places, and `A19` is *"a picture-box compositing
path"* (`DECISIONS.md` §1 table).

- **`A17` `--audio-dir`.** Caller-supplied per-scene audio, exactly
  `clip_count(N)` files, **copied** into the work dir because the normaliser is
  destructive in place. **Measured: `--audio-dir` returns 0 occurrences.** The
  `audio_dir` in `video.py` and `cli.py` are **output** staging directories; the
  input flag does not exist. Do not read those hits as `A17` being done.
- **`A18` audio-contract gate.** Per-clip `ffprobe` (count, duration, codec) plus
  `ebur128` against target, and the 20/90-word band re-expressed in **seconds**
  (20 words = 11.7 s, 90 words = 52.4 s — restated from `PLAN.md` §4). With caller
  audio the word-count gates stop measuring duration at all, so a seconds-based
  contract must exist. `PLAN.md` §4 records a supplied clip at **−22.3 LUFS
  shipping under `verdict: PASS`** — the defect this gate closes.
- **The caption gate** rides with `A18`. A recording carries no `WordBoundary`
  stream, so measured captions go **55 → 0 with no log line**. `silencedetect`
  restores them at 7.6 words/cue against a target of 8, and an authored
  `caption_text` field removes the need to infer the text. **Zero cues is a
  blocking failure.** (`DECISIONS.md` §14.2: *"Captions are a gate."*)

**Record per scene, never one long file** — that convention is why the caption
gate is meaningful at all.

---

## 10. Renderers and entry points

**Two** reachable renderers: `slides.py`'s `render_scenes` and `pptx.py`'s
`build_pptx`, which `video.py` only calls. The baseline's `create_video` and
`_make_slide_image` have **0 callers**, and `generate_lesson` — the only consumer
of `TUTOR_PROMPT` — likewise, so none of them is vendored (§5.1 rows 17–19).

A third copy of the scene counts lives in `TUTOR_PROMPT`'s literal
`"5-8 sections"`, and it is **pre-seam only**: the file is dropped. A taxonomy
check must therefore scope itself to the copies that ship (§12).

**Both renderers draw `"Key Takeaways"`, and it is in no enum.** Measured: written
by `slides.py` and by `pptx.py`, four write sites across two modules. §4.3 keeps it
as the one sanctioned renderer-label exception, named rather than excluded by
membership — and §4.3's check is an **allow-list** of string constants, not a
blacklist of known labels, because a blacklist is how the label got there.

A profile test that asserts a plan is correct but never renders it **will not catch
a renderer that ignored the new field.** So §12 requires one render assertion per
`(renderer × SectionKind)`, and `AC#8` now requires the **render**, not only the
schema half — v008 asserted that assertion in this section's prose while no
criterion required it.


## 11. Configuration

| setting | source | note |
|---|---|---|
| `uv` | 0.12.2, `x86_64-unknown-linux-gnu` | measured; the project is `uv`-managed |
| Python | `>=3.12`, 3.12.13 present | `requires-python` |
| `ffmpeg` / `ffprobe` | 8.0.1-3ubuntu2 | measured; **a system package, not a Python dep** |
| `LLM_BASE_URL` | env | defaults to `""`; `build` cannot run without it (`NFR-010`) |
| narration mode | plan field | `recorded_voice` (v1) · `tts_standard_voice` (fallback) |

**Type checker: `mypy` only.** Nothing in the channel doc tree states a
type-checker requirement, and two checkers over this codebase produce a
disagreement with no tie-breaker.

**Baseline: a commit, not a path.** `VENDOR_REF` carries it (§5.3). The baseline
has **0 git tags** and is not on PyPI, and we want neither — it is a reference,
not a dependency.

**Notebooks: none, and none planned.** Measured: **0** `.ipynb` files in this
project and in the engine — though **78 exist elsewhere under `/home/dipak`**, so
"zero on this machine" is false and is not claimed. And `grep -riow notebook docs/`
returns **8 occurrences** (4 here, 4 in `PLAN-tutorial-lane.md`), every one of them
a sentence asserting the absence. v001's *"zero mentions in `docs/`"* was
self-refuting; the number is given here so a reader can reproduce it.

---

## 12. Testing strategy

`AGENTS.md` rule 8: **a check only ever shown a true statement is untested.** For
every gate the **wrong input is written first and must fail**, before the correct
input is written and must pass. This is the discipline whose absence let a
fabricated date pass a 315-test suite.

| layer | approach | wrong-input-first witness |
|---|---|---|
| **`profile` defaults** | **behavioural differential.** Build one plan from the frozen `tutorial` profile and one from all-defaults; assert the normalised `plan.json`, both renderers' output, and `*.verify.json` are identical. **Requires the §5.6 fixtures** | a profile with one deliberately wrong `scene_counts` value must produce a **different** plan. If it does not, the differential measures nothing. **Known hole:** `_infer_section` fires only on an *invalid* `section`, so a clean fixture reads as PASS — a second fixture with a deliberately bad `section` is required |
| **narration determinism** | the §5.6 precondition, restated as a criterion: **vary the stub within a run and digest `*.tts_script.json`, not the plan** | a stub that alternates its narration response must produce **more than one** narration digest. Measured: alternating the *plan* response gives 6 digests over 6 runs; alternating **only** the narration gives **1** — the check is structurally blind to that chain today |
| **taxonomy reachability** | every `SectionKind` renders in **both** renderers, and `profile.label_for(kind)` is the only source of a section label | a profile whose labels differ must be found **by string containment** in `STUDIO_PROMPT`'s text, in the `spread` rotation's output, and in the plan's `section` values. Not set equality: after the seam those names are aliases bound to the profile, so `x == x` is the vacuous form |
| **`SectionKind` typing** | an AST check fails if a known label literal appears in either renderer; the schema rejects an unknown kind | the literal `"What Is This?"` (with the question mark) must be **rejected** by `SlideScene`, and must **fail** the AST check. This is the two-spelling defect, and it is enforced in the schema rather than by a post-pass |
| **profile ownership** | a `_audit_profile_ownership` in `plan.py` reporting **which module supplied each value**, as **~10 instrumentation points** across 10 functions, all in `plan.py`. Same `plan[...]` channel as the hook, so no global. **Known limit:** `_concept_headers`, `_trim_scene_overflow` and `_overflow_audit` bind constants as *import-time default arguments* (4 bindings, 3 functions) and a side channel cannot see a default-argument binding, so this reports **7 of 10** | a value supplied by a module other than the profile must appear as a bypass row |
| **`script_policy`** | both `reject_non_latin_*` branches, through `model_validate(..., context=...)` | a Latin-script plan must pass; the wrong input is a Devanagari `section`, which must raise. The existing suite tests the *parallel* `guard_plan` path only, so the schema branch is untested on both sides |
| **the `context=` trap** | construct via `Model(x=..., context=...)` and assert the policy **did not** arrive | **must fail.** Under the default `extra="ignore"` this is swallowed silently — the exact silent-zero class, and a green test would hide it |
| **`A22`/`A32` gate** | a fabricated command with no `CommandClaim`; a claim whose text is absent from its `source_span`; a `negative`-polarity claim | **all three must block.** The polarity case is new: a command quoted verbatim inside a *"do not do this"* example satisfies "appears verbatim" |
| **`presented` from the raw response** | count `presented` off the model's own output at `issued_at_stage == "raw_model_response"` | **inject exactly one invented command before any pass runs.** `presented` must rise by 1, `dropped` by 1, and the injected `claim_id` must appear in the `presented` list. A `presented` computed as `issued − dropped` passes this vacuously — which is the point |
| **the two equations** | `presented == issued + admitted + dropped`; `rendered ⊆ admitted`; `rendered == verified ∧ admitted` | **delete a candidate after issuance without recording a drop** → reconciliation must **fail**. A command rendered outside the admitted set → the render assertion must fail |
| **finding severity** | the hook's findings are blocking, checked **at the hook** as a typed result rather than by string prefix | a deliberately-soft message must be reported **hard**; a message beginning with a soft prefix must not be demoted by the sample loop's widened set |
| **entry point** | `main(argv)` accepts `argv` and prints usage on `--help` | today `main()` ignores `argv` and prints a greeting on every invocation, exit 0 (measured) — the state this row is written against |
| **`A41` allow-list** | a build whose source path is excluded | must fail **at the door**, before the format gate's message can hide it |
| **content-hash blocklist** | a source file whose md5 is on the 18-hash list, at an **unexcluded** path | must be refused. The path allow-list alone passes this — that is the wrong-input case |
| **the fixture bit** | a build with `--test-fixture` on an excluded source | the **load** succeeds; any model call, any TTS call, and any media write must **refuse**. The wrong input is a build that reaches the provider |
| **the stamp is load-bearing** | a media artefact whose manifest carries `fixture: true` | **`write_media` must refuse it**, and the same manifest with the bit false must be written. *v009's witness said "the release step", which does not exist; and the wrong input is a manifest differing **only** in the bit, so the check cannot pass on a missing component* |
| **the egress inventory** | the §8.3 table | every egress site must appear, and a chokepoint reached with the fixture bit set must refuse |
| **`A6`** | 6 of 6 scenes receive a `source_chunk` on a prose source | a headingless source is the input; a 1-of-6 result is the failure |
| **`A15`** | unsupported extension refused in one line, before any model call | the valid case must reach the adapter; and an **excluded path with a valid extension** must produce the *rights* message, not the format message |
| **`A17`** | wrong clip count, wrong codec, wrong duration | each must block |
| **`A18` loudness** | a clip at **−22.3 LUFS** | must fail. Note §9 must also state the **target and tolerance**; a zero-tolerance reading would fail a clip the engine's own comment calls in-spec |
| **`A18` captions** | a recording with no `WordBoundary` | **zero cues must block** — the silent-zero case |
| **the `json_snippet` deletion** | a document containing `{schema_version, baseline_id, path}` | must produce **no** path on screen. §14.3's deletion breaks the existing test's *count* assertion at `assert 0 == 1`, so the test is rewritten to witness the branch is **gone** — not deleted |
| **no filler under COMMAND CONTEXT** | every rendered command panel in video one | a contentless sentence (*"Use this documented command in the lesson workflow"*) must fail. These fire on the first video, which is why the criterion is a release gate and not a backlog item |
| **practical-step completeness** | every practical scene carries purpose, action, expected result, recovery | a scene with a command and no **recovery** must fail. A valid scene is not "a command on screen" |
| **environment applicability** | each command scene's manifest | a command valid for `bash` rendered in a `target_os: windows` manifest must fail |
| **the V-1 spike** | one rendered scene, **measured four ways** (§5.4) | an `ebur128` result outside the target ± a stated tolerance must **fail**; a narration transcript missing the tool name, or missing a matching `WordBoundary` token, must **fail**. **Instruments 1 and 2 are UNAVAILABLE and are not yet rewritten** — see the note under §5.4. *v008's witness cell was a verbatim copy of its approach cell, and the four adjectives had no instrument; two of the four replacements also have none* |
**WITHDRAWN 2026-09-28 by the mentor ruling in §12.2.** Both rows were placeholders written to keep §12 looking covered while instruments 1 and 2 had nothing to measure. The ruling is to **burn captions in**, which restores both as real pixel measurements, so these substitutes are no longer needed. *Kept in the changelog rather than deleted silently, because the reason they existed — "2 of 4 instruments cannot fail" — is the finding worth keeping.*
| ~~caption text-fit~~ | ~~every cue against `_VTT_CUE_WORDS`~~ | **WITHDRAWN** — burn-in makes the real glyph measurement available |
| ~~panel geometry~~ | ~~two boxes `render_slide` computes~~ | **WITHDRAWN** — the real caption/command bbox disjointness check supersedes it |
| **brand string** | one rendered scene, frames sampled | the old brand string is absent and the new one present. `PACKAGE_NAME` renders on 100% of frames, and V3 is a 2-line change |
| **test vendoring** | the collection report | it shows the expected count **and** the run count. Tests that are copied but silently skipped are invisible otherwise |
| **static** | `ruff check src tests` and `mypy src` clean | configured in Phase 0, so this is a real check and not `All checks passed!` over an empty tree |
| **the witness manifest** | per §12 row: test id, wrong input, the assertion that failed, recorded output | re-runnable by a reviewer who was not in the room. A sentence in this document asserting the witnesses exist satisfies the earlier form of `AC#15`, which is why it names an artefact |

**Three rows are deleted, not corrected.** "Seam absorption — a probe reporting 0
bypassing reads" is gone: it is blind to prompt strings and validators, which is
the class the seam exists to prevent, and §3 goal 4 makes a manufactured silent
zero a defect rather than a pass. **You cannot write the wrong input for a check
with the wrong question.** The other two deletions are in §4.3's typing change:
a taxonomy *equality* check and a post-pass label audit are both subsumed by the
`SectionKind` type.

**The harness is a deliverable, not a footnote** — and §5.6 now says precisely what
it must prove, which is not what v007 said it did.

**On the two unavailable V-1 instruments, and why they are unavailable.** Measured
2026-09-28 against the baseline: a produced MP4 carries **2 streams**
(`h264,video` + `mp3,audio`) and **no subtitle track**; **0** files in `src/` contain
burn-in, subtitle-mux, ASS/SSA or `drawtext`; and **0 of 14** produced `.vtt` files
contain a `::cue` or `STYLE` block, so no font size is declared anywhere. A caption
that is **not on the canvas has no glyph height and no bounding box** — the height
is the *player's* property. So instruments 1 and 2, as v009 worded them, compare a
measurable thing to an unmeasurable one and **cannot fail**, and leaving them under
`AC#30` is the defect round 7 caught in the previous wording.

**This is the owner's decision, not an implementer's**, and it is a channel
question: *should a tutorial video carry burned-in captions?*

- **Burn the caption in.** Both instruments become real pixel measurements against a
  frame that contains the glyphs, and they are the checks a viewer would recognise.
  Cost: a new renderer stage, crossing **both** renderers.
- **Redefine both as properties that exist** — caption text-fit against the `.vtt`
  ceiling, and panel geometry between two boxes the renderer already computes. These
  are computable today and are the two rows §12 now carries provisionally.

*Both rows below are now **WITHDRAWN** — see §12.2. The caption decision is
RULED: burn them in, which restores instruments 1 and 2 as real pixel
measurements, so these two substitutes are obsolete. `AC#30` is gated on all four
instruments, and instruments 1–2 are unblocked by the ruling rather than by the
provisional rows.*

**One measured correction to the loudness instrument, and it is a real finding.**
`A18` gates the **pre-mux clip**, not the published file. Measured: per clip
pre-mux **−16.1..−16.0 LUFS / −1.5 dBTP**; the assembled MP4 **−16.5 LUFS /
−5.2 dBTP**; the baseline's best four delivered MP4s **−16.6..−16.7 LUFS**, against
`LOUDNESS_TARGET = -16.0` and `LOUDNESS_TP = -1.5` (both env-overridable). So the
**delivered** file differs from the gate's reading point by **0.5–0.7 LU and
3.7 dBTP**, and no tolerance is stated anywhere in this document. If the published
file is what ships, the gate's reading point should be the published file;
otherwise the band must be wide enough to absorb the mux, and **a wide band is a
weaker gate** — the same shape as `AC#26`, a control on the wrong side of the
boundary. **RESOLVED in §12.2: the gate moves to the published file, integrated
is −16.0 ±1.0 LU, and true peak is a ≤ −1.5 dBTP ceiling rather than a band.**
*Left here as written on the day it was measured, with its own figures
(−16.5 / −5.2 for the assembled clip, −16.6..−16.7 for the four best delivered),
because §12.2 re-measured a single named file and got −16.7 / −5.1 from it — a
different file, not a contradiction. Overwriting the older measurement with the
newer one would have destroyed the range.*

### 12.1 Exit codes, and why a not-yet-built verb is not a usage error

Phase 0 had to choose a code for a verb that is declared but unbuilt, and the
choice is design rather than bookkeeping: it is the same distinction the
mentor ruling on `write_media` rests on, that a wrapper must not have to parse
message text to tell what happened.

| code | meaning | who sets it |
|---|---|---|
| **0** | success | — |
| **1** | a gate refused the work (blocking problems, a failed check) | the pipeline |
| **2** | **usage error** — an unknown verb, a missing verb, bad flags | `argparse` |
| **3** | **declared but not built** | the entry point |
| **4** | **refused on purpose** — `--test-fixture` content, a blocklisted source | `write_media` (V5) |

Three codes are worth defending over the other two.

**Why 3 is not 2.** A declared verb that is not built yet is not a typo, and
folding it into `argparse`'s 2 makes a legitimate request indistinguishable from
a misspelling. Every one of the five verbs currently exits 3, and a wrapper
branching on `2` versus `3` can tell "you mistyped" from "this is not written
yet" without reading `stderr`.

**Why 4 exists at all, when 1 looks like it would do.** It does not. `1` is the
code a *gate* uses, and a caller that treats every non-zero as "retry or
escalate" will retry a refusal that is a standing policy, not a transient
condition. `AC#26` was the case that forced this: the refusal is a deliberate,
permanent property of the input, so it gets a code that is not the failure code.
`write_media` raises `SystemExit(4)`, and **that is a number reserved before the
writer exists**, so V5 cannot quietly take 1 or 2.

**What this costs.** Three of these five codes are not reachable today: no code
returns 1, and 4 needs `write_media`. `0`, `2` and `3` are the only codes
exercised by the suite, and 12 tests cannot tell a reader that 1 and 4 mean what
this table says. **No code may be added to this table without a test that reaches
it**, which is the same rule §12's rows follow.

### 12.2 The caption decision, and the loudness band

Both were owner decisions in v010 and both are **RULED (mentor, 2026-09-28)**.
They are recorded here rather than in the changelog alone because each one
changes what `AC#30` measures.

**Captions are burned in.** Measured: a published MP4 carries **2 streams**
(`h264,video` + `mp3,audio`) and **no subtitle track**; **0** files in `src/`
contain burn-in, subtitle-mux, ASS/SSA or `drawtext`; and **0 of 14** produced
`.vtt` files contain a `::cue` or `STYLE` block. So the baseline produces a
caption file and attaches it to nothing, and the frame carries no glyphs for an
auditor to measure.

The ruling is burn-in rather than muxing a soft subtitle track, and the reason is
evidential: **the frame is the only artefact this project can inspect**, and
"rendered pixels" is the only evidence channel `AGENTS.md` grants
`graphic-reviewer`. A soft track stays outside every evidence channel here, which
is the same reason the two instruments could not fail in the first place. Soft
subtitles also leave the sound-off mobile viewer, which is the common case for a
tutorial.

**Cost, stated rather than buried:** this is a new render stage, and it must cross
**both** renderers — `pptx.py` and `slides.py` — which `AGENTS.md` records as
where a fix has silently missed the other one four times. It lands in **V5**, with
the rest of the render path, and it is the *first* thing to check when a
rendered frame shows captions on one output and not the other.

**Consequence:** `AC#30`'s instruments 1 and 2 are restored as pixel
measurements, and the two provisional rows in §12 (caption text-fit, panel
geometry) are **withdrawn** — they were placeholders for instruments that had
nothing to measure, and keeping them alongside the real ones would make §12 look
better-covered than it is.

**The loudness gate moves to the published file, and gets a stated band.**
`A18` reads the **pre-mux clip**. Re-measured 2026-09-28 on
`output/mod03_gates_v013.mp4`:

| point | integrated | true peak |
|---|---|---|
| published MP4 | **−16.7 LUFS** | **−5.1 dBFS** |
| pre-mux, per clip | −16.1 .. −16.0 LUFS | −1.5 dBTP |
| `config` target | −16.0 (`LOUDNESS_TARGET`) | −1.5 dBTP (`LOUDNESS_TP`) |

The published file sits **0.7 LU** below target, so a gate reading the other side
of the mux boundary is reading a different measurement than the one that ships —
**the same defect as `AC#26`, a control on the wrong side of the boundary.**
`A18` therefore moves to the published file, and the band is stated rather than
left implicit:

- integrated: **−16.0 ±1.0 LU**, so the measured −16.7 passes and a clip at
  −14.0 or −18.0 fails. The band is standard and is not a rubber stamp.
- true peak: a **ceiling of ≤ −1.5 dBTP, not a band.** Being quieter than the
  ceiling is not a defect, so a two-sided band would manufacture one. Measured
  −5.1, comfortably under.

Both targets stay env-overridable, which is why the *configured* value is not
sufficient evidence and the *measured* one is quoted above.

### 12.3 Enrichment when a step is missing: coverage, not invention

Asked directly — *if the source document does not contain a step, what does
enrichment do?* — and the baseline already has the right answer, written down in
`validate.py`'s own docstring:

> "The enrichment lever this exposes is **coverage, not invention**: on
> `mod03_gates_v012_013` four numbered concepts were used by no scene, and the
> only coverage check in the pipeline — `_topic_coverage_problem` — is a vocabulary
> test that cannot see them, because a skipped concept's words still appear in
> passing elsewhere."

**RULED, and it is three parts.**

**1. Enrichment never invents the missing step.** This is not a preference, it is
the baseline's stated position and `AC#19`'s existing rule ("no enrichment
fabricates a value on screen", all eight write sites named). A fabricated step
would be the worst possible outcome for this channel: it is on screen, it is
spoken by the narration, and it carries a `source_refs` stamp pointing at
something that does not say it.

**2. The mechanism is detection.** `_unclaimed_source_sections` reports the
document's sections that no scene *claimed*, judged by the assignment's own
record. The choice is **claim-based with no token-overlap fallback**, and the
docstring gives the measured reason: overlap cannot tell "mentions the word" from
"teaches the concept" — concept 4 ("Tolerance and the two units") scores **0.70**
overlap on the strength of the single word "tolerance", and **0.75** after
dropping every token appearing in more than half the scenes. An overlap fallback
would manufacture false negatives on exactly the borderline cases worth seeing.

**3. In this channel it becomes a GATE, and that is the change.** In the baseline
it is a `soft_finding` — it reports and never refuses, so a document with an
untaught step can still build and ship. For a channel whose only contract is
whether the lesson *lands*, coverage that cannot fail is coverage that will not.
So: **every numbered concept in the source must be claimed by a scene, or the
build refuses.**

**The consequence, which shapes the source document itself.** The detector
prefers the document's own numbered concept list and only falls back to
`_is_coverable_section` over inferred headings when it finds **fewer than 3**
numbered entries (`plan.py` matches `^\d+[.)]\s`). So the source document **must
carry a numbered concept list**, and a concept dropped from that list is a
concept the coverage check *cannot prove was taught* — it becomes invisible rather
than untaught. `sources/uv-getting-started.md` therefore carries **7** numbered
concepts against a `MIN_SCENES` of 5 and a `TARGET_MAX_SCENES` of 8: enough
material for a legal plan, and few enough that every entry can be claimed.

**Reported honestly:** this ruling tightens a gate the baseline left soft, so it
will find coverage failures the baseline would have shipped. That is the intent,
and the first build may well fail on it.

### 12.4 The session is a second artifact, and it breaks a constant

**The bar is different from an explainer, and the difference is measurable.** A
practical session must satisfy: *a learner who starts from the stated state and
follows only what is on screen reaches the stated end state.* Audited against
`sources/uv-getting-started.md` on 2026-09-28, the source document scores **5 of
8 gap classes present at all**, and **0 of 7 steps carry a failure path** while
**1 of 7 has no command**. It is a good explainer and a bad session script.

So there are now **two artifacts**, and conflating them is the cause of the gaps:

| artifact | job | provenance |
|---|---|---|
| **source document** | what the channel teaches | `[MEASURED]` / `[CITED]`, tagged per claim |
| **storyboard** | what the video shows, and what a learner can follow | an executable data file |

**The storyboard is the single source for two consumers** — the renderer and the
replay/learner-only harness. That is the whole reason it is data rather than
prose: a harness that parsed a transcript of the finished video would be testing
the transcription, not the video, which is the drift class §14 has now caught four
times. It lives at `storyboards/uv-install.storyboard.json`: **5 chapters, 15
steps**, of which **14 are replayable and 1 is not** — `install-uv`, because it
installs software and rewrites the shell profile, so re-running it would change the
machine under the test. It is exempt **with a stated reason**, and the loader
refuses an exemption that has none.

**The six-field step contract**, extending the existing `CommandClaim` rather than
inventing a second type:

| field | severity | why |
|---|---|---|
| `purpose` | blocking | a step with no reason is not memorable |
| `precondition` | blocking | this is what declares unshown state |
| `command` | blocking | render-blocking under reject-never-repair |
| `expected_output_pattern` | blocking | a **pattern**, never a literal: the cited docs reference `uv 0.12.19` while this box runs `0.12.2` |
| `state_change` | blocking | without it, directory drift is undetectable |
| `checkpoint` | blocking | "you should see this before continuing" |
| `common_failure` | **warning** | an undocumented failure costs one learner a session; repair-invention would put an unrun command on screen |

**Three checks ship, and each was shown a wrong input first.** Contract
completeness, elision (`...`, `<placeholder>`, `$VAR`, redaction markers), and
**unshown-state** — every path a command touches must be produced by an earlier
step, created by this one, or named in a precondition.

**The unshown-state check found three false alarms in its first run, and all three
were bugs in the check**, which is worth recording because two of them were
false *negatives* in a check whose only job is catching omissions:

- a trailing full stop became part of the token, so `Creates src/main.py.` yielded
  `src/main.py.` and the step that *creates* the file looked like it did not;
- `https://astral.sh/uv/install.sh` read as a local path `astral.sh/uv/install.sh`,
  reporting every install step as depending on a nonexistent file;
- `expected_output_pattern` was scanned for paths that must pre-exist, but it is
  what a step **prints** — so every checkpoint was reported as an unshown
  dependency, and a checkpoint's job is precisely to name a path the learner
  should now see.

**Four mutations are permanent tests**, because a validator that has only ever been
shown a true statement is untested: removing the step that creates `src/main.py`
(which is the exact defect the source document shipped with), blanking a command,
eliding a command, and stripping a `replay_skip_reason`. All four are caught.

**The constant this breaks.** 3–5 minutes per chapter across 5 chapters is
**15–25 minutes**. This design was built around a 4-minute video with
`MIN_SCENES = 5` and `TARGET_MAX_SCENES = 8`, and **an install session with a
prerequisites card, a checkpoint per step and a failure scene does not fit that
budget** — not marginally. **Chaptered mode becomes the delivery shape**, and
`TARGET_MINUTES` and the scene budget change with it. That is a live open item,
stated here rather than discovered at V4 when `plan_lesson` refuses a legal-looking
plan. *The scene budget is per **chapter**, not per video.*

**The interpreter download, now measured.** A first-time learner pays a wait and
**111 MB** (`~/.local/share/uv/python` measures 111M, containing
`cpython-3.12.13-linux-x86_64-gnu`). This machine's copy has mtime **2026-08-13**,
46 days before the session was written, so **the recorded run downloaded nothing** —
which is exactly why an unmeasured claim about it would have been false. The wait is
therefore shown honestly in the storyboard's `state_change` rather than silently
sped up.

### 12.5 Chaptered mode is the delivery shape (RULED, mentor, 2026-09-28)

**The constant this breaks, measured.** A practical session at 3–5 minutes per
chapter across 5 chapters is **15–25 minutes**. This design was built around a
4-minute video with `MIN_SCENES = 5` and `TARGET_MAX_SCENES = 8`, and an install
session with a prerequisites card, a checkpoint per step and a failure scene does
not fit that budget — not marginally, and not by tuning. Five minutes is roughly
**four spoken commands plus a checkpoint and a pause**; the `uv` storyboard's first
chapter alone is four steps with three checkpoints.

**RULED: the video is delivered in chapters, and the budget is per chapter.**

| | was | is |
|---|---|---|
| delivery unit | one video, ~4 min | **a chapter**, 3–5 min |
| total length | ~4 min | **15–25 min** across 5 chapters |
| `MIN_SCENES` / `TARGET_MAX_SCENES` | per video | **per chapter** |
| `TARGET_MINUTES` | per video | **per chapter** (~4), and the sum is the total |
| `source_sections` coverage | per video | **per chapter** |

**A chapter is a standalone unit and must work alone.** It states its **start
state** at the top, and the learner can begin there without having watched the
previous one. That is a hard requirement, not a convenience: a learner who
arrives at chapter 3 from a search result has not seen chapters 1 and 2, and a
chapter that assumes otherwise has a gap the coverage machinery cannot see — the
`start_state` is the declaration that closes it, and it is the field
`_unclaimed_source_sections` has no opinion about.

**The five `uv` chapters are fixed by the storyboard**, and each maps to one
delivery unit: install and verify, first project, add dependencies, lock and sync,
run and `--with`.

**Three consequences that are easy to miss.**

1. **Coverage becomes per chapter, and so does the gate that now enforces it.** The
   §12.3 ruling — every numbered concept claimed or the build refuses — is applied
   **per chapter**. A 5-scene chapter that draws on 7 numbered concepts cannot
   claim all 7, so the source document's concept list is partitioned across
   chapters, and the storyboard's `start_state` is where the partition is recorded.
2. **`AC#30`'s instruments become per chapter.** Loudness, caption geometry and the
   word-boundary check are measured on each chapter's own artefact, and the
   published file for the gate is the chapter's MP4. A gate reading a concatenation
   would be a control on the wrong side of a boundary in exactly the way `A18` was
   (see §12.2).
3. **The cheat-sheet card and the chapter marker are load-bearing, not polish.** A
   learner who joins at chapter 4 has no list of the commands from chapters 1–3, and
   the session's promise — *follow only what is on screen and reach the stated end
   state* — is only checkable per chapter if the chapter says where it begins.

**What was deliberately NOT changed.** `MIN_SCENES` stays at 5 rather than dropping
to 2 or 3 for a short chapter. A 3-scene chapter is a prerequisites card, one
command and a checkpoint, and the honest minimum for "a learner can tell whether it
worked" is five distinct beats. Lowering it to make a chapter fit would be tuning
the gate to the artefact, which is the same error as widening a tolerance to absorb
a mux (see §12.2).

**Honest limitation:** this ruling changes the shape of the deliverable and the
meaning of two constants. It does **not** re-measure the gate's own behaviour
against a 25-minute plan, because no render has been produced at the new size. The
first chapter render is the measurement, and if the scene budget or the duration
estimator is wrong at this scale, that render will say so.

### 12.6 The repeat gate protects commands, not prose (RULED, mentor, 2026-09-28)

This is finding **F1** from the V-1 spike, and it blocked any real video until now.

**The conflict, measured.** Instrument 4 of `AC#30` requires the narration to
**name the command on screen**. The repeat gate forbids a repeated 3-word phrase.
Naming `uv --version` three times, as a three-scene chapter must, produces three
repeated 3-grams: `run uv dash` ×3, `uv dash dash` ×3, `dash dash version` ×3 —
**confirmed against the real gate, not reasoned about.**

Satisfying the gate instead produced *"try that same check once more"*, which a
learner **listening** rather than looking cannot act on. The gate was right that the
prose repeated and wrong about what to do about it: it was protecting the one
repetition a follow-along video is *required* to make.

**RULED: a command the storyboard declares on screen is protected terminology, and
the repeat gate continues to govern the prose around it.**

The mechanism is `spoken_command_trigrams`, in `storyboard.py`, and it feeds the
plan's existing `protected_trigrams` — the same channel source-derived terminology
already uses. Three properties make it correct rather than convenient:

1. **A flag is spelled the way TTS says it.** `--version` becomes
   `dash dash version`, so the protected span matches the *narration* being gated.
   A string search over the command would protect `uv --version` while the text
   under examination is `uv, dash, dash, version`, and the two never match. This is
   why the mechanism is a tokeniser and not a search.
2. **It derives from a declaration.** The commands come from the storyboard, so the
   protection is a claim a human can falsify by reading — the same discipline that
   replaced the `creates_indirectly` inference (§12.4).
3. **It is narrow.** Only trigrams **inside** a command's spoken span are protected.
   A window straddling the command/prose boundary is **not**, and measured: with the
   protection in place the gate went from **3 findings to 1**, and the survivor was
   `dash version and` — real prose repetition, because two sentences both said
   "and" after the command. Varying that connective cleared it. **The gate kept
   catching prose repetition, which is the behaviour it is for.**

**Proof it is load-bearing**, against the real gate with a five-scene fixture:
without the protection, narration naming a command three times is **refused** (2
banned phrases plus an unrepairable repeat); with it, the same narration **passes**.
Both directions are permanent tests, and the test filters to the repeat gate's own
findings — asserting on the whole gate would have failed for two unrelated
`transition-only` findings and proved nothing about this mechanism.

**Related, and why F1 could not be worked around instead.** `A43`: the
baseline's `_entity_tokens` does not recognise short lowercase tool names. `uv`,
`curl`, `astral`, `uvx`, `sh` and `bash` are **all** absent from the recognised set
while `0.12.2` and `~/.local/bin/uv` are present — so the term a `uv` tutorial
repeats most gets no protection from the mechanism that exists to protect
terminology. Fixing that would be necessary and **is not sufficient**: the surviving
`dash version and` contained no tool name at all. Both changes are needed, and only
this one was available to us.

**What this does not settle.** The narration-versus-screen instrument itself remains
**unbuilt**, and that is now a recorded decision rather than an omission. Three
mechanical versions were tried on the V-1 spike and the first two were wrong: a
hardcoded "must say `uv`" failed because the install scene correctly names `curl`, and
a full-token comparison failed because *"Astral's installer"* **is** speaking a URL.
The third still reports false failures, because the narration says *"capital L, small
s"* and *"dash, l, c"* — which **is** speaking `-LsSf` and `-lc`. A token comparison
cannot know that a spelled-out flag is the flag. So the instrument needs a
spelling-aware normaliser or a human, and until one exists `AC#30` instrument 4 is
verified **by hand, for 4 of 5 scenes**, and the baseline is right to treat it as a
`soft_finding`.

## 13. Acceptance criteria

1. `doc-to-video-channel --help` prints usage listing all five declared verbs and
   **exits 0**. **Now met** (measured 2026-09-28): it exits 0 and its usage names
   `build`, `review`, `tts-check`, `verify`, `render`. *It was false when written:
   the stub ignored `argv`, so `--help` printed "Hello from
   doc-to-video-channel!", an unknown verb **exited 0**, and bare invocation
   **exited 0** — a silent zero. The gate could not see any of this, because
   `ruff` and `mypy` do not know a CLI contract.*
2. `ruff check src tests`, `mypy src` and `pytest` are all configured and all pass
   — and `pytest` collects more than zero tests. The type gate is `mypy src` by
   decision; the vendored tests sit outside it deliberately (§5.4). **Now met**,
   measured 2026-09-28 as **exit 0, 12 tests passed, 100% of 19 statements and 2
   branches**. *It was false when written: there was no `tests/` directory, so
   `ruff` exited 1 with `E902` and `pytest` reported `no tests collected`.*

   **The gate was then shown to be capable of failing, in both directions.** Each
   tool was fed a violation it is configured to see: `ruff` an unused import,
   `mypy` an untyped `def` under `src/`, `pytest` an `assert 1 == 2` in a
   `test_*.py`. All three reported it. The first attempt at this check was itself
   wrong and is worth recording: the file was named `_teeth_check.py`, which
   matches neither mypy's nor pytest's discovery, so **two of the three tools
   reported success over a file that had not been read at all** — a green gate
   over an unexamined file, which is the exact failure class of §1.

   **`mypy src` is kept, and the gap it leaves is deliberate.** Measured: `mypy
   tests` reports **0 errors on the channel's own tests** while the same command
   reports **2 errors** in a deliberately-broken one, so the tests here are typed
   and stay typed. But the vendored seven carry **74 errors in 7 files** (§5.4),
   so widening the gate to `tests` would buy 6 of those 7 files' worth of signal
   today and **break at V6**. The 0/74 split is recorded so that, when V6 lands,
   the new number is attributable to the vendored files alone.
3. A fresh clone resolves with `uv sync` and runs the gate.
4. Two `TopicProfile` values produce two different scene plans from one source.
5. **The behavioural differential passes**: a defaults-only profile reproduces
   **the frozen copy at `VENDOR_REF`, pre-seam** — its normalised `plan.json`, both
   renderers' output, and `*.verify.json`. *Measured constraint: the seam's purpose
   is to collapse the two spellings of a section label, so post-seam output cannot
   equal pre-seam output. The differential is therefore against the frozen
   reference, and `AC#8` owns the spelling change.*
   **This requires the two §5.6 fixtures, and §5.6's precondition: a fixture that
   produces a *passing* plan, plus the narration-digest falsifier re-run and
   passing.** Without that, what the differential proves is the determinism of the
   *repair* path, not the success path.
6. **A Devanagari `section` is rejected by `SlideScene`, and a Latin one is not** —
   both directions, through `model_validate(..., context=...)`.
7. **One entry point: `doc_to_video_channel.main(argv)`.** The copy carries no
   second door — `__main__.py` is **dropped** (§5.1 row 19) and the deprecated shim
   is **not copied** (row 17). Proven by a reachability test over the entry points
   actually present.
8. **`SectionKind` is a type and the schema enforces it.** The two-spelling defect
   is closed: `"What Is This?"` (with the question mark) is **rejected** by
   `SlideScene`, and an AST check fails if a known label literal appears in either
   renderer. Neither renderer owns a title string.
9. `A6` yields a `source_chunk` on **6 of 6** scenes for a prose source.
10. An unsupported input file is refused at the door, **before any model call**,
    and an **excluded** path with a valid extension produces the *rights* message,
    not the format message.
11. A clip at −22.3 LUFS fails the `A18` gate, against a **stated target and
    tolerance**. A recording with no `WordBoundary` fails the caption gate on zero
    cues.
12. `--audio-dir` accepts exactly `clip_count(N)` files and copies them.
13. **The provenance gate is invoked at all four** `_render_blocking_problems` call
    sites, and **every finding it emits is blocking** — classified at the hook as a
    typed result and rendered with the `RENDER-BLOCKING: ` prefix.
14. `verify.json` publishes `command_provenance` as **id lists** over the
    **pre-drop** population: `presented`, `issued`, `admitted`, `dropped`, and
    `claims[]`. **A zero-population publish fails** — `presented >= 1` whenever the
    plan shows a command.
15. **A witness manifest exists, and every row in §12 has an entry in it**: test id,
    wrong input, the assertion that failed, and the recorded output.
16. **`TopicProfile` has no `decision_prompt_rule` field** — and the check is
    **structural** (`dataclasses.fields`), not a grep, because a grep cannot fail
    here. Currently true over a 66-byte file and therefore **vacuous until
    `profile.py` exists**; it becomes falsifiable at V7.
17. **The adapter never truncates silently, and never truncates in a way that
    wastes the window it was given.** Two properties, two owners, two witnesses.

    **(a) the boundary property — a V1 criterion, no reader required.**
    `_truncate_on_boundary` lives in `util.py` and operates on a `str`: the joined
    text, *after* `load_documents` has wrapped each file in `<doc name='…'>`. It
    **never sees a `.docx`**, so a synthetic oversized source exercises it exactly.
    The wrong input is a source built to break it: a body with no line break and no
    space, a body of one unbroken token, and a source whose only section heading
    falls just past the half-window mark. *Measured over 7 such sources: 0 split a
    token.* Assert the cut never ends mid-token **and** that
    `chars_read / read_window >= 0.5` — the invariant the docstring states and
    never asserts.

    **The second clause is the one with teeth.** Measured: a boundary-free body of
    40,038 characters is cut to **30 characters — 0.25% of a 12,000-char window** —
    because the last space in the window is the one inside the `<doc name='…'>`
    wrapper header, so the whole body is discarded while the window sits unused. A
    **1,334.6x** drop, on demand, from a synthetic source. The 18-document corpus
    never reaches it: it uses 99.9–100% of the window.

    **(b) the corpus figure — the reader's job, and the reason `AC#17` exists.**
    A golden check over the 18-document corpus pins the
    **post-`_truncate_on_boundary`** admitted count, not the document-level count,
    because a golden file storing the document-level number passes while the
    pipeline's number is wrong. **Unblocked at V1**, which carries `A5` (see the V1 row), and checkable there
    carries it. What is measurable today, without the reader, is in §14.6.
18. **The drop column is enforced, over a stated population.** Row 17's symbols
    **excluding `main`** (6: `TUTOR_PROMPT`, `generate_lesson`, `text_to_audio`,
    `_split_sections`, `_make_slide_image`, `create_video`), row 18's **5**
    re-exports, and row 19's `__main__` module — **12 in all.** *v008 said 11; 6+5+1
    is 12, and its falsifier ("fails when a twelfth name appears") therefore fired
    on a legitimate member — a test built to that criterion produces a false red.*
    The check is **structural** over the module list, and must be shown to fail
    when a **thirteenth** name appears. **`main` is deliberately excluded**,
    because an earlier draft included it and that made this criterion contradict
    `AC#7`.
19. **No enrichment fabricates a value on screen — all eight write sites, named.**
    The eight, so the criterion has a closed population rather than a count:
    `visual_diagram` ×4 in `_ensure_technical_visuals`; `code_context` ×3 in the
    same function; `json_snippet` ×1 in `_populate_concrete_values`. A document
    containing the trigger key names produces **no** path. The `json_snippet` branch
    and its regex are deleted and the existing test is **rewritten with it**, not
    deleted: its first assertion counts the branch firing, so deleting the branch
    fails it at `assert 0 == 1` (measured). *v008 said "all eight" and enumerated
    none, so §12's witness covered 1 of 8 and read as complete.*
20. **No filler under the COMMAND CONTEXT panel in video one**, and the three
    `code_context` sentences are **derived from the source span** `A32` binds, not
    written.
21. **Narration determinism**: varying only the narration response changes the
    **narration digest**, and the stub varies within a run. This is the §5.6
    precondition as a criterion, and it is currently the one check known to be
    structurally blind.
22. **`presented` is counted from the raw model response**, and the injection
    falsifier attacks the derivation that would actually vacate the equation. One
    invented command, injected before any pass runs, raises `presented` by 1 and
    `dropped` by 1, and the injected id appears in the `presented` list. **This
    criterion also requires a named producer for `presented`** — nothing writes it
    yet, and a criterion with no producer is a sentence.
23. **The two equations hold and can fail**: a candidate deleted after issuance
    without a recorded drop breaks reconciliation; a command rendered outside the
    admitted set breaks the render assertion.
24. **A `negative`-polarity claim cannot be rendered.** A command quoted verbatim
    inside a "do not do this" example satisfies "appears verbatim" and must be
    refused.
25. **The fixture bit refuses every egress.** A `--test-fixture` build loads and
    parses, and any model call, any TTS call, and any media write **refuse**.
26. **The fixture stamp is load-bearing, and the media writer is what reads it.**
    The bit reaches the media's own manifest alongside `vendor_ref` (§6.3), and
    `write_media` — the single chokepoint §8.3 creates at **V5**, reached by
    **both** `_render_media` call sites — **refuses** a `fixture: true` artefact and
    exits **2**, distinct from the **1** that already means "gated". *Witness: a
    manifest carrying `fixture: true` must be refused, and the same manifest with
    the bit false must be written.* `publish` as a subcommand was named in v008 and
    v009 and is **withdrawn** — it would gate neither `build` nor `render`.
    `REQUIREMENTS.md` §4's seven human checks are **referenced, not enforced**.
27. **A content-hash blocklist refuses an unexcluded copy.** A source whose md5 is
    on the 18-hash list, at a path the allow-list does not exclude, is refused —
    which is the case a path-only allow-list passes.
28. **The egress inventory is closed against an independent enumeration.** The
    population is **not** §8.3's table — a check whose population is the table under
    test is satisfiable by writing the table, which is what v008's version was.
    The population is: every network primitive and every media write in the 16
    copied modules of §5.1, enumerated by AST. Measured today that is **2 egress
    sites** (`llm._ask_llm_stable`; `video.py`'s TTS call via `synth_scenes`) and
    **≥7 media write sites across 4 modules**, with **no media writer to chokepoint**
    — so the inventory must also assert that a writer now exists. A chokepoint
    reached with the fixture bit set must refuse.
29. **Every practical scene carries purpose, action, expected result and recovery**,
    and the environment manifest names target OS, shell, version policy,
    prerequisites and source freshness.
30. **The V-1 spike has been run and its four measurements recorded**, with the
    caption gate reading the **published** file and the loudness band the stated
    ±1.0 LU / ≤−1.5 dBTP (§12.2): minimum
    caption glyph height at 720p, **disjoint** caption and command-panel bounding
    boxes, `ebur128` within the `A18` target ± a stated tolerance, and a narration
    transcript containing the tool name with a matching `WordBoundary` token.
    **This is the first moment the design has been exercised at all**, and §5.4's
    V0–V6 does not begin until it has. *v008's four adjectives — legible, clear,
    intelligible, pronounced — had no instrument and could not fail, and this is
    §13.1's condition 6, so the stop rule was gated on a criterion that could not
    fail.*
31. **The brand string is changed and checked in a render**: one scene rendered,
    frames sampled, old string absent and new present.
32. **The vendored tests are not silently skipped**: the collection report shows the
    expected count **and** the run count.
33. **`vendor_manifest.json` exists**, its hashes match the tree, and the closure
    claim in §5.1 is stated **relative to `VENDOR_REF`** rather than absolutely.

### 13.1 When to stop reviewing this document

Six internal rounds and two external reviews have produced 34 and then 12 more
defects, most of them about the document rather than the design. The stop
condition, adopted from the second external review:

```
1a  every must-have criterion names a CONCRETE witness -- a test id, a file, a
    command, or a literal.  (This is a spec-completeness gate.)
1b  every named witness has been EXECUTED and its output recorded.  (This is an
    execution gate, and it is V7 work.)
2   every blocker has an owner, an implementation location and a failure behaviour
3   every number a report publishes has a defined population and an immutable source
4   every pipeline stage has an input, an output and a failure state
5   the first end-to-end fixture is selected
6   no open decision blocks the first vertical slice
```

**v008 conflated 1a and 1b, and that is the unsatisfiable form**: a gate that
terminates the document review cannot be one that only running code can satisfy.
**Document review is gated on 1a and 2–6. 1b is a V7 condition, not a
document-review condition.**

**1a was nearly met and was not met.** As of v010: `AC#3` ("the gate" names no
command), `AC#7` (no reachability row), `AC#33`'s third clause (satisfied by prose
that already exists, so it cannot fail). *`AC#17`'s row and `AC#26`'s `publish`
subcommand are now closed — `AC#17` split into (a), which V1 owns on a synthetic
source, and (b), which V1 also owns now that `A5` is placed there; `publish` was
withdrawn and its control moved to `write_media`. Both were open when the review
that produced this paragraph was written, and leaving the paragraph claiming they
were open would be the review citing its own correction as pre-existing — the
second time in this file.*

**Condition 6 is `AC#30`, and `AC#30` had no falsifier** — which the round-7
reviewer found by observing that §12's V-1 row's witness cell was a verbatim copy
of its approach cell. It has four instruments now (§5.4).

**Drift exposure is larger than v008 said.** §15 recorded "roughly 30 claims"
measured against the reference tree; an independent enumeration lists **40+**, in
ten groups. The reference is a **full local clone with 66 commits and `origin`
configured**, so every one is re-derivable offline today by a command — which is
why "there is no mechanism that would notice" over-claims the constraint. **There
is no CI job; there is a clone and a command, and nothing runs them on a schedule.**

**What is already true of condition 3**, and should be preserved deliberately:
§5.1's per-row populations, §6.5's two equations, §8.4's three measured corpus
populations, and §5.6's four-population refusal are all stated with a basis, and
none of them is a bare total.


## 14. Decisions

**Eight decisions are ruled (2026-09-28): §14.1–§14.7 from the owner, plus §14.8
which is upstream of this project and is the only one still needing an action
elsewhere.** Nothing in this section is open.

### 14.1 Where the seam lives — RULED: the channel

The baseline is a reference, not a dependency. The pipeline is vendored, so §4's
five field types and the `_extra_gates` hook are edits to files this package owns.
The earlier text here — that the seam *"cannot be implemented channel-side"* — was
true only while a dependency was proposed, and is withdrawn with it.

**Carried into vendoring:** every measurement quoted from the baseline must be
**re-measured after the copy lands**, because the copy is the code that will run.
**And the closure claim is reworded:** §5.1 is a closed population **relative to
`VENDOR_REF`**, not an absolute one, and `vendor_manifest.json` records what was
taken and what was left. There is no drift detector, and this document does not
claim one.

**One earlier open question is ruled by this ruling:** the size of the `A33`
population. **v007 said "7 sites in one document" and v008 published "24 across 6
files" — and both were wrong.** Measured 2026-09-28: `grep -rn A33 docs/` returns
**33 across 7 files**, of which the design records are **22 across 5**
(`LLD-tutorial-lane.md` 18, and 1 each in `DECISIONS.md`, `PLAN.md`, `RIGHTS.md` and
`PLAN-tutorial-lane.md`); the other 11 are in the two review triages and the
outbound summary. v008's own breakdown summed to 20 and named a sixth file holding
none. **The population is 22 / 5 for design records, 33 / 7 including the review
artefacts, and which one is meant must be stated at the point of use.**

### 14.2 `A33` vs the source allow-list — RULED: `A41` is a new row, not a rename

**This was mis-framed as a rename, and the distinction changes the work.** Three
measured facts settle it:

1. **`A33` is correctly defined.** `DECISIONS.md` §1: *"Corpus excluded from
   publication; the publishable source is the owner's own notes."* No allow-list.
2. **`PLAN.md` §7 is the error** — its table redefines the ID rather than citing it.
3. **The decisive fact: `FR-028` has 0 hits in `DECISIONS.md`.** The allow-list
   gate has **no ledger row at all**. It never lived under `A33`'s number, so
   `A41` is a **net addition**, not a renumbering.

**Disposition.** `A33` keeps its meaning. `A41` is **created** as a new ledger row
— *"source allow-list — a build whose source resolves inside an excluded path fails
loudly; `--test-fixture` stamps the plan non-publishable"* — placed beside `A40`
(rows are priority-ordered, not numeric). `PLAN.md` §7 changes **one cell**,
`A33` → `A41`. That is the entire fix.

**No tombstone.** The `A31` precedent exists because a **second ledger** reused a
number; here the reuse is a wrong cell in one table in the same repo, and
`DECISIONS.md` is unambiguous. A tombstone for a typo is ceremony. **The provenance
worry is moot twice over:** 0 code comments, 0 test names, 0 audit artifacts cite
`A33`, and this repository has **0 commits**, so there is no history to break.

**One collision to name in the commit message:** `PLAN.md` §7 **already lists
`A34`**. An editor choosing "the number after `A33`" by reading that table downward
would pick `A34` — the exact collision this item exists to prevent.

### 14.3 The `json_snippet` fabrication — RULED: delete, and re-rank the eight sites

`_populate_concrete_values` fires a three-name literal regex
(`{schema_version, baseline_id, path}`) and writes
`{"schema_version": 1, "baseline_id": "v1.2.0", "path": "eval/baselines/v1.2.0.json"}`
**without reading the match.** Its own docstring claims these blocks *"can never
invent a fact"*. The one function whose purpose is preventing invention is the one
inventing.

**Delete the branch and the regex; do not build a guard.** A field would be opt-in
and the only value anyone would ever write is `False`. There is no honest version
of this enrichment: the match carries **key names and nothing else** — no values,
no version, no path — so it cannot be made source-grounded.

**What the test does with the fabrication, measured both ways — because v005 and
v006 each stated half of this, and each half is true of a *different* change.**
`test_concrete_values_population_is_source_grounded` asserts a **change count**
(`1` on the first call, `0` on the second) and two **key names**. It never
inspects a **value**. So:

| change | result |
|---|---|
| remove the fabricated **values**, keep the branch and the key extraction | test **passes** (measured) |
| **delete the branch**, which is what `AC#19` mandates | test **fails** at its first assertion, `assert 0 == 1` (measured) — the count becomes 0 because the enrichment never fires |

**So `AC#19`'s instruction is right, and this section was wrong to say the test
"keeps passing".** Deleting the branch deletes the behaviour the test counts.
**The count assertion must be updated as part of the deletion** — it then becomes
a witness that the branch is *gone*, which is a better test than the one it
replaces. What must not happen is deleting the test: the trigger coverage is the
only thing asserting the branch existed at all. *v005's AC#17 instruction to
"update or delete it with" the payload would have removed that coverage for
nothing.*

**The ranking inverts for this lane, and that is the actionable part.** Measured over
all 18 corpus documents: **0 contain the fabrication's trigger tokens**, so
`json_snippet` **never fires on our lane** and is the *least* urgent of the eight
sites in AC#19. The **three `code_context` sentences are the most urgent**, because
they fire on the first video. Run against our own commands, 5 of 6 get
*"Use this documented command in the lesson workflow."*, and `uv sync` gets a
sentence asserting *"the locked environment"* and *"the suite"* — words a `uv
install` tutorial never uses — under the panel the renderer labels
`COMMAND CONTEXT`, in a video whose entire value is the commands.

**The defect class there is not fabrication but filler under a label that promises
explanation**, so "delete the write" is not the fix either. `code_context` must be
**derived from the source span the command was verified against** — the same span
`A32` binds, so it is free once `A22`/`A32` land.

### 14.4 Publish `.docx`? — RULED: no. Wire the parser, do not announce it

Measured: `.docx` appears **0 times** in the baseline's `src/`, and the only format
claim is one argparse help string naming `.md, .txt, .pptx`. **There is nothing to
un-publish.**

A published format is a support commitment — every user who sends a Word doc
becomes a bug report about fonts, tracked changes and embedded objects. So the
parser ships and the format stays out of the README's supported list and out of any
error message naming accepted formats. That allows promotion later without a
migration, which un-publishing an announced format would not.

**This is a constraint on `A15`'s implementation, and it strengthens `A15`.** A
`.rtf` whose bytes decode as UTF-8 **loads silently** (measured: 103 chars, no
exception, no refusal), while a `.docx` — a zip — raises `UnicodeDecodeError`
*after* the LLM call. The defect is not "`.docx` crashes"; it is **"the input set is
unbounded and defined by an accident of encoding."** The allowlist is a
**correctness gate**. See §5.2.

### 14.5 Rights exclusion vs format failure — RULED: separate, and give it a shape

`A15`'s ledger row contains **no rights dimension at all**; it is purely *"allow-list
the supported extensions and `raise` on anything else, at the door."* The rights
exclusion is already separately specified, by `RIGHTS.md` §0 (*"read on this
machine, **never uploaded** … `FR-028` makes the build enforce it"*), §1, and
`A33`. **So this is a confirmation, not a change** — the two were never merged.

They must not be, and the reason is operational. A format failure is an engineering
defect: fix and re-run. A rights exclusion is a policy decision: **retrying is
wrong**, and overriding needs an audit trail. Shared code means a retry loop retries
a rights block, and a rights block counted in the format-failure rate makes parser
quality look worse than it is.

**So the policy needs a code shape, or a rights refusal inherits whatever retry and
suppression semantics the format arm carries:**

```
class AdapterError(Exception): ...               # one CLI except-arm
class UnsupportedFormatError(AdapterError): ...  # A15  — retryable
class SourceExcludedError(AdapterError): ...     # A41  — non-retryable, and not
                                                #   suppressible by the flags
                                                #   that suppress format warnings
```

### 14.6 The `.docx` corpus — RULED: adopt, with the population corrected

**The population is 18 unique documents, not 30 paths.** Measured by md5: 30 files
resolve to **18** unique hashes, because six are byte-identical copies sitting in
two **sibling** repositories outside this project's scope. "All 30 open with 0
failures" was 18 checks run 30 times. `RIGHTS.md`, `A33`, `A15` and `PLAN.md` all
say 18 — **this document was the lone outlier.**

**Canonical root: `rag-apidriven-pipeline/data/transcripts/`, 18 files.** The
duplicates in the sibling trees are left alone.

**"Opens without raising" is a low bar** — it shows the parser does not crash, not
that it extracts the right text, and silent truncation passes it. So a golden-output
check is required, and **it must pin the post-`_truncate_on_boundary` admitted
count**, not the document-level count. A golden file storing the
document-level number passes while the pipeline's number is wrong. **AC#17.**

**How far apart the two counts are: measured 2026-09-28, and the reason v007 and
v008 gave for not measuring it was wrong.** Both said the ratio was unmeasurable
*because the reader `A5` has not built*. It is not: `_truncate_on_boundary` takes a
`str` — the joined text, after `load_documents` has wrapped each file in
`<doc name='…'>` — and **never sees a `.docx`**, so the corpus is measurable today
with `python-docx` (already a declared dependency) and the vendored truncation
function, with no reader built.

Measured over the 18 unique documents — **all 18 truncate**:

| | |
|---|---|
| per document, `chars_total / chars_read` | **9.23 – 13.83x** (population: 18 documents) |
| aggregate, `sum(chars_total) / sum(chars_read)` | **2,425,201 / 215,924 = 11.23x** (population: the same 18 **summed** — a different population from the range, not a second reading of it) |
| share of characters dropped | **89.2 – 92.8%** |
| read window used | **11,990 – 11,999 of 12,000** |

**The earlier drafts conflated two measurements: 90 is the percentage dropped, 11.2
is the ratio.** v007's *"up to 90x"* is out of range by about 6.5x — a percentage
published as a multiplier. v008's *"9.5x" **sits inside the measured range** and is
a real value for a real document; what was wrong with it was that it named no
population, so **it is not withdrawn.** v009's claim that *"both earlier drafts were
wrong"* was **half wrong**, and saying both were is the error this paragraph exists
to avoid.

**What remains unmeasurable is narrower: the *pipeline's* admitted count over the
corpus.** `load_documents` cannot open a `.docx` — it raises `UnicodeDecodeError` —
so what is pinned above is what the truncation *function* does to these documents,
not what a `load_documents` call *reports*. `AC#17`(b) closes that gap.

**Two facts that kill competing ratios rather than qualifying this one:** all 18
files carry **0 tables** and **0** header/footer parts, so paragraph extraction is
*exact* for this corpus rather than a lower bound; and **0 of the 18 carry a single
`##` heading**, so a *concept*-level ratio is undefined here.

**Out of published artifacts — and now enforced rather than merely true.** Neither
`pyproject.toml` has a `[tool.uv.build*]` section, so the default `src/` layout
governs and a `tests/fixtures/` corpus would not ship; the channel has **no
`.github/` at all**. But "would not ship" is a property of the *current* build
configuration, and it is not the property that matters. §8.4 makes the corpus
**referenced by external path, gitignored, with synthetic `.docx` for CI** — so
§0's *"read on this machine, never uploaded, never narrated into a video, never
published"* holds of the
**repository** and not only of this machine. This settles the question left open in
the open question external review 1 raised: the reader and the corpus are kept apart for exactly this
reason, and a path allow-list alone was never enough (12 of the 30 paths are
duplicates outside the excluded path).

**What the corpus cannot witness.** It contains **0 tables** across all 18
documents, so a `python-docx` table path would be code with no fixture — the
`python-docx`-declared-but-unimported mistake again. And with 0 of 18 containing
the fabrication's trigger tokens, **the golden check cannot witness AC#19**
(§14.3). Those links do not exist; do not write tests asserting them.

### 14.7 Drop the `studio/__init__.py` façade — RULED: moot, and the caveat is closed

**There is no façade to drop.** §5 creates **no** `studio/` subpackage: its 16
modules sit at the package root, and the two façades are **excluded by §5.1**
(rows 17–19), not deleted by a decision. §5.1 row 18 records why — the re-exports
are 5 of the 39 and each carries `# noqa: F401`, a suppression that would hide a
*second* binding of exactly the constants §4 exists to reach.

The namespace-package caveat was **measured, not deferred**: a regular package with
a subdirectory carrying no `__init__.py` imports correctly from the source tree,
from site-packages, and via `python -m`, and `uv_build` puts the module in the
wheel. **The "empty `__init__.py` if in doubt" fallback is unnecessary for this
backend**; keep it only as a backend-change contingency.

**One correction to the figure this decision was argued on, and it is the
opposite one.** The private names the tests reach do **not** travel through the
façade at all — measured 0, against 11 module-name exports. The `48` quoted in two
earlier drafts of this document was never reproducible, and §5.1 has deleted it;
that deletion stands. `studio/__main__.py` is confirmed to be exactly the façade
re-export `from doc_to_video_tutor.studio import main`.

**This discharges one of §2's seven unowned sites** — legitimately, by not copying
the file. Recorded as a resolution, or the site stays open forever against a file
this package will never contain.

### 14.8 The `moviepy` floor — RULED: declare the **exercised** version

The baseline declares `>=1.0.3`, and the copy's only moviepy import is a top-level
`from moviepy import (...)` that resolves only under moviepy 2.x's layout. **The
channel's own floor is the problem:** it declares `>=2.2.1` — 2.2.1 exists and is
current — and **no code in either tree has ever run against it**. The only
exercised version anywhere is **2.1.2**.

So this package would open with the renderer moved by a minor version with **no
test, no build and no measurement behind it**, and the LLD called that
"unaffected". **It is the same defect as the one this item exists to report, with
the defect and the fix exchanged between the two projects** — a declared floor
nobody exercised.

**Fix:** set the floor at the **exercised** version (`>=2.1.2`), not the latest, and
add an import probe at the door that fails by name. That is `A18`'s existing shape
and costs three lines. *Upstream of this project and not its to make, so it stays
the one open item.*


## 15. What changed, by round

**v008 — two external reviews, applied as one change.** Triaged in
**two external reviews** (8 adopt / 4 modify / 4 reject / 9 already present, and
12 adopt / 5 modify / 2 reject / 10 already present). Their triages were transient
and are now folded into this section, so the files no longer exist. Both
were applied together so the document is not reviewed twice for the same edit.
**Acceptance criteria 17 → 33; §12 rows 16 → 31.**

**Three design changes, and each supersedes something v007 got wrong:**

- **Section kinds are a type, not a string** (§4.3). v007's `SectionPolicy` was
  still string-based, which is *why* one label reaches the artifact under two
  spellings and why a fix landed in one renderer and not the other. A
  `SectionKind` enum with one `label_for` accessor makes "fixed in one renderer,
  missed the other" *unrepresentable* rather than reviewed. **`decision_prompt_rule`
  is deleted**, and `voice` keeps only what is spoken.
- **`presented` is counted from the raw model response** (§6.5). v007's equation
  `issued + dropped == presented` **can be an identity** — if `presented` is
  computed as `issued − dropped`, it holds for any values — and v007 called that
  equation "the single most important property in the document" while it could not
  fail. Two equations and three falsifiers replace it.
- **A render spike comes before the copy** (§5.4, V-1). v007 vendored 17,589 lines
  across V0–V6 before anything rendered, so the largest user-facing risks —
  terminal font, captions over output, audio drift, a mispronounced command name —
  could not be tested until after the whole copy. V-1 renders one `uv --version`
  scene first, throwaway, as evidence.

**Four contracts added, three of them about rights and egress:**

- **`--test-fixture` means load and parse only** (§8.1). `FR-028` as written refuses
  at the door and stamps the report, and says **nothing** about the model or TTS —
  so a third party's course text could reach a provider with only a stamp in a
  report a human may not read. `NFR-006` is recorded **VIOLATED**; this was an
  unmonitored path into it.
- **The stamp must reach the media, and the media writer must read it** (§8.2).
  It currently reaches neither, so the artefact that gets published is unstamped and
  the stamp is a record with no control.
- **A closed egress inventory with one chokepoint per egress type** (§8.3). §5.1
  closes the *import* population rigorously and the *network* population was never
  closed. §8.1 is unenforceable without it.
- **A content-hash blocklist, and the corpus referenced rather than vendored**
  (§8.4). `RIGHTS.md` §0 excludes a **path**, and 12 of the 30 corpus paths are
  byte-identical duplicates sitting **outside** it — a path allow-list does not
  exclude them. This also settles the question external review 1 left open.

**Two gaps named rather than solved**, because a design record that hides its weak
points cannot be reviewed:

- **Narration command grounding** (§7.1). The gate iterates the commands *the scene
  shows*; a command spoken in narration and shown on no slide is never seen, and
  the reference's grounding check does not read `narration` at all. This is the
  **third** thing, distinct from the deferred date gate, and it is unowned.
- **The "profile owns everything" goal is false** for `NARRATION_PROMPT`'s 46-word
  recap and the 30/55-word band (§3 goal 5).

**Numbers corrected, including three of my own:** the `A33` population is **24
sites across 6 files**, not "7 in one document" (v007's figure answered a
different question); §5.4's *"74 errors, all `no-untyped-def`"* is **43 of 74**, so
31 are not annotation debt and the stated rationale was wrong in kind; and the
private-name count is **deleted rather than adjusted** — four AST populations
returned 89/191, 25/70, 0/0 and 127/108.

**A defect in my own outbound artefact, found by the second reviewer and fixed:**
Annex A.4's `FR-028` cell ended in a bracketed placeholder, in the one file whose
entire purpose was supplying exact wording for checking. Now byte-exact, 605
characters, and all four annex artefacts verified.

**Rejected, and the reason matters:** a neutral shared-core library (against the
2026-09-28 ruling that cancelled the dependency), the IEC 29148 appeal (`DOCS.md`
§5 already answers it — *"DOCS.md **is** our tailoring record"*), a CI drift job
(needs network access to a repo we deliberately do not track), literal JSON schemas
that would create a second vocabulary beside `plan.json`/`verify.json`, and the
**multilingual rows** of the language contract (`REQUIREMENTS.md` records
hi-IN/mr-IN/MHE as *"ruled out by design"* and warns that writing such tests
*"would manufacture a permanent red suite for features nobody has agreed to build"*).

**Where the two reviews agreed independently**, which is the strongest signal in
either file: a per-file vendor manifest, and the closure claim reworded to be
relative to a commit. They reached it from opposite positions on whether to vendor
at all. *v008's own tally of the first review was wrong — it said 12 adopt where
the first triage had 8 — so the numbers were re-derived from the triages themselves.*

---

**v009 — round 7, four agents, all informed by the injected project knowledge.**
`reviewer`, `code-reviewer`, `tester` and `pipeline-architect` each returned NOT
GREEN: 11, 8, 5 and 12 defects, of which **six are confirmed by execution** and
three converge across independent reviewers. All fixed. The pattern is now
specific and worth naming: **round 7's defects were almost entirely v008's own new
prose**, not the design — four of them in text written hours earlier.

**Two confirmed first-sample crashes, in the lane's only blocker:**

- **`CommandClaim.source_file: Path` crashes every build.** Confirmed by running
  the real `atomic_json_write`: `TypeError: Object of type PosixPath is not JSON
  serializable`, and the writer has **no `default=`**. This is the *same* failure
  §7 documents for a `Callable`, in a field added alongside the fix for it. §6.2
  now carries `source_file` as a **`str`**, with `Path` only at the validator.
- **`polarity` has no producer.** The gate `REQUIRE`s it; the claim set is built
  from the raw model response, so the model cannot assign it. §6.2 now specifies a
  deterministic negation-cue scan over `source_span`, **or the field is marked
  advisory and `AC#24` is withdrawn** — it must not sit unassigned in the blocker.

**The reconciliation proof was arithmetically false, and the control was right.**
v008 justified `presented`'s independence by claiming `presented := issued −
dropped` would make its equation *"an identity that holds for any values."*
Executed over all non-negative triples: that substitution satisfies the equation in
**10 of 1,000** cases — **it fails loudly, it vacuates nothing.** The derivation
that *is* an identity is `presented := issued + admitted + dropped`, at **1,000 of
1,000**, and it went unnamed. §6.5 now states the two relations separately —
`issued == admitted + dropped` for reconciliation, `presented == issued` for
independence — and `AC#22`'s injection attacks the derivation that would actually
vacuate it. `issued` no longer appears on both sides, which it did.

**A number I deleted was true.** §5.1 claimed **0** private names were reachable
through the dropped façade, and that its 11 exports are module names. Measured: the
façade binds **193** imported names, **146** underscore-private, and `__all__`
holds **11 function names** with **0** module names. The tests reach **48 distinct
private names over 261 sites** — and **v008 had deleted "48" as not reproducible.**
It is reproducible, and it is restored with its population. The earlier passes that
returned 89/191, 25/70 and 0/0 were counting a different population and were never
the right question. **Deleting an unreproducible number is right; deleting one
because you measured the wrong thing is not.**

**Five criteria could pass while measuring nothing, and three named things that do
not exist:** `AC#26`'s "**the release step**" — the CLI has five subcommands
(`build`, `review`, `tts`, `verify`, `render`) and no `release` or `publish`, and
`REQUIREMENTS.md` §4's gate is seven *human* checks; the component is now named and
**created as work**. `AC#28`'s egress inventory, whose population **was the table
under test** — now enumerated independently (measured: **2 egress sites**, and
**≥7 media write sites across 4 modules**, with `speech.py` holding **zero** network
primitives, so two of v008's three chokepoints did not exist). `AC#30`, the V-1
spike — its four adjectives had no instrument, and it is §13.1's condition 6.
`AC#18`'s arithmetic, **6+5+1 = 12 not 11**, whose falsifier fired on a legitimate
member. And `AC#19`'s "all eight write sites", which were **never enumerated** —
they are now, and `AC#19` has a closed population.

**§13.1's stop condition was unsatisfiable as written.** It conflated *"every
criterion **names** a witness"* with *"every witness has been **executed**"* — a gate
that terminates a document review cannot be one only running code can satisfy. It is
now split **1a** (spec-completeness, gates the review) and **1b** (execution, a V7
condition). 1a is **not yet met**: `AC#3`, `AC#7`, `AC#17`, `AC#26` and `AC#33`'s
third clause still name no witness.

**Also corrected:** the `A33` population (v007 said 7-in-one-document, v008
published 24/6 whose breakdown summed to 20 — measured **22 across 5** design
records, **33 across 7** including the review artefacts); §5.4's V5 step (8
modules → **10**); §4's table was **missing the `enrichments` row** that §4.4
depended on; §4.3's AST check was a **blacklist** (which is how `"Key Takeaways"`
got there) and is now an **allow-list**; §4.3 said *"no renderer-owned title
strings **at all**"* while keeping one; §2 claimed `value_table`/`status_badges`
reach no renderer, which is **false** — both draw them, the defect being that no
*schema* field addresses them; §10's surviving *"Three renderers"*; a `RIGHTS.md`
§0 quote **elided "never narrated into a video"** with no ellipsis, in two places;
and the **coverage denominator**, now written down — 97%+ of the package would be
vendored code the channel did not author, so the floor keys to the channel's own
lines with the exclusion **generated from `vendor_manifest.json`**.

**Drift exposure is 40+ claims in ten groups, not "roughly 30"** — and the
constraint is weaker than §5.1 claims: the reference is a full local clone, 66
commits, `origin` configured, so every claim is re-derivable offline today by a
command. **There is no CI job; there is a clone and a command, and nothing runs
them on a schedule.**

**v007 — four agents, two of them new to this document.** Round 6 ran `reviewer`
(sixth time), `code-reviewer` (fifth), and two agents that had never seen the
project: **`tester`**, scoped to whether the gates can fail, and
**`pipeline-architect`**, scoped to provenance and coverage. All four returned NOT
GREEN, between them **34 category-a defects**. The two that mattered most were both
**confirmed by execution** and both were mine:

- **§7's hook was unrunnable as specified.** A `Callable` stored in the plan dict
  reaches `atomic_json_write`'s bare `json.dump`, and the write sits outside the
  `try/except` around the build — so `TypeError: Object of type function is not
  JSON serializable` on the first sample of every build, before any gate runs. §7
  now specifies `plan["_extra_gate_ids"]: list[str]` plus a module-level ordered
  registry, so no function is ever serialised.
- **The provenance population was post-drop.** `_drop_ungrounded_slide_text` runs
  at `plan.py:2397`; the gate at `plan.py:2493`. So a `total` counted at gate time
  is over **survivors** — a command the model emitted and grounding discarded is
  invisible, and the artifact publishes `verified: N, unverified: 0, total: N`,
  which is **100% over a filtered denominator.** That is
  `unclaimed_source_sections: 0` beside `source_sections: 12`, reproduced one layer
  down, inside the document that argues against that shape. §7 now requires the
  claim set to be built **before** the drop, and `AC#14` requires the **equation**
  `issued + dropped == presented`.

**§5.6's falsifier diagnosis was also wrong**, in a way that mattered: a genuinely
varying stub produces **6 distinct digests over 6 runs**, so the "1 digest" result
was a harness artefact of the same class §5.6 had just withdrawn. The real hole is
narrower and worse — varying **only** the narration response yields 1 digest,
because the stub's narration never reaches the plan dict. **The plan-digest check
is structurally blind to the narration chain**, which is the sole reason §5.6
patches two bindings; patching both is **necessary and not sufficient**, and a
passing fixture will not fix it. The precondition is now: vary within a run, and
digest an artifact that carries the narration.

**False published measurements, all removed rather than adjusted:** "74 errors, all
`no-untyped-def`" (measured: **43** of 74, and 31 are not annotation debt — so the
stated *rationale* for excluding `tests/` was wrong in kind, not just count);
"48 untyped helpers" and "48 unique private names, not 68" (four populations each
returned a different number; none published, and §5.1's earlier deletion of the
figure was correct while §14.7 still asserted it); "differ by up to 90x" for the
corpus truncation (**not measurable at all** — measuring the admitted count needs
the reader `A5` has not built, and `load_documents` raises `UnicodeDecodeError` on
a `.docx`, which is the defect `A5` exists to fix); "reach private names **through
the façade**" (measured **0** through it — they come from their own modules, and the
façade's 11 exports are all module names); "the only two modules with zero internal
imports" (it is **three** — `config.py` too, which also gives `VENDOR_REF` a file
that exists at V1); and "7 import lines" change in V6 (**241** import statements
over 17 module paths).

**From the two new agents, the residuals that survive.** `AC#16` is now
**structural** with a stated falsifier, and `AC#10` now covers the `A41`
allow-list in substance. **Three do not survive:**

- *"`A41` has no AC"* — **stale**: `AC#10`'s second clause requires an excluded path
  with a valid extension to produce the rights message. Closed.
- *"the `_audit_profile_ownership` row admits 7 of 10 and nothing requires it"* —
  **still open.** A row that publishes 70% and is required by nothing is §3 goal 4's
  silent zero in its own words. It needs an AC or removal.
- *"no mechanism would notice the baseline moving"* — **weaker than stated, and
  corrected in §5.1 and §13.1**: the reference is a full local clone, 66 commits,
  `origin` configured, so every claim is re-derivable offline by a command. The
  exposure is **40+ claims in ten groups**, not 30. There is no CI job; there is a
  clone and a command, and nothing runs them on a schedule.

**Structural correction:** §5.4's V4 gate on §5.6 was **circular** — the harness
exists to run `plan_lesson`, and `plan_lesson` arrives *with* V4. V4 now **carries**
the harness in the same commit.

**v006 — vendoring, and the owner's five rulings.** The engine dependency is
**removed**; the pipeline is vendored and §5 is rewritten as a **closed
population**. Three defects in v005 were found by the checks that answered the
owner's questions, and all three were mine:

- **§5's module map was not buildable.** It named 8 modules; the measured import
  closure is **15**. Seven — `duration`, `llm`, `narration`, `speech`, `text`,
  `topics`, `voice` — were missing, each a hard import from a module the map *did*
  list. "0 bypassing reads" over an open set is not a measurement.
- **The corpus population was wrong.** "30-file" was 30 paths resolving to **18**
  unique documents by md5; six files are byte-identical copies in two *sibling*
  repositories. `RIGHTS.md`, `A33`, `A15` and `PLAN.md` all said 18 — this
  document was the lone outlier.
- **§5's renderer paragraph was corrupt** — two drafts spliced mid-sentence.

Also corrected here: the private names reached from the tests are **48 unique**,
not 68; `AC#8` cannot be a set-equality check, because the five taxonomy copies do
**not** hold the same five strings and one label reaches the artifact under two
spellings (`"What Is This"` and `"What Is This?"`); `AC#7` named a symbol §5 never
created; and the **`json_snippet` test claim was inverted** — v006 asserted the
test "keeps passing" when the fabrication is deleted, and it does not: its first
assertion counts the branch firing, so deleting the branch fails it at
`assert 0 == 1`. Measured both ways; §14.3 now carries the table and `AC#19` is
correct.

**Also corrected here:** the import closure is **16**, not 15 — a module-level walk
misses `schema` and `validate`, which `plan` reaches through *function-local*
imports. And §5.4's "the copy arrives green" was over-claimed: `mypy` is clean on
`src` (19 files) and reports **74 errors in 7 files** on `tests/`, so the type gate
is `mypy src` by decision and the vendored tests sit outside it deliberately.

**G1 withdrawn.** The behavioural differential's determinism was reported as
"8 of 8 distinct digests". With **both** `_ask_llm_stable` bindings patched
(`narration.py` holds a second binding, which is what the first harness missed) and
a deterministic stub, the answer is **1 digest over 6 runs** — the chain is
deterministic. **The falsifier still fails**, because every fixture run lands on a
RENDER-BLOCKING plan and never reaches the success path; that is now §5.6's stated
precondition, and the determinism of the success path is **unmeasured, not
established**.

**v005 — architecture, owner-ruled 2026-09-28.** The engine dependency is
**removed**. `../doc-to-video-tutor` is a **baseline reference** only: this package
imports nothing from it, installs nothing from it, and pins no version of it
(`uv.lock`: 0 references). §5 is rewritten to a vendored module map, §14.1 is
**ruled** rather than open, and the entry-point test becomes the `argv`/`--help`
behaviour it should have been. This reverses a decision the owner had provisionally
approved earlier, and it is recorded because §14.1's earlier text — *"the seam
cannot be implemented channel-side"* — was only true while a dependency existed.

Recorded because `DOCS.md` rule 4 requires a re-read after editing a tracked doc,
and because a review that leaves no trace is indistinguishable from no review.

**Wrong, and corrected:** the console script was described as broken with no
`main` — it exists, runs, exit 0, and is a stub that *ignores `argv`* (AC#1
reframed). The audio gate was `A19` in six places; it is `A18`. `A5`'s done-when
was stated as 30 against a requirement that says 18, for a lane that parses 0
— now names the population at need-time (§8). `decision_prompt_rule`'s default
was misattributed to prompt framing when it is a `NarrationVoice` field; the
field is deleted (§4). "Two renderers" is three; "missed one four times" is
withdrawn as unverifiable. "Zero notebook mentions" was self-refuting and is now
a counted figure. The 39 is reported as a **total with its command** and no
decomposition, because every split attempted disagreed. A cross-reference to the renderers pointed at the front-door section.
"Twelve lines" was "~12 lines" in `DESIGN.md` §4.3 and `DECISIONS.md`.

**v003 — second review round (`reviewer` + `code-reviewer`, both NOT GREEN).** The
39-decomposition table is **deleted rather than settled**: three methods returned
16, 18 and 19 executable reads, and per `DOCS.md` rule 2 a number that cannot be
re-derived is deleted. A proposed `26 + 10 + 3 = 39` AST split also failed to
reproduce on a second walk and is not published either; the 39 total stands alone
with its command. `plain_scene_target` was **invented — 0 hits outside this
document**; the real symbol is `_plan_scene_target`. `A34` was **already taken**
(*"Review the MP4, not the deck"*), so assigning it to the allow-list created a
**second** collision one line after this document quoted the rule against exactly
that; the allow-list is now **`A41`**. `LoadedSource` is **five fields plus one
`@property`**, not six fields, and the 8-tuple's `content` is reached as
`result.source.text` — a rename that was previously unstated. §4.1 now names the
mechanism that carries `script_policy` into a Pydantic validator, including the
`Model(..., context=...)` swallow trap. §4 now owns `_ENUM_HINTS`, which v002 left
in a second object. The behavioural differential **cannot run today** —
`plan_lesson` is never executed by the suite — so the two fixtures are promoted
into Phase 1 as `PLAN-tutorial-lane.md` P1-f. `_extra_gates` is **four** call sites, and the hard/soft split is by
string prefix applied by callers, so "no warning tier" needed a prefix test. The
`.ipynb` claim was **false** (78 exist elsewhere under `/home/dipak`; 0 in the two
repos). The 46-word recap is a **bug report, not an open decision**.

**Rejected on review, after being factually confirmed:** the deprecated
`doc-to-video-tutor` shim does **not** bypass every gate — it translates and
delegates to `studio.cli.main(argv)`, and `--help` exits 0. The defect is that
its banner text lies about the invocation it is announcing. Ruling on the false
version would have banned an already-gated command, so §5 and §7 rule on the
true one. The real script name is `doc-to-studio`, not `doc-to-video-studio`.

**Rewritten, not corrected, because one shared premise was false:** §2, §4, §12's
deleted row, and AC#5. The premise was that a symbol-counting sweep is a
behaviour-preservation proof. It is neither — it is blind to prompt strings and
validators, which is the class of defect the seam exists to prevent.
