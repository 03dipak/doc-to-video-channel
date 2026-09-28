# V-1 spike source: install and verify uv

> A FIXTURE source for the V-1 render spike, not a lesson and not a real document.
> It exists so the plan can derive its protected terminology the same way a real
> plan does, by passing text through `_persist_protected_trigrams`. Without it a
> plan gets NO terminology protection, and the trigram gate then forbids the natural
> repetition of technical phrases like `command -v uv` across five scenes about one
> tool.

## The check

Run `uv --version`. It prints a version and the platform it was built for, such as
`uv 0.12.2 (x86_64-unknown-linux-gnu)`. Every later command is version sensitive.

## The install

`curl -LsSf https://astral.sh/uv/install.sh | sh`, from Astral's installation page
dated 2026-09-24. The installer writes `uv` and `uvx` into `~/.local/bin` and adds
that directory to the shell profile. A version-pinned URL is available.

## The PATH trap

A shell opened before the profile was edited has not reread it, so `uv --version`
reports `uv: not found` even though the install succeeded. `bash -lc 'command -v uv'`
reads the profile and prints `~/.local/bin/uv`. The docs say: "Then restart the
shell or source the shell config file."

## The version, recorded

`uv --version` succeeds in a new shell. Below `0.5.0` the installer used
`~/.cargo/bin`, and uninstalling removes `~/.local/bin/uv ~/.local/bin/uvx`.
