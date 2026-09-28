"""Pipeline constants, prompts, colors, fonts and policy data."""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv

load_dotenv()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
TTS_VOICE = os.getenv("TTS_VOICE", "hi-IN-SwaraNeural")
TTS_RATE = os.getenv("TTS_RATE", "-8%")
TTS_PITCH = os.getenv("TTS_PITCH", "+0Hz")
TTS_VOLUME = os.getenv("TTS_VOLUME", "+0%")
# Audio rule C3: loudness normalization of every TTS clip (off via TTS_LOUDNORM=off).
TTS_LOUDNORM = os.getenv("TTS_LOUDNORM", "on")
LOUDNESS_TARGET = float(os.getenv("LOUDNESS_TARGET", "-16.0"))  # LUFS, integrated
LOUDNESS_TP = float(os.getenv("LOUDNESS_TP", "-1.5"))  # dBTP true peak
LOUDNESS_LRA = 11.0  # LU, range gate
# Speaking pace used ONLY for the pre-audio duration estimate, where no audio
# exists yet. Calibrated by measurement, not by reading the rate off the TTS
# setting: mod03_gates_v023 rendered 383 spoken words across 223.0 s of ffprobe-
# measured clip time, i.e. 103.1 words/min at -8% for the mhe-mix profile. The
# previous 135.0 was ~31% high, which made a 3.72 min lesson look like 2.84 min
# and fired a false under-run warning. Once audio exists, _render_media reports
# the measured duration and re-checks against that instead of this constant.
LOUDNESS_WPM = 103.0

# The one spoken form of "1/(n+1)". Single-sourced because it had four
# hand-written copies that no test tied together, and because it is consumed by
# two different layers that must agree: the TTS rewrite table (voice.py, which
# rewrites the literal before synthesis) and the planner/narrator prompts (which
# exist to stop the model emitting raw symbols at all).
#
# The wording is a structural fix, not a stylistic one. "one over n plus one"
# runs the divisor and the addend together with nothing for the ear to attach
# "plus" to, and 1/(n+1) is exactly the case where precedence decides the
# answer - the same words also read as 1/n + 1. "the whole of" is a
# determiner-plus-noun phrase, so it gives the clause a boundary the listener can
# hold before the addend arrives. A trailing qualifier cannot do this job: it
# lands after the ambiguity has already been spoken.
SAMPLE_SIZE_FLOOR_SPOKEN = "one divided by the whole of n plus one"


def _with_spoken_floor(prompt: str) -> str:
    """Interpolate `{floor}` prompt prose with `SAMPLE_SIZE_FLOOR_SPOKEN`.

    The prompts are plain strings carrying `str.format` placeholders, so they
    cannot be f-strings - an f-string would try to evaluate `{content}` at
    import. A token keeps the phrase single-sourced while the prompt stays
    formattable.
    """
    return prompt.replace("{floor}", SAMPLE_SIZE_FLOOR_SPOKEN)


_SCHEMA_VERSION = 2
_REPEAT_POLICY_VERSION = 2
STUDIO_PROMPT = _with_spoken_floor("""You are an expert educator preparing a classroom lesson.
Read the documents below, then output a STRICT JSON lesson plan (no extra text).
Narration is written by a SEPARATE narration pass - leave every "narration"
field as an empty string "" and never spend output tokens on speech.

LESSON PLAN SCHEMA:
{{
  "title": "short lesson title",
  "opening": "1-2 sentence spoken intro (Roman-script Marathi-Hindi-English mix)",
  "scenes": [
    {{
      "section": "ONE section exactly (single value, not the list): 'What is this?', \
'Why do we need it?', 'How does it work?', 'Example', 'Takeaway'",
      "title": "short slide heading (ENGLISH); name the real source module/phase \
 here, e.g. '1: Data & testset (goldens)' - never put the module name in 'section'",
      "topic": "short canonical topic for this scene",
      "source_refs": ["source file or source heading reference"],
      "narration": "",

      "bullets": ["1-4 short ENGLISH bullet points for the slide"],
      "steps": ["numbered steps, 2-5 items (optional, empty array if none)"],
      "flow": ["arrow pipeline, e.g. A to B to C (optional, empty if none)"],
      "analogy": "one short real-life analogy in English (optional, empty if none)",
      "design_decision": "WHY this approach vs a REAL alternative the DOCUMENTS
                          imply, phrased 'X not Y because Z' (optional; empty
                          string if the docs don't distinguish an alternative)",
      "visual_diagram": "Optional. A diagram chain of REAL assets from the DOCUMENTS,
                         written as label nodes joined by '--- >' arrows, e.g.
                         '[Golden dataset] ---> [Judge] ---> [Verdict]'. Omit if none.",
      "code_snippet": "Optional. A real, VERBATIM command/JSON/assertion lifted from
                       the DOCUMENTS. Omit if none."
    }}
  ],
  "takeaways": ["3-5 short ENGLISH takeaway points"]
}}

RULES:
- exactly {scene_count} scenes (one per major source section / concept),
  matching a spoken length of about {target_minutes} minutes total
  (~130 words per minute). One scene per source concept; merge minor examples into
  their parent scene; never add a separate recap scene (takeaways are generated by the pipeline).
- NARRATION EMPTY (MANDATORY): every "narration" field MUST be "". A separate
  narration pass writes the spoken script from the finished plan - never write
  narration here, never budget output tokens for speech.
- OPENING LANG (MANDATORY): the "opening" field must be written ONLY in
  Latin/Roman script Marathi-Hindi-English mix (Hinglish). NEVER use Devanagari
  or any other script - Latin letters only, no matter the language. Do NOT write
  the opening entirely in English. Scatter a few everyday Marathi/Hindi words
  naturally (e.g. 'ha ka', 'samajh', 'accha', 'aaj', 'kya', 'kasa', 'mhanje').
  Technical words stay English. Example style (never copy this sentence;
  write your OWN opening about the LESSON TOPICS, not about embeddings):
  "Aaj aapne dekha ki yeast kaam kasa karto — chala step by step samajhuyacha."
- OUTPUT FORMAT (MANDATORY): reply with EXACTLY ONE ```json code block containing the
  WHOLE plan and nothing else. Never open a second ```json block anywhere. Never nest a
  JSON object or code fence inside an opening/bullet/analogy string - every
  string value is ONE quoted layer.
- OPENING SPOKEN (MANDATORY): the opening is a teacher's spoken line - NEVER slide
  metadata. Never say 'slide pe', 'yeh points likhe hain', 'exact points',
  'bullets', or read a bullet verbatim aloud. Write number prefixes out ('first',
  'step one' - never '1:' or '1.'), spell file names naturally ('module one',
  'active dot json', '{floor}'), and NEVER leave raw symbols in the
  opening ('=', '&', '→', '/', backslashes, underscores, brackets are not spoken).
- Slide visible text (title, bullets, steps, flow, analogy, design_decision, visual_diagram,
  code_snippet, and takeaways) must stay in ENGLISH and use Latin script only; never emit Devanagari
  or any other non-Latin script in any slide-visible field.
- GROUNDING (MANDATORY): every slide fact and takeaway must be traceable to the DOCUMENTS.
  Never invent definitions, numbers, names, or examples not present in the docs. When the
  docs name concrete assets (module tables, lifecycle phases, pipeline stages, engine/option
  names, deferral registers), keep those names on the slide instead of generic restatements.
  Takeaways must reflect the docs' stated thesis and priorities, not generic advice.
- INTERVIEW FRAMING (MANDATORY): each scene's "design_decision" must explain a REAL
  design choice the DOCUMENTS make - e.g. 'gate lets a row through at
  tolerance-baseline, it is NOT a blocking guardrail'. Ground it in contrast language
  the docs actually use (unlike, never, must, not the same as, instead of, rather
  than) or two similar concepts defined near each other. If the docs don't support a
  genuine distinction, set "design_decision" to "" - never invent an interview
  question or a plausible alternative the docs don't mention.
- TAKEAWAYS (MANDATORY): takeaways are synthesized CONCLUSIONS/DECISIONS in
  DIFFERENT wording from the scene bullets - never restate a bullet verbatim.
- SOURCE-DRIVEN OUTLINE (MANDATORY): build the scene list from the DOCUMENTS' own
  structure - their headings, module/table rows, lifecycle phases, named components,
  and registers. Name scenes after real elements that appear in the docs. A scene
  title or bullet that would fit any topic's generic course template ("What is X?",
  "Improves accuracy", "Provides feedback", "Ensures quality") is REJECTABLE -
  replace it with the docs' actual content.
- SCENE COUNT (HARD): exactly {scene_count} scenes, never more, never fewer.
- UNIQUENESS: every bullet line must be unique across the whole lesson.
- WHITEBOARD VISUALS: "section" must be ONE of the five schema values above; the
   source element name goes in "title". "visual_diagram" must be a short chain of REAL
   component names from the DOCUMENTS joined by '--- >' arrows, and every label must
   illustrate THIS slide's OWN topic (the slide title) - never another concept's
   assets. For a tolerance/threshold concept, draw the comparison chain itself
   (e.g. '[Run Value] ---> [Delta vs Baseline] ---> [Absolute/Relative Threshold]'),
   not a baseline-pointer file. "code_snippet" must be
   a verbatim real command, path, JSON, or assertion from the DOCUMENTS (e.g. 'uv sync',
   'compare.py --baseline active.json') - never invented pseudo-code or made-up
   function names like 'compare function'.
- SOURCE-DRIVEN RICHNESS (HARD): every scene needs 2+ substantive bullets drawn from the
    DOCUMENTS for that concept. A single generic word ("Canonical pointer") is REJECTABLE -
    replace it with the doc's actual specifics (e.g. for `active.json`: the full schema
    `{{schema_version, baseline_id, path}}`, the resolve-BEFORE-compare rule, the atomic
    rewrite, and the path-safety checks). A title or bullet that fits any generic course
    template is REJECTABLE. For schema/state concepts (e.g. a config or pointer file),
    output the ACTUAL JSON keys, path rules, and structural fields inside the bullet text -
    never a paraphrase or placeholder.
- Never return text outside the JSON. No markdown fences around it.
- Output JSON only.

DOCUMENTS:
{content}""")
NARRATION_PROMPT = _with_spoken_floor("""You are the narration writer for an existing lesson plan.
Below are the finished scenes (section, title, bullets, steps, design_decision)
and a source excerpt. Write the SPOKEN script for EVERY scene in Roman-script
Marathi-Hindi-English (Hinglish) - the studio's teaching voice. The planner
left every "narration" blank; YOUR output becomes the whole spoken track.

Return EXACTLY ONE JSON ARRAY (no extra text, no markdown fences other than the
array), one object per scene IN ORDER:
[{"scene": 1, "narration": "..."}, {"scene": 2, "narration": "..."}, ...]

For EVERY scene's "narration" write {words_min}-{words_max} spoken words as
2-4 COMPLETE sentences that TEACH that scene's ONE concept. The whole lesson
must total about {words_total} spoken words across {clip_count} clips - that
total is what lands the video on the requested length, so treat it as the
budget, not a suggestion. Requirements:

- LANG (MANDATORY): Latin/Roman script ONLY - never Devanagari or any other
  script. NEVER write a narration entirely in English. Scatter a FEW everyday
  Marathi/Hindi words ('ha', 'samajh', 'accha', 'aaj', 'kya', 'mhanje'); use
  DIFFERENT ones per scene and never paste this word list.
- SPOKEN, NOT SLIDE METADATA: you are a teacher explaining - never 'slide pe',
  'yeh points likhe hain', 'exact points', or 'bullets'. Do NOT read bullets or
  the title verbatim, and never open a narration by re-reading the scene title
  (mention it at most once).
- NO RAW SYMBOLS: write number prefixes out ('first', 'step one' - never '1:'
  or '1.'), spell file names naturally ('module one', 'active dot json',
  '{floor}'), and never leave '=', '&', '→', '/', backslashes,
  underscores or brackets in the narration.
- TEACH ONE CONCEPT: narrate the reasoning behind the scene - what it is, why
  this approach (lean on "design_decision") and not another, what happens on
  failure, what limit applies. Do not cram several concepts into one scene.
- GROUNDING: every fact must be traceable to the SOURCE EXCERPT - never invent
  definitions, numbers, names, or examples.
- VARY: every scene's narration must START and END differently; never reuse a
  closing phrase or any full sentence across scenes. No rhetorical fillers
  ('thik hai? na?') and no 'isliye aaj hum samajhe ge' non-closures.
- LENGTH: keep each narration between {words_min} and {words_max} spoken words.
  Do not pad to reach the budget and do not pad with filler - if a scene has
  less to teach, say less. The 46-word closing recap is inside this budget.

Return the JSON ARRAY only - no prose before or after it.""")
TOPIC_PROMPT = """List the 1-3 CENTRAL topics covered by the documents below.
Return ONLY a JSON array of short topic strings, e.g. ["rag and retrieval", "observability"].
No extra text, no markdown fences.

DOCUMENTS:
{content}"""
_BANNED_EXAMPLE = re.search(r'Example style.*?"([^"]+)"', STUDIO_PROMPT,
                            re.DOTALL)
_BANNED_NGRAMS: set[tuple[str, ...]] = set()
_BANNED_DISTINCT: set[str] = set()
if _BANNED_EXAMPLE:
    _B_EX_TOKS = [w for w in re.findall(r"[a-z0-9]+", _BANNED_EXAMPLE.group(1).lower())]
    for _n in (2, 3):
        _BANNED_NGRAMS |= {tuple(_B_EX_TOKS[_i:_i + _n])
                           for _i in range(max(0, len(_B_EX_TOKS) - _n + 1))}
    _BANNED_DISTINCT = {t for t in _B_EX_TOKS if len(t) >= 7}
_MHE_MARKERS = {
    "accha", "aaj", "aap", "hai", "kaise", "kar", "karte", "kya", "kyun",
    "mhanje", "sakta", "samajh", "seekhe", "seekhenge", "sikha", "sirf",
    "sodya", "unka", "unke", "woh", "yeh",
}
_NARR_MIN_TOKENS = 12
_SECTIONS = ("what is this", "why do we need it", "how does it work", "example", "takeaway")
_ENUM_HINTS = (
    ("what is this", ("schema", "contract", "definition", "identifier",
                      "metadata", "registry", "defines")),
    ("why do we need it", ("why", "risk", "without it", "guardrail-like")),
    ("how does it work", ("compare", "gate", "pipeline", "process",
                          "mechanism", "mirror", "frozen", "baseline")),
    ("example", ("example", "sample", "walkthrough", "trace", "scenario")),
    ("takeaway", ("takeaway", "recap", "key point", "summary", "remember")),
)
_DD_GENERIC = (
    "must be consistent", "consistent across", "not out of scope",
    "because the docs", "as you can see", "simply because",
)
# Optional contrastive connectives: a closed grammatical class, and the
# recognised frame of a templated 'WHY THIS' card. "X is done to A, not just B
# - unlike C, it D" is a skeleton, and a whole population of cards reaching for
# the same connective is the 7B filling that skeleton in rather than writing
# nine separate decisions.
#
# Optional is what makes this measurable. Obligatory grammar ("is the", "not a",
# "but a") also has a high document frequency across any set of English cards
# and carries no signal at all - a bigram-of-function-words version of this
# check fired on 25 of the 51 plan artifacts and would have stripped the card
# from most lessons. These words are ones a writer may simply not use.
#
# Measured over the 51 plan artifacts with >=4 cards: `unlike` is over-
# represented in 2, `not just` in 3, and every other marker in none.
_DD_FRAME_MARKERS = (
    "unlike", "whereas", "although", "rather than", "instead of",
    "not just", "not only", "as opposed to",
)
# A marker carried by at least this share of the cards is a frame rather than
# one writer's preference. The observed gap is wide: the frame markers scored
# 0.67-0.89 on the templated plans and 0.00-0.11 elsewhere, so the exact value
# is not delicate.
_DD_FRAME_MIN_DF = 0.6
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_TEMPLATE_AHEM = re.compile(
    r"(?:aage badhte hai\s+)?ek ahem module hai,?\s+hum yeh samajhenge ki "
    r"kya (?P<c>[^.]*)\.", re.I)
_TEMPLATE_SEEKHTE = re.compile(
    r"chaliye\s*['\"]*seekhte hai\s+kya (?P<c>[^.]*)\.\s*['\"]*", re.I)
_NARR_HEADS = ("Yahan samjho", "Ab dekho", "Ismein focus karo", "Main point",
               "To chaliye dekhein", "Aur yahan dekhte hain")
# No trailing space. These are prefixes, and a prefix whose separator is an
# invisible trailing space is a trap: `narration.py` has two call sites that
# join a lead to a design decision, one of which `.strip()`s the lead and
# inserts nothing, so the separator vanished and the 7B's "Gate lets a row
# through" was spoken as the single nonsense token "kiGate" (confirmed in
# word_timings.json on mod03_gates_v013, 2 of 9 scenes). The separator now
# lives at the join, where it is visible.
_DD_LEADS = ("Reason yahi hai ki", "Iska ahem reason yeh hai ki",
             "Design choice dekho,", "Yeh is soch ke banaya,",
             "Core decision yeh hai,", "Asli wajah yeh hai,",
             "Faisla yeh hua,", "Isliye design aisa hai,")
_POINTS_LEADS = (" Aur slide ke exact points: ", " Slide pe yeh points likhe hain: ",
                 " Aur in points pe dhyaan do: ", " Slide ke asli points: ",
                 " Aur points, ek ek karke: ", " Slide ke main points: ",
                 " Slide ke yeh key points hain: ", " Points abhi padhte hain: ")
_OPENER_POOL: list[str] = [
    "Is scene mein hum ek fresh concept samjhenge. ",
    "Ab chaliye isse detail mein dekhte hain. ",
    "Yahan hum ek important piece samjhte hain. ",
    "Ek key idea ka asaan explanation lete hain. ",
    "Is baar hum simple terms mein explore karenge. ",
    "Samajhne ke liye step-by-step chalein. ",
    "Isko ek hi example se clear kiya jaa sakta hai. ",
    "Chaliye ab iska kaam karne ka tareeka dekhte hain. ",
]
_CLOSER_POOL: list[str] = [
    " to yehi hai iska matlab.",
    " to yahan baat clear ho gayi.",
    " ye hi tha iska asli kaam.",
    " to isse agle scene mein use karenge.",
]
MIN_SCENES = 5
TARGET_MAX_SCENES = 8
AUTO_TRIM_MAX_SCENES = 12
_CONTRAST_RE = re.compile(
    r"\b(?:unlike|never|must(?!aybe)|not the same as|instead of|rather than|"
    r"as opposed to|compared with|whereas)\b",
    re.IGNORECASE,
)
BG = (18, 24, 38)
PANEL = (30, 40, 60)
ACCENT = (66, 133, 244)
GOLD = (255, 193, 7)
GREEN = (76, 175, 80)
RED = (234, 67, 53)  # FAIL semantics only; see LLD B2.2 exception
FG = (235, 238, 245)
MUTED = (150, 158, 175)
TITLE_HOLD = 4.0  # seconds the cover card stays before the first scene

# Per-clip spoken-word thresholds, as ENFORCED by `audit_tts_script`. Named here
# because they are also the input to the duration-reachability arithmetic in
# `video.reachable_duration_band`, and that arithmetic was previously argued
# from an invented 42-word floor rather than from the contract the gate applies.
#
# The FAIL pair is the hard contract (FAIL is in the build's blocking set); the
# WARN pair is advisory. LLD 20.2 #10 settled the band at 20-90 for this reason.
NARRATION_WORDS_MIN_FAIL = 20
NARRATION_WORDS_MAX_FAIL = 90
NARRATION_WORDS_MIN_WARN = 25
NARRATION_WORDS_MAX_WARN = 70
# What the prompts ASK for, which is a narrower target than the enforced band.
# A plan inside this range satisfies both; the gate only enforces the pair above.
NARRATION_WORDS_PROMPT_MIN = 30
NARRATION_WORDS_PROMPT_MAX = 55
_VIDEO_BODY_MAX = 652  # int(H) - 68 for the 720px canvas
_SOFT_PREFIXES = ("narration pure-English",
                   "repeating narration phrase",
                   "near-duplicate bullets vs takeaways",
                   "placeholder title restates section",
                   "fused slide token",
                   "unspoken visual claim",
                   "narration still speaks about",
                   "source section not covered")
PACKAGE_NAME = "doc-to-video-tutor"
PACKAGE_VERSION = "0.1.0"
BRAND_NAME = PACKAGE_NAME
BRAND_TAGLINE = "learn by listening"
BRAND_FOOTER = f"{BRAND_NAME} v{PACKAGE_VERSION} — {BRAND_TAGLINE}"
