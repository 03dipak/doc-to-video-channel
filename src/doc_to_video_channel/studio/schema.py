"""Strict Pydantic schema for lesson plans and TTS clips.

Phase 1 of the deterministic pipeline: enforce layout constraints at
generation time (max 4 bullets per scene, normalized narration text,
English-only slide fields) before rendering or audio synthesis.
"""

from __future__ import annotations

import re
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .text import _has_non_latin_script

_FIELD_NAMES = ("title", "bullets", "steps", "flow", "visual_diagram",
                "code_snippet", "code_context", "analogy", "design_decision",
                "section", "topic")


# --- V2 / AC#7: SectionKind becomes a TYPE, and the two spellings collapse ---
#
# Measured 2026-09-28, and this is the defect AC#7 names:
#   config._SECTIONS  = ('what is this', 'why do we need it', 'how does it work',
#                        'example', 'takeaway')          <- lower case
#   a built plan.json emits "section": "What Is This"    <- Title Case
# Two spellings of one concept, and `section: str` accepted ANY string, so nothing
# ever noticed: 'bogus' passed validation.
#
# The canonical form is the one in config, lower case, because that is what the
# planner is TOLD the sections are. A before-validator accepts either spelling and
# stores the canonical one, because the reference plans already exist in Title
# Case and refusing them would break inputs that were never wrong. This is a
# SPELLING canonicaliser, not repair: it maps a known member onto its canonical
# spelling and REJECTS everything else. It never invents a section.
SectionKind = Literal[
    "what is this",
    "why do we need it",
    "how does it work",
    "example",
    "takeaway",
]

#: The Title-Case spellings the reference plans carry, mapped to canonical.
_SECTION_SPELLINGS: dict[str, str] = {
    "what is this": "what is this",
    "why do we need it": "why do we need it",
    "how does it work": "how does it work",
    "example": "example",
    "takeaway": "takeaway",
}

#: What a caller wrote, when it is a member under SOME accepted spelling.
_SECTION_LOOKUP: dict[str, str] = {
    **{k: v for k, v in _SECTION_SPELLINGS.items()},
    "What Is This": "what is this",
    "Why Do We Need It": "why do we need it",
    "How Does It Work": "how does it work",
    "Example": "example",
    "Takeaway": "takeaway",
}


def canonical_section(value: str) -> str:
    """Resolve any accepted spelling to the canonical one, or raise.

    Case-insensitive on the way in, so `WHAT IS THIS` and `what is this` agree.
    A value that is not a member is refused rather than passed through, which is
    the whole point: the old `section: str` accepted `'bogus'` without comment.
    """
    candidate = value.strip()
    resolved = _SECTION_LOOKUP.get(candidate) or _SECTION_LOOKUP.get(candidate.lower())
    if resolved is None:
        raise ValueError(
            f"section {value!r} is not one of {sorted(set(_SECTION_SPELLINGS))}. "
            f"Accepted spellings are the canonical lower case and the Title Case "
            f"the reference plans carry; anything else is refused rather than "
            f"stored, because a section the planner never named is a section the "
            f"renderer will not have a layout for."
        )
    return resolved


class SlideScene(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    narration: str
    bullets: list[str] = Field(default_factory=list, max_length=4)
    steps: list[str] = Field(default_factory=list)
    flow: list[str] = Field(default_factory=list)
    visual_diagram: str = ""
    code_snippet: str = ""
    code_context: str = ""
    analogy: str = ""
    design_decision: str = ""
    # V2: `| None` rather than a default member, because the baseline's default was
    # `""` and a scene with NO section is legitimate -- most scenes are not section
    # cards. Defaulting to "what is this" would FABRICATE a section for every such
    # scene, which is repair, and it would also make an omitted field fail
    # validation. Measured: 133 reference plan files carry section values, and
    # every one of them is one of the five members, but "absent" is still a state
    # the baseline allowed and this must not remove.
    section: SectionKind | None = None

    #: A44: the locale of the voice that will speak this scene's narration.
    #: Class-level, not per-scene, because the voice is chosen once per build --
    #: a plan where two scenes disagree about their voice is a plan whose audio
    #: cannot be rendered, and that should be a schema error rather than a
    #: surprise at TTS time.
    _narration_lang: ClassVar[str] = "en-IN"
    topic: str = ""
    source_refs: list[str] = Field(default_factory=list)

    @field_validator("bullets", "steps", "flow", mode="before")
    @classmethod
    def normalize_sequence_fields(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, tuple):
            return list(v)
        return v

    @field_validator("bullets")
    @classmethod
    def validate_bullets_max(cls, v: list[str]) -> list[str]:
        if len(v) > 4:
            raise ValueError("bullets per slide must be at most 4")
        for item in v:
            if _has_non_latin_script(item):
                raise ValueError("slide text must stay English (Latin script)")
        return v

    @field_validator("title")
    @classmethod
    def require_non_empty_title(cls, v: str) -> str:
        if isinstance(v, str) and not v.strip():
            raise ValueError("title must not be empty")
        return v

    @field_validator("section", mode="before")
    @classmethod
    def validate_section_kind(cls, v: object) -> object:
        """Canonicalise the spelling, then let the Literal do the enforcing."""
        if isinstance(v, str) and v.strip():
            return canonical_section(v)
        # Empty and absent both mean "this scene is not a section card". They map to
        # None, NOT to a default member: inventing a section is the repair this
        # project forbids.
        return None if v is None or (isinstance(v, str) and not v.strip()) else v

    @field_validator("narration", mode="before")
    @classmethod
    def reject_unpronounceable_narration(cls, v: object) -> object:
        """A44, landed at V5 because it needs the voice registry.

        `narration` sits outside `_FIELD_NAMES`, so the script check that guards
        every ON-SCREEN field never looked at it. Measured before this fix:
        `SlideScene(narration="यह अनुभाग")` validated clean while the same script
        in `title` or `bullets` was refused.

        The rule is **voice-relative**, and the measurement that decided it is that
        the reference's DEFAULT voice is Hindi. `_VOICES` holds `mhe-mix` at
        `hi-IN-SwaraNeural` and `english` at `en-IN-NeerjaNeural`, and
        `NarrationVoice` has no `locale` field at all -- the only signal is the
        `tts_voice` prefix. So an absolute rule is wrong in both directions:
        refusing non-Latin narration would break the default, which CAN pronounce
        Devanagari, and allowing it would let the English voice narrate gibberish.

        `narration_lang` names the voice's locale, defaulting to the only locale
        this build can speak. It is a field rather than a constant so a caller
        declaring a Hindi build is making a claim the validator can check, not
        asking the check to be switched off.
        """
        if not isinstance(v, str) or not v.strip():
            return v
        if str(getattr(cls, "_narration_lang", "en-IN")).startswith("hi"):
            return v
        if _has_non_latin_script(v):
            raise ValueError(
                f"narration contains a non-Latin script and the selected voice is "
                f"{cls._narration_lang}, which cannot pronounce it. Pass "
                f"narration_lang='hi-IN' for a Hindi build. The on-screen fields "
                f"are checked unconditionally because a viewer READS them; this one "
                f"is checked against the voice because a viewer HEARS it."
            )
        return v

    @field_validator(*_FIELD_NAMES)
    @classmethod
    def reject_non_latin_slide_text(cls, v: str | list[str]) -> str | list[str]:
        values = v if isinstance(v, list) else [v]
        if any(_has_non_latin_script(str(item)) for item in values):
            raise ValueError("slide text must stay English (Latin script)")
        return v

    @field_validator("source_refs")
    @classmethod
    def validate_source_refs(cls, v: list[str]) -> list[str]:
        return [str(x).strip() for x in v if str(x).strip()]

    @field_validator("narration")
    @classmethod
    def normalize_narration(cls, v: str) -> str:
        v = re.sub(r"(\w):(\w)", r"\1: \2", v)
        v = v.replace(".jso ", ".json ")
        v = v.replace(".jso", ".json")
        return v

    @field_validator("code_context")
    @classmethod
    def normalize_code_context(cls, v: str) -> str:
        v = re.sub(r"Design choice \w+:", "", v)
        v = re.sub(r"Faisla hua ki:", "", v)
        v = re.sub(r"Yeh .*? सोच के बनाया:", "", v)
        v = re.sub(r"Iska ahem reason:", "", v)
        return v.strip()


class LessonPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    opening: str
    scenes: list[SlideScene] = Field(min_length=1)
    takeaways: list[str] = Field(default_factory=list)

    @field_validator("title", "opening")
    @classmethod
    def reject_non_latin_plan_text(cls, v: str) -> str:
        if _has_non_latin_script(v):
            raise ValueError("plan text must stay English (Latin script)")
        return v

    @field_validator("scenes")
    @classmethod
    def validate_scene_count(cls, v: list[SlideScene]) -> list[SlideScene]:
        if len(v) < 1:
            raise ValueError("at least one scene is required")
        return v

    @field_validator("takeaways")
    @classmethod
    def validate_takeaways(cls, v: list[str]) -> list[str]:
        return [str(x).strip() for x in v if str(x).strip()][:8]

