"""Vendored pipeline modules, byte-identical to `VENDOR_REF` except where recorded.

**This package marker re-exports nothing, and that is the point.**

The baseline's `studio/__init__.py` is a **re-export facade**: its whole job is to
let callers write `from doc_to_video_tutor import studio as S`. §5.1 row 18 drops
it, and the reason it is dropped is that a facade is a **second import path** to
every module in the tree -- the defect the LLD records as "a method with two
spellings is how a type drifts". Deleting the facade is a real decision and it
stands.

Creating this *directory* is a separate decision from dropping the *facade*, and
conflating them is where the LLD went wrong: it concluded "no `studio/`
subpackage" from a premise about re-exports. This file is the counter-example --
a package marker with a docstring and zero re-exports, so every module has exactly
one import path, `doc_to_video_channel.studio.<name>`.

**Why the directory is worth having:**

* **Provenance is visible.** Everything in here came from the baseline; the four
  modules beside this package are ours. In a flat layout that distinction is
  something a reader has to know.
* **It forecloses a class of collision.** V5 brings `cli.py`, `plan.py` and
  `config.py`. Today none of those clash with `storyboard.py`, `harness.py` or
  `vendor.py`, but nothing in the design prevents a future original module from
  being named `cli.py` and colliding with a vendored one.
* **Relative imports keep working either way**, so this is not a correctness
  change. `from .util import` in a vendored `plan.py` resolves to
  `doc_to_video_channel.studio.util` here and to `doc_to_video_tutor.studio.util`
  there. Verified, not assumed.
"""
