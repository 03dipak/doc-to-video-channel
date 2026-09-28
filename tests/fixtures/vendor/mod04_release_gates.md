# Concept Field Guide — Mod 04: Release Gates

## The one sentence to memorize

A release gate is a check that runs *before* the artifact ships, and its verdict
is recorded whether it passes or fails.

## The 4 big ideas (everything else is detail)

- A gate is a function of the artifact, not of the author's intent.
- A gate that cannot fail is not a gate.
- Every verdict needs an owner, or nobody reads it.
- A gate that blocks without a repair is a wall, not a gate.

## Concept by concept

### 1. Gate versus check — the difference is the verdict

A check answers a question. A gate answers it *and acts on the answer*. A unit
test that prints "threshold drift" is a check. The same test wired into a
pipeline that refuses to build is a gate. The distinction is not severity, it is
whether the answer has consequences.

### 2. Fail closed, not fail open

A gate that cannot reach its verdict must refuse the release, not wave it
through. This is the difference between `missing dependency -> skip the check`
and `missing dependency -> refuse to ship`. Fail-open gates are the most
dangerous kind, because the failure looks like a pass.

### 3. The verdict must be reproducible

A recorded verdict is evidence only if re-running the gate on the same artifact
produces the same answer. This is what binds a verdict to the artifact it is
about: a digest, not a filename, because a file can be copied, renamed, or
replaced while keeping its name.

### 4. Every gate needs an owner

A gate whose failures nobody triages is worse than no gate, because it trains
the team to ignore red. Ownership is a name, not a team, and it is recorded
with the verdict.

### 5. Escalation is a policy, not a mood

Two gates failing at once is a different situation from one. The policy decides
whether the second is independent evidence or a symptom of the first. Deciding
that per-incident, under time pressure, is how a release ships broken.

### 6. A gate that blocks with no repair is a wall

If a verdict can refuse a build and nothing in the pipeline can resolve it, the
gate is a wall. Either the finding must be mechanically repairable, or the gate
must be advisory. Refusing without an escape is the worst of both: it stops the
build and teaches the team to route around the gate.

### 7. Silence is not a verdict

A gate that produces no output has not passed; it has failed to run. This is the
false-pass class, and it is the reason a verdict must be *recorded* rather than
merely absent. Absence of evidence is not evidence of absence.

### 8. Threshold drift is a defect, not a tuning knob

When a threshold is moved to make a build pass, the threshold changed meaning,
not the artifact. Record the move, or the next reader inherits a number whose
justification nobody remembers. Tuning it silently is how a gate stops gating.

### 9. The binding digest must cover what the verdict is about

A verdict bound to a digest of the *plan* is not bound to the verdict about the
*artifact* if the artifact is produced later. Bind to the bytes that were
measured. Otherwise swapping a plan under a passing audit inherits a clean bill
of health it never earned.

### 10. Gate ordering is a contract

If gate A invalidates what gate B checks, running B first means B validated a
stale state. Ordering is therefore part of each gate's definition, not an
implementation detail of the runner.

### 11. Advisory findings need a threshold too

"Advisory" with no numeric threshold is a mood. An advisory finding should state
the ratio or count at which it would become blocking, so the reader can judge
whether the advice matters for *this* artifact.

### 12. A removed gate leaves its assertion behind

When a gate is retired, the check it performed is usually still correct. Deleting
the gate without moving the check into a test turns a recorded guarantee into an
assumption, and nobody notices until the guarantee is needed.

## Checkpoints (how you know you understood it)

- Can you state, for one gate you own, what it does when it cannot reach a
  verdict?
- Can you name a gate in this codebase that blocks with no repair?
- Can you explain why a filename is not a binding?

## Now read the field guide for the next module
