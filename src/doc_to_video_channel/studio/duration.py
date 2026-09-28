"""The duration contract: silence schedule, word budget, and verdict bands.

One home for the arithmetic, because the same three questions were being
answered in three places with three different assumptions:

- how much silence the assembly will add (`structural_silence_seconds`, which
  `assemble_video` actually inserts, and two re-derivations of it from the same
  literals);
- how many spoken words a target duration implies (`words_for_target`, needed by
  the planner to put a number in the prompt, and by the gate to check the plan);
- whether a measured duration is acceptable (`duration_verdict`).

It lives apart from `video.py` because the planner needs it and must not import
moviepy to get it. `video.py` re-exports everything here, so existing callers
and tests keep working.
"""

from __future__ import annotations

from .config import (
    LOUDNESS_WPM,
    NARRATION_WORDS_MAX_FAIL,
    NARRATION_WORDS_MIN_FAIL,
    TITLE_HOLD,
)

# The inter-clip pause and the tail hold, as used by `assemble_video`. Named
# here so the schedule, the estimate and the prompt all quote one pair.
GAP_SECONDS = 3.0
END_HOLD_SECONDS = 6.0

# Verdict bands, as a ratio of delivered duration to declared target. Symmetric
# on purpose: an earlier version only ever looked at the short side, so a fresh
# `build` that rendered 4.38 min against a 4.0 min target (109%) reported PASS -
# and so would 300%, since anything at or above 0.92 cleared it. A lesson twice
# its declared length is as much a product defect as one at half, and it needs a
# different remedy: overshoot is trimmed selectively, undershoot is filled with
# source-grounded teaching.
BAND_LOW = 0.80       # below -> critical
BAND_OK = 0.92        # below -> short
BAND_OK_HIGH = 1.15   # above -> long
BAND_HIGH = 1.50      # above -> critical

_SECONDS_PER_WORD = 60.0 / LOUDNESS_WPM


def clip_count(n_scenes: int) -> int:
    """Spoken clips for N scenes.

    N+1, not N: the Key Takeaways clip is spoken after the scenes, carries its
    own pause, and contributes audio like any other clip. Getting this wrong
    shifts the whole budget by one clip's worth of words and one pause.
    """
    return n_scenes + 1


def structural_silence_seconds(n_clips: int, gap: float = GAP_SECONDS,
                               end_hold: float = END_HOLD_SECONDS) -> float:
    """Seconds of deliberate silence the assembly adds for `n_clips` clips.

    The parameter is a CLIP count. It was named `n_scenes` at the call site in
    `video.py` and was passed `len(paths)`, which is clips - so the arithmetic was
    right and the name was a trap for the next reader.
    """
    return TITLE_HOLD + gap * n_clips + end_hold


def audio_seconds(words: float) -> float:
    """Delivered audio seconds for a spoken word count, at the calibrated rate."""
    return words * _SECONDS_PER_WORD


def words_for_target(n_scenes: int, target_seconds: float,
                     gap: float = GAP_SECONDS,
                     end_hold: float = END_HOLD_SECONDS) -> float:
    """Spoken words per clip that land `n_scenes` on `target_seconds`.

    Negative when the target is shorter than the structural silence alone, which
    is the case a hard fail has to name rather than divide through.
    """
    clips = clip_count(n_scenes)
    silence = structural_silence_seconds(clips, gap, end_hold)
    return (target_seconds - silence) / _SECONDS_PER_WORD / clips


def total_words_for_target(n_scenes: int, target_seconds: float,
                           gap: float = GAP_SECONDS,
                           end_hold: float = END_HOLD_SECONDS) -> float:
    """Total spoken words across every clip, for `target_seconds`."""
    return words_for_target(n_scenes, target_seconds, gap, end_hold) * clip_count(
        n_scenes)


def predicted_duration_seconds(words: float, n_scenes: int,
                               gap: float = GAP_SECONDS,
                               end_hold: float = END_HOLD_SECONDS) -> float:
    """Delivered seconds implied by a word count: audio plus the silence schedule.

    This is the quantity the user's `--minutes` is about. Reporting the audio
    sum alone understates it: on mod03_gates_v013 the clips totalled 5.24 min
    (131%) while the delivered MP4 was 5.91 min (148%), the difference being
    40.4s of deliberate silence reported as if it were teaching time.
    """
    clips = clip_count(n_scenes)
    return audio_seconds(words) + structural_silence_seconds(clips, gap, end_hold)


def reachable_duration_band(n_scenes: int, gap: float = GAP_SECONDS,
                            end_hold: float = END_HOLD_SECONDS
                            ) -> tuple[float, float]:
    """Shortest and longest delivered duration, in seconds, for N scenes.

    Both ends come from the word thresholds the TTS gate ENFORCES
    (`NARRATION_WORDS_*_FAIL`), not from a figure observed in one build. That
    distinction decided a plan question. `mod03_gates_v013` shipped 10 clips of
    42-76 words (mean 52.9) against a 4.0 min target, and the review took 42 -
    the minimum of that one over-budget build - as a per-scene floor. Under that
    invented floor a 4.0 min target looked unreachable at 9 scenes, and scene
    count was made "the keystone". Under the enforced contract the same target
    needs 34.3 words/clip at 9 scenes, inside both the 20-90 gate band and the
    30-55 band the prompt asks for. The target was never unreachable: the
    overshoot was 529 spoken words where 343 fit.

    The floor is what a hard fail tests against. The ceiling is what makes a
    scene count viable for a given target at all.
    """
    clips = clip_count(n_scenes)
    silence = structural_silence_seconds(clips, gap, end_hold)
    return (silence + clips * NARRATION_WORDS_MIN_FAIL * _SECONDS_PER_WORD,
            silence + clips * NARRATION_WORDS_MAX_FAIL * _SECONDS_PER_WORD)


class _Budget(dict):
    """Word budget with display rounding already applied.

    The numbers go into a prompt, so they are rounded to whole words here rather
    than at each call site - a prompt that says "34.3 spoken words" reads as
    false precision, and a site that rounds `min` up while another rounds `max`
    down can produce an empty band.
    """

    def __init__(self, raw: dict[str, float]) -> None:
        super().__init__(raw)
        self["words_min"] = max(NARRATION_WORDS_MIN_FAIL,
                                int(raw["per_clip_min"]))
        self["words_max"] = min(NARRATION_WORDS_MAX_FAIL,
                                int(raw["per_clip_max"]))
        self["words_total"] = int(raw["total"])
        self["clip_count"] = int(raw["clips"])
        if self["words_max"] < self["words_min"]:
            # Below the enforced floor the band is empty. Say so rather than
            # hand the model a min above its max.
            self["words_min"] = NARRATION_WORDS_MIN_FAIL
            self["words_max"] = NARRATION_WORDS_MIN_FAIL


def prompt_budget(n_scenes: int, target_minutes: float) -> _Budget:
    """The word budget as whole words, ready to interpolate into a prompt.

    A target too short for this scene count reports the enforced floor and
    `feasible == 0`, so the caller can name the shortfall instead of asking for
    a length no clip is allowed to use.
    """
    raw = word_budget(n_scenes, target_minutes * 60.0)
    return _Budget(raw)


def budget_feasible(n_scenes: int, target_seconds: float) -> bool:
    """Can `n_scenes` reach `target_seconds` without breaking the word contract?

    False when hitting the target would need a clip shorter than the enforced
    `tts_too_short_critical` floor, or longer than `tts_too_long_critical`. This
    is the check that a target below the floor must fail on, per the ruling
    that the pipeline hard-fails with the floor stated.
    """
    per_clip = words_for_target(n_scenes, target_seconds)
    return NARRATION_WORDS_MIN_FAIL <= per_clip <= NARRATION_WORDS_MAX_FAIL


class TargetBelowFloor(ValueError):
    """The requested duration cannot be reached at the planned scene count.

    Deliberately NOT a `RuntimeError`. `cli` catches `RuntimeError` from
    `plan_lesson` and treats it as an LLM flake to be resampled up to five
    times, so a hard fail raised as one would burn five plans before stopping -
    and would report a contract problem as a flaky model. This type is not
    caught there, so it stops the build at once and says what the floor is.
    """


def assert_target_reachable(n_scenes: int, target_minutes: float) -> None:
    """Stop the build when the target is unreachable at this scene count.

    The ruling was hard-fail with the floor stated, because the pipeline knows
    this before spending any LLM or TLM money and the user asked for a contract
    rather than a best effort. The message names the measured numbers rather
    than asserting infeasibility, so the reader can see which side failed: a
    target too SHORT needs fewer scenes, a target too LONG needs more words per
    clip than the TTS gate permits.
    """
    target = target_minutes * 60.0
    if budget_feasible(n_scenes, target):
        return
    per_clip = words_for_target(n_scenes, target)
    floor, ceiling = reachable_duration_band(n_scenes)
    if per_clip < NARRATION_WORDS_MIN_FAIL:
        reason = (f"it would need {per_clip:.1f} spoken words per clip, below "
                  f"the {NARRATION_WORDS_MIN_FAIL}-word floor the TTS gate "
                  f"enforces")
        remedy = (f"the shortest {n_scenes}-scene lesson is {floor / 60:.2f} min; "
                  f"use fewer scenes or a longer target")
    else:
        reason = (f"it would need {per_clip:.1f} spoken words per clip, above "
                  f"the {NARRATION_WORDS_MAX_FAIL}-word ceiling the TTS gate "
                  f"enforces")
        remedy = (f"the longest {n_scenes}-scene lesson is {ceiling / 60:.2f} min; "
                  f"use more scenes or a shorter target")
    raise TargetBelowFloor(
        f"--minutes {target_minutes:g} is unreachable for {n_scenes} scenes: "
        f"{reason}. {remedy}.")


def word_budget(n_scenes: int, target_seconds: float,
                gap: float = GAP_SECONDS,
                end_hold: float = END_HOLD_SECONDS) -> dict[str, float]:
    """The word budget a plan must hit, and the band that keeps it acceptable.

    `per_clip` is what lands the lesson on its declared target. The min and max
    are NOT invented tolerances: they are the word counts at which
    `duration_verdict` leaves its OK zone, i.e. the widest band the gate itself
    will call acceptable. A prompt asking for more than `per_clip_max` is asking
    for a finding, and one asking for less than `per_clip_min` is asking for the
    other one.

    The per-clip bounds are additionally clamped to the enforced word contract,
    so a target so short that its band would sit below `tts_too_short_critical`
    reports the floor rather than a number no clip may legally use.

    On mod03_gates_v013 (9 scenes, 4.0 min) this returns per_clip 34.3, band
    31.0-40.5, total 343 - against a shipped mean of 52.9 words/clip and 529
    words, which is where the 148% came from.
    """
    clips = clip_count(n_scenes)
    silence = structural_silence_seconds(clips, gap, end_hold)
    target = words_for_target(n_scenes, target_seconds, gap, end_hold)
    low_total = (BAND_OK * target_seconds - silence) / _SECONDS_PER_WORD
    high_total = (BAND_OK_HIGH * target_seconds - silence) / _SECONDS_PER_WORD
    return {
        "per_clip": target,
        "per_clip_min": max(NARRATION_WORDS_MIN_FAIL, low_total / clips),
        "per_clip_max": min(NARRATION_WORDS_MAX_FAIL, high_total / clips),
        "total": target * clips,
        "clips": float(clips),
        # Stated so the prompt can name the shortfall instead of implying the
        # requested length is reachable.
        "feasible": 1.0 if budget_feasible(n_scenes, target_seconds) else 0.0,
    }


def duration_verdict(ratio: float) -> tuple[str, str]:
    """Band a delivered/target duration ratio into (label, finding code+text).

    Labels are descriptive, not severities. These bands are advisory - the
    remedy is source-grounded teaching, which no mechanical step can supply - so
    an earlier version printing "[FAIL]" and then carrying on to write the deck
    was incoherent, the mirror image of a soft finding that announced
    "proceeding anyway" and then refused the build.
    """
    if ratio < BAND_LOW:
        return "SHORT", ("lesson_duration_critical_short: the render reaches only "
                        f"{ratio:.0%} of the declared target, so the lesson does "
                        "not meet its stated format")
    if ratio < BAND_OK:
        return "SHORT", ("lesson_duration_short: the render is materially under "
                        f"target at {ratio:.0%}. Add source-grounded teaching - "
                        "never padding")
    if ratio > BAND_HIGH:
        return "LONG", ("lesson_duration_critical_long: the render reaches "
                        f"{ratio:.0%} of the declared target, which is a pacing "
                        "defect rather than extra teaching")
    if ratio > BAND_OK_HIGH:
        return "LONG", ("lesson_duration_long: the render runs long at "
                        f"{ratio:.0%} of target; trim selectively rather than "
                        "across the board")
    return "OK", ""
