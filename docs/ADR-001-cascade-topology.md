# ADR 001 — Cascade topology stays distributed (for now)

**Status:** Accepted
**Date:** 2026-05-08

## Context

The control plane has historically had a `chain_config.py` file that *described* the agent cascade topology (news → scorer → analyst → seat) but was **never imported or executed**. The actual cascade is hardcoded inside each agent's graph:

- `scorer_agent`'s graph POSTs to `/agents/analyst_agent/tasks` after scoring
- `analyst_agent`'s `chain_to_seat` node POSTs to `/agents/seat_agent/tasks` per constituency tagged on the article
- `signals_analyser` does NOT cascade — its outputs are picked up lazily by seat_agent's next run (within a 14-day recency window)

This created a documentation hazard: the file looked authoritative but was decorative. Reading the codebase suggested cascade logic was centralised when it was not.

## Decision

**Delete `control_plane/chain_config.py`. Do not centralise the cascade in control_plane at this time.**

The cascade remains distributed: each agent's LangGraph defines its own downstream dispatch. Cascade topology is documented in `README.md` (Architecture section) rather than in code.

## Rationale

The current distributed model works because the cascade has only two shapes:

- **News pipeline** — synchronous 4-stage cascade (news → scorer → analyst → seat)
- **Signals pipeline** — single-stage with lazy pickup (signals → seat reads later)

Centralising this would require:
- A payload-transformation layer (today `analyst_agent.chain_to_seat` extracts `constituency_codes` from the article and fans out N seat_agent tasks — this is non-trivial logic, not just "dispatch the next agent")
- A condition evaluator with DB access (`score >= 40`, `score >= 60`, etc. are evaluated inside agent code today)
- 1–2 days of refactoring for value that mostly accrues to developer ergonomics

The misleading-documentation concern is better addressed by a clear cascade diagram in README.md than by load-bearing code that nothing currently needs.

## Revisit trigger

**Revisit this decision if any of the following happen:**

1. **3+ new source types of varied shape are onboarded** (e.g. polling data, official documents, video transcripts, citizen reports). At that point the "edit blast radius" of distributed cascading compounds, and a Python-rule-based cascade subsystem in control_plane becomes the better design.
2. **Conditional gating becomes a recurring requirement** — e.g. "only cascade if poll sample size > 800 AND tier-1 pollster". Each new gating rule today requires editing the upstream agent's graph and rebuilding its container.
3. **Multi-instance agent replicas are deployed** and routing decisions need awareness of replica state beyond the registry's `task_count`.
4. **A cascade test suite is wanted.** Mocking distributed cascades is harder than mocking a single cascade engine.

If revisiting, the suggested design is a small `cascade.py` module in control_plane with rule functions (Python, not config), called by `_stream_task` after each task completes. Each rule returns a list of `CascadeAction` objects that the dispatcher executes. Avoids the DSL trap and supports fan-out + conditions natively.

## Consequences

**Positive:**
- One less misleading file in the repo
- README.md becomes the authoritative source for cascade topology
- No premature abstraction for hypothetical scope

**Negative:**
- Adding the third source type will require either accepting more agent-code edits or doing the cascade refactor under deadline pressure rather than ahead of time
- New contributors must read multiple agent graphs to understand the cascade (mitigated by README diagram)

## References

- `README.md` — Architecture section documents the current cascade
- `agents/scorer_agent/graph.py:211` — scorer → analyst dispatch
- `agents/analyst_agent/graph.py:300-314` — analyst → seat fan-out
- `agents/signals_analyser/graph.py` — terminates without cascade (lazy seat pickup)
