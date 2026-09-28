"""Filesystem helpers (atomic json write, progress bar, document loading)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

_SECTION_HEADING_RE = re.compile(r"(?m)^#{1,6} ")


def file_digest(path: Path) -> str:
    """SHA-256 of a file's bytes, or "" when it cannot be read.

    Used to bind an artifact to the exact input it describes. A path is display
    metadata - it can be copied, renamed, or point at a different file - so
    identity has to come from content. See `check_audit_binding`.
    """
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 16), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def atomic_json_write(path: Path, data: dict) -> None:
    """Write JSON atomically (tmp file + fsync + rename) so a crashed write
    never leaves a truncated .plan.json / .audit.json behind. Same-directory
    rename keeps the move atomic on POSIX."""
    tmp = path.with_name(f".{path.name}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
class _Progress:
    def __init__(self, stage: str, total: int):
        self.stage = stage
        self.total = total
        self.start = time.monotonic()
        self._tick(0)

    # V1: annotated. The baseline ships this untyped, and `mypy src` runs
    # strict here, so a copy inherits the debt or the gate is weakened to
    # hide it. Two annotations are cheaper than either.
    def _tick(self, done: int) -> None:
        elapsed = time.monotonic() - self.start
        frac = done / self.total if self.total else 0
        bar_len = 20
        filled = int(bar_len * frac)
        bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
        if done > 0 and self.total > 1:
            per_item = elapsed / done
            eta = int(per_item * (self.total - done))
            eta_str = f"{eta // 60}m {eta % 60:02d}s" if eta else "done"
        else:
            eta_str = "..."
        print(
            f"\r  [{self.stage}] |{bar}| {frac:5.0%}  elapsed {elapsed:.0f}s  ETA {eta_str}   ",
            end="", flush=True,
        )

    def done(self) -> None:   # V1: annotated, same reason
        elapsed = time.monotonic() - self.start
        print(f"\r  [{self.stage}] \u2713  done in {elapsed:.0f}s{' ' * 40}", flush=True)
def _wait_before_retry(failed_samples: int) -> None:
    """Jittered exponential backoff between failed LLM sample retries.

    The free 7B hub is bursty: hammering it after a parse failure tends to
    re-trigger the same 429/500. Wait 1.5s, 3s, 6s, then cap at 12s (with
    +/- 25% jitter) so consecutive samples spread out.
    """
    delay = min(1.5 * (2 ** min(failed_samples, 3)), 12.0)
    jitter = 0.25 * (2 * (time.monotonic() % 1.0) - 1.0)
    time.sleep(max(0.25, delay * (1 + jitter)))


@dataclass(frozen=True)
class LoadedSource:
    """A loaded document, plus an exact account of what the read window dropped.

    `text` is what the planner is allowed to see. `full_text` is what the files
    actually held. They are the same string when nothing was dropped, and the
    gap between them is the point: `chars_total - chars_read` is a measured
    number, so coverage can be reported against the real document instead of
    against the part of it that happened to fit. That distinction is what turned
    a 9-of-12 lesson into a printed "all concepts covered".
    """
    text: str
    full_text: str
    chars_read: int
    chars_total: int
    read_window: int

    @property
    def truncated(self) -> bool:
        return self.chars_read < self.chars_total


def _truncate_on_boundary(text: str, max_chars: int) -> str:
    """Cut `text` to at most `max_chars` without ever splitting a word.

    Replaces a raw `text[:max_chars]`. Measured on
    `modules/08_concepts_mod03_gates.md` (17,975 chars against a 12,000-char
    window): that slice ended inside "violation)", and since the caller appends
    its own `</doc>` wrapper immediately after the body, the last scene's
    `source_chunk` shipped as `"...var is a violati\\n</doc>"` - a broken word
    and a leaked tag in the same five characters. Both were one cause.

    Preference order:
      1. the last section heading at or before the limit, so what survives is
         whole sections;
      2. otherwise the last line break or space in the window.

    Option 1 is skipped when it would keep less than half the window: that
    means the document is a single section longer than the window, and retreating
    to its one lone heading would discard the budget for nothing. Both branches
    end on a boundary, so neither can split a word.

    A window containing no line break and no space at all means the text is one
    unbroken token; there the window stands rather than returning nothing, and
    the caller reports the cut either way.
    """
    if len(text) <= max_chars:
        return text
    head = text[:max_chars]
    starts = [m.start() for m in _SECTION_HEADING_RE.finditer(head)]
    cut = starts[-1] if starts and starts[-1] * 2 >= max_chars else 0
    if not cut:
        cut = max(head.rfind("\n"), head.rfind(" ")) + 1
        # V1 / AC#17(a): the half-window floor applies to the HEADING preference
        # above but was missing here, so the space fallback could return almost
        # nothing. Measured on a boundary-free 40,026-character body inside a
        # wrapper whose only space sits at offset 4: a 12,000-character window
        # yielded **18** characters -- 0.15% of the window, and the ratio gets
        # WORSE as the window grows (0.018 at 1,000, 0.0015 at 12,000). The
        # document was effectively one unbroken token, which is precisely the case
        # the docstring says should let "the window stand".
        #
        # This is a trade and the trade is recorded: a cut that splits a word is a
        # smaller harm than discarding 99.85% of the input. The two AC#17(a)
        # properties are UNSATISFIABLE together when the text has no boundary near
        # the window, so the floor wins and the caller reports the cut either way.
        if cut * 2 < max_chars:
            cut = 0
    return text[:cut].rstrip() if cut else head


def load_documents(paths: list[str], max_chars: int = 12000) -> LoadedSource:
    """Read the inputs under one read window, and report what it excluded.

    A single boundary-aware cut is applied to the joined text. There is
    deliberately no second cap: the previous version sliced each file to
    `max_chars` and then the join to `max_chars * 4`, which is two independent
    silent truncations of the same input at two different units, and only the
    first one was ever reported.
    """
    parts: list[str] = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Input not found: {path}")
        if p.suffix.lower() in (".pptx", ".ppt"):
            body = _load_pptx(p)
        elif p.suffix.lower() in (".docx", ".doc"):
            body = _load_docx(p)          # A5
        else:
            body = p.read_text(encoding="utf-8")
        parts.append(f"<doc name='{p.stem}'>\n{body}\n</doc>")
    full_text = "\n\n".join(parts)
    text = _truncate_on_boundary(full_text, max_chars)
    return LoadedSource(text=text, full_text=full_text, chars_read=len(text),
                        chars_total=len(full_text), read_window=max_chars)


# --- A5: the .docx reader. THE FIRST CHANNEL EDIT TO VENDORED CODE. ----------
#
# Reproduced 2026-09-28 against the baseline: `load_documents` raises
# `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xab in position 10` on a
# real .docx, because a .docx is a ZIP of XML rather than text. `python-docx` was
# already a declared dependency and was never used here.
#
# Two things a naive reader gets wrong, both measured rather than assumed:
#   * TABLES. A specification document puts most of its content in tables, and
#     `Document.paragraphs` does not include them -- a reader that reads only
#     paragraphs returns a document whose tables have silently vanished, and a
#     vanished table is a gap the coverage report cannot see.
#   * EMPTY. A .docx with no readable text is a failure, not an empty document, so
#     it raises rather than contributing a blank <doc> block.
def _load_docx(p: Path) -> str:
    from docx import Document

    doc = Document(str(p))
    parts: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            style = (para.style.name if para.style is not None else "") or ""
            parts.append(f"# {text}" if style.startswith("Heading") else text)
    for ti, table in enumerate(doc.tables, 1):
        rows = [
            " | ".join(cell.text.strip() for cell in row.cells)
            for row in table.rows
            if any(cell.text.strip() for cell in row.cells)
        ]
        if rows:
            parts.append(f"--- Table {ti} ---\n" + "\n".join(rows))
    joined = "\n\n".join(parts)
    if not joined.strip():
        raise ValueError(f"No readable text found in {p}")
    return joined


def _load_pptx(p: Path) -> str:
    from pptx import Presentation

    prs = Presentation(str(p))
    parts: list[str] = []
    for i, slide in enumerate(prs.slides, 1):
        texts = [
            shape.text_frame.text.strip()
            for shape in slide.shapes
            if shape.has_text_frame and shape.text_frame.text.strip()
        ]
        if texts:
            parts.append(f"--- Slide {i} ---\n" + "\n".join(texts))
    joined = "\n\n".join(parts)
    if not joined.strip():
        raise ValueError(f"No slide text found in {p}")
    return joined


def _text_digest(text: str) -> str:
    """Short content digest of a source section, for provenance.

    Lives here rather than in `plan.py` because `plan` imports `narration`, so
    anything provenance-related that the narration repair also needs would be
    unreachable from there. `hashlib` was already imported for `file_digest`.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def verified_source_chunk(plan: dict, scene_no: int) -> str:
    """The scene's `source_chunk`, but only if it still matches the record.

    Defect 2d. Every deterministic repair that hydrates from source - the
    thin-narration rebuild and the starved-scene bullet top-up - reads
    `sc["source_chunk"]` directly. That field is mutable and unverified, so a
    plan whose assignment moved on while the chunk did not would feed another
    section's prose straight into the audio: no finding, no log line, and a
    narration that is grounded in the wrong paragraph.

    `section_digest` proves which section was assigned but cannot be recomputed
    from the chunk, so assignment records also carry `chunk_digest` - a digest of
    the chunk itself, written at the same moment.

    Returns "" when there is no record or the digest disagrees, so callers fall
    back to their existing behaviour instead of trusting a chunk they cannot
    vouch for. A plan written before `chunk_digest` existed is passed through
    unverified rather than rejected: the field is absent, not wrong, and
    refusing it would invalidate every artifact already on disk.
    """
    scenes = plan.get("scenes") or []
    if not (1 <= scene_no <= len(scenes)):
        return ""
    chunk = str(scenes[scene_no - 1].get("source_chunk") or "").strip()
    if not chunk:
        return ""
    record = next((a for a in (plan.get("source_assignment") or [])
                   if a.get("scene") == scene_no), None)
    if not record:
        # No record is not the same as a contradicted one. There is nothing for
        # the chunk to disagree with, and refusing it would break legitimate
        # plans - a hand-built scene, or one predating source assignment
        # entirely. The defect this guards is a MISMATCH, and that is caught
        # below. An existing test caught the over-strict version.
        return chunk
    recorded = record.get("chunk_digest")
    if not recorded:
        return chunk
    return chunk if _text_digest(chunk) == recorded else ""
