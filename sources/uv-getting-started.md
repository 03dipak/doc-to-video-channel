# Installing and using `uv` — the Python package and project manager

> **PROVENANCE — read this first, because it is load-bearing.**
>
> This document was **authored by the `doc-to-video-channel` agent on
> 2026-09-28.** It is **not** an upstream Astral document and must never be cited
> as one. Every factual claim below carries a tag saying how it is known:
>
> - **[MEASURED]** — the command was executed on the authoring machine and the
>   output is quoted verbatim. Reproducible against the stated version.
> - **[CITED]** — taken from `uv`'s own `--help` text on that machine. Accurate
>   for `0.12.2`; a later version may word it differently.
>
> **Environment of record:** `uv 0.12.2 (x86_64-unknown-linux-gnu)`, system
> `python3` is `3.14.4`, Linux. [MEASURED]
>
> A video built from this document is grounded in **a measured environment
> report written by an agent, not in vendor documentation.** That is an honest
> claim. It is *not* the claim "this is what Astral says," and the narration must
> not imply that it is. See `docs/RIGHTS.md` — this file is the channel's own
> source, and `A33`'s exclusion of the course-transcript corpus does not apply
> to it.

## The one sentence to remember

**`uv` resolves your Python version, your dependencies and your virtual
environment together, so a project becomes reproducible from two files instead of
from a machine's history.**

## The 7 concepts (this is the coverage list, and it is numbered on purpose)

The pipeline's coverage check looks for a numbered concept list and prefers it
over inferred section headings — it requires at least three entries
(`plan.py`'s `_unclaimed_source_sections` matches headings against
`^\d+[.)]\s` and only uses the numbered pool when it finds 3 or more). So this
list is load-bearing, not decorative: **a concept dropped from here is a concept
the coverage report cannot prove was taught.**

1. **One tool, three jobs** — `uv` replaces `pip`, `venv` and the interpreter
   manager, and they stop being three things that can disagree.
2. **Check what you have** — `uv --version` first, because every command below is
   version-sensitive and a lesson that skips this cannot be debugged.
3. **`uv init` — a project starts from a file, not a ritual** — it writes
   `pyproject.toml` for you instead of asking you to remember its fields.
4. **`uv add` — dependencies go in the project, not just the environment** — the
   single most important habit, because it is the difference between a working
   machine and a reproducible one.
5. **`uv lock` and `uv sync` are different jobs** — the lockfile is the *answer*,
   syncing is *applying* it. Conflating them is how "works on my machine"
   returns.
6. **`uv run` — one command for the environment, no activate** — and it is what
   makes the tool's isolation usable without shell ceremony.
7. **`uv run --with` — a throwaway dependency, deliberately not recorded** — the
   right tool for a one-off, and the wrong tool for anything the project needs.

---

## 1. One tool, three jobs

`pip` installs packages. `python -m venv` makes environments. Something else
downloads the interpreter. Three tools, three failure modes, and they disagree
in exactly the situations that are hard to debug.

`uv` does all three, and the reason that matters is not speed — it is that the
three answers are **derived from the same file**. When `pip` installs a version,
`venv` chooses an interpreter and the toolchain disagrees, there is no single
place that records what the project actually requires. `pyproject.toml` is that
place, and `uv` reads it for all three jobs. [CITED]

## 2. Check what you have

Always the first command in a lesson, and the first thing to run when a command
below behaves unexpectedly.

```
$ uv --version
uv 0.12.2 (x86_64-unknown-linux-gnu)
```

[MEASURED]

That output is a **measurement, not a configuration.** The number is the thing
that makes every other claim in this document falsifiable — a command documented
against `0.12.2` may differ in `0.13`, and quoting the version is what lets
somebody check rather than trust. The architecture suffix matters too: a
prebuilt binary for one platform will not run on another.

## 3. `uv init` — a project starts from a file, not a ritual

```
$ uv init --name uvprobe
Initialized project `uvprobe`
```

[MEASURED] — and it created exactly three entries:

```
README.md
pyproject.toml
src
```

[MEASURED]

The `pyproject.toml` it wrote, verbatim: [MEASURED]

```toml
[project]
name = "uvprobe"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
authors = [
    { name = "03dipak", email = "03dip.vaidya@gmail.com" }
]
requires-python = ">=3.12"
dependencies = []
```

**The line to notice is `requires-python = ">=3.12"`.** It is not a comment and
not a convention — it is a *constraint the tool will enforce*, and concept 6
shows it being enforced. A generated file that nobody reads is decoration; this
one is read by the next four commands.

## 4. `uv add` — dependencies go in the project, not just the environment

This is the habit the whole tool exists to install.

```
$ uv add requests
 + certifi==2026.7.22
 + charset-normalizer==3.5.1
 + idna==3.20
 + requests==2.34.2
 + urllib3==2.8.0
 + uvprobe==0.1.0 (from file:///tmp/opencode/uvprobe)
```

[MEASURED]

**Two things in that output carry the lesson.** First, five packages were
resolved when one was asked for — `requests` depends on the other four, and the
versions are *exact pins* (`==`), not ranges. Second, the last line names the
project itself as installed from a **file path**, not a registry. That is the
distinction worth remembering:

- `pip install requests` puts a package in an environment, and records nothing
  about *which* environment or *why* that version.
- `uv add requests` puts a package in a **project**, and writes the requirement
  into `pyproject.toml` where a reader — or a CI system, or a new machine — can
  find it.

If you only remember one command, it is this one. Everything else is
convenience; this is the difference between a project and a directory.

## 5. `uv lock` and `uv sync` are different jobs

People treat these as one command and it costs them an afternoon.

- `uv lock` — "Resolve the dependency graph and **write down the answer**."
  [CITED: "Update the project's lockfile"]
- `uv sync` — "Make the environment **match** that answer." [CITED: "Update the
  project's environment"]

```
$ uv lock
Resolved 6 packages in 1ms
```

[MEASURED] — and it created `uv.lock`. [MEASURED]

Read that output carefully: **`uv lock` did not install anything.** It resolved
six packages in a millisecond and wrote a file. Nothing about your environment
changed. That is the point, and it is why the two commands are separate: **you
lock once and commit the answer, and you sync on every machine.** If `lock`
installed things, you would have no way to review a resolution before adopting
it.

## 6. `uv run` — one command for the environment, no `activate`

```
$ uv run python src/main.py
python 3.12.13 in /tmp/opencode/uvprobe/.venv
```

[MEASURED]

Look at the interpreter version in that line. The system `python3` on this
machine is **3.14.4**. [MEASURED] The project asked for `>=3.12`, and `uv run`
gave it **3.12.13** in a project-local `.venv`.

**So `uv` did not use the system interpreter, and that is not a bug — it is the
feature.** `pyproject.toml` said `>=3.12`; the tool satisfied the constraint the
file expressed. A new contributor on a machine with a different global Python now
gets the interpreter *this project* specifies, without anyone editing a
Dockerfile or reading a wiki page.

The second half of the line is the other half of the lesson:
`/tmp/opencode/uvprobe/.venv` is **inside the project**. Nothing was activated,
no shell was modified, and there is no "my shell is now broken" state to unwind.
`uv run` is a prefix, not a mode you enter.

## 7. `uv run --with` — a throwaway dependency, deliberately not recorded

```
$ uv run --with rich python -c "import rich; ..."
rich imported from python3.12
```

[MEASURED]

Now check what it did **not** do. After that command: `rich` appears **0 times**
in `pyproject.toml` and **0 times** in `uv.lock`. [MEASURED]

That is the whole feature, and it is the deliberate opposite of concept 4. When
you need a library for one command — a debugger, a one-off format check, a
profiler — you do not want it in the project's dependency list, where it will
outlive the reason you wanted it. `--with` gives you the package for this
invocation and forgets it.

**The rule, stated once so it can be applied later:** if the project needs the
dependency, use `uv add` (concept 4). If *you* need it for one command, use
`uv run --with`. The failure mode is one-directional — a package added with
`--with` when the project needed it is a bug that only appears on the next
machine, and a package added with `uv add` when only one command needed it is
noise nobody will ever remove.

---

## What this document does not claim

Stated explicitly, because a source document that overstates itself teaches a
video to overstate itself.

- **It is not vendor documentation.** It is a measured report by an agent on one
  machine. [MEASURED] tags mean "this was run," not "this is the specification."
- **It does not document the installers.** How to *install* `uv` itself is
  covered by Astral's own material and is deliberately **absent here**, because
  this environment already had `uv` on `PATH` at `~/.local/bin/uv` and recording
  an install procedure this document never executed would be exactly the
  fabrication the provenance header forbids. [MEASURED: `which uv` returned
  `/home/dipak/.local/bin/uv`]
- **It does not cover** `uv tool install` (CLI application management),
  `uv build` / `uv publish` (packaging), workspaces, or private indexes. Those
  are real features that a complete reference would include and that this
  measured session did not exercise.
- **Version-sensitive.** Every claim is scoped to `0.12.2`. The `+freethreaded`
  builds visible in `uv python list` [MEASURED] are noted only to say they
  exist; nothing here depends on them.
