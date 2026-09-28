# V-1 render spike -- results

Run 2026-09-28. Reproduce: `../doc-to-video-tutor/.venv/bin/python spikes/run_v1.py`

## The render path works

Five artefacts, produced by calling the baseline's `_render_media` directly:

| artefact | size | notes |
|---|---|---|
| `v1_install.mp4` | 18.0 MB | 172.6 s, 1280x720, h264 + mp3, 2 streams |
| `v1_install.pptx` | 36.6 KB | the deck |
| `v1_install.vtt` | 2,971 B | **40 cues** -- only present because the spike calls `_render_media` |
| `v1_install.word_timings.json` | 31.8 KB | 5 clips, 303 word-boundary tokens |
| `v1_install_audio/` | 5 clips | per-scene audio kept |

**Why `_render_media` and not the CLI.** Measured: the gate
(`_render_blocking_problems`) is called in `cli.main`'s branch and **not inside
`_render_media`**. So calling it directly bypasses the gate while keeping the whole
render path, including the `_write_webvtt` call. Going through the CLI would run
the gate, and a spike that exists to test the *render* path must not be blocked by
a plan-quality gate.

## The four AC#30 instruments

| # | instrument | result |
|---|---|---|
| 1 | caption glyph height | **NOT MEASURABLE.** Burn-in lands at V5 (D1). Re-confirmed: the `.vtt` carries **0 `::cue`** and **0 `STYLE`**, so no font size is declared anywhere. |
| 2 | caption/command bbox disjointness | **NOT MEASURABLE**, same reason. The 2-stream MP4 has no subtitle track. |
| 3 | loudness on the **published** file | **PASS.** `-16.7 LUFS`, `-5.2 dBFS`. D2's band is `-16.0 ±1.0 LU` (0.7 inside) and the peak ceiling is `≤ -1.5 dBTP` (3.7 under). |
| 4 | narration speaks what is on screen | **PARTIAL, and the instrument itself is not buildable as written.** See below. |

## Instrument 4: two wrong instruments, then a real limit

Measured in three passes, and the first two were mine being wrong:

1. *"Every clip must name `uv`"* -- **wrong.** Clip 2 is the install scene; its
   command is `curl ... | sh` and the narration correctly says *"curl, dash,
   capital L, small s... piped into sh"*. It names the installer, not the tool.
2. *"The narration must contain every token of the command"* -- **wrong the other
   way.** It demanded `astral.sh`, `https`, `install.sh`. Saying *"Astral's
   installer"* is the correct way to speak a URL.
3. *"The program and subcommand must be spoken; a URL may be a name"* -- **correct
   in principle, and still reports 2 false failures:** `-LsSf` and `-lc`. The
   narration says *"capital L, small s, capital S, small f"* and *"dash, l, c"*,
   which **is** speaking them. A mechanical token comparison cannot know that a
   spelled-out flag is the flag.

**Conclusion, not a fourth attempt:** narration-versus-screen cannot be checked by
token matching. It needs either a spelling-aware normaliser, or a human. The
baseline already treats it as a `soft_finding` ("the slide shows X but the
narration never mentions them"), and that is the right severity for a check that
cannot be made exact. **A mechanical version of this instrument is deferred**, and
the honest statement is that `AC#30` instrument 4 is verified for 4 of 5 scenes by
hand, not by a gate.

## Two findings the spike produced

### F1. The trigram gate and narration-versus-screen are structurally incompatible

Instrument 4 requires the narration to **name the command**. The trigram gate
forbids a repeated 3-word phrase. Naming the command three times produces three
repeated 3-grams -- measured: `run uv dash` x3, `uv dash dash` x3, `dash dash
version` x3.

Removing the repetition to satisfy the gate produced *"try that same check once
more"*, which a learner listening rather than looking cannot act on. The gate was
right that the prose repeated and wrong about what to do about it.

**Required before any real video:** the trigram ban must apply to **prose**, not to
a command the storyboard declares on screen. The gate must skip windows falling
inside a declared command string. Until then a practical session cannot be
narrated correctly.

### F2. `_entity_tokens` does not recognise short lowercase tool names

Measured against the fixture source: `uv`, `curl`, `astral`, `uvx`, `sh` and `bash`
are **all** absent from the recognised entity set, while `0.12.2`, `~/.local/bin/uv`
and `https://astral.sh/uv/install.sh` are present. So the one term a `uv` tutorial
repeats most gets **no** terminology protection from `_persist_protected_trigrams` --
the mechanism that exists precisely to stop the repeat gate deleting terminology.

This is why F1 could not be worked around by source-derived protection. It is a
baseline defect a vendored copy inherits, and it belongs in the ledger.

## Declared deviation

The fixture carries a `V1_TRIGRAM_EXEMPTION` block, and `run_v1.py` **prints it and
renders anyway**. The exemption is F1, it is scoped to the spike, and it is not a
precedent. A silent bypass would be the defect this project keeps recording.
