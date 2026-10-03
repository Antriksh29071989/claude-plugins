# ADR 0001: Run the ReAct loop in-process with an append-only event log

- Status: Proposed
- Date: 2026-10-03

## Context

We need a production runtime for a ReAct agent serving ~100,000 runs/day: 90% interactive (about 6 steps, 30 s), 10% long-running (about 40 steps, 10 min). Peak load is ~370 concurrent runs and ~45 model calls/s. Tools are read-only lookups. The team is 2-5 engineers on a managed cloud.

Ranked drivers: reliable completion, cost per run, interactive latency, operability by a small team, containment of untrusted tool output.

Estimates show model spend ($216k-$718k/month depending on tier) is over 98% of total cost and that prompt caching changes it by about 5x. Platform cost differs between options by a few thousand dollars a month. The first scalability limit in every design is the model provider's rate limit.

Because tools are read-only, repeating a step after a crash has no side effect.

## Decision

We will run the loop as plain async code in one deployable with two roles (API for interactive runs, queue-fed workers for long runs), and persist every step to an append-only, versioned event log in PostgreSQL. A lost run is resumed by replaying its log and redoing the single unfinished step. One writer per run is enforced by a queue lease plus a unique `(run_id, seq)` key.

The step function will be pure (no I/O) so the loop can later be hosted in a workflow engine without a rewrite.

## Alternatives considered

- **Durable workflow engine (Option 2).** Rejected for now: its main benefit, never re-executing a completed side effect, is not needed with read-only tools; it adds a hard dependency on every step, a determinism and versioning discipline, a streaming side channel, and 2-4 weeks of learning for a small team. It remains the planned destination when the triggers below fire.
- **Managed agent runtime (Option 3).** Rejected: gives up control of cache layout and context trimming, which drive 98% of cost; ties the product to one provider's beta surface; session-start latency for short interactive turns is unmeasured; pays for a per-session workspace that read-only tools do not use.

## Consequences

Positive
- Fewest moving parts; lowest per-step overhead (~15 ms).
- Full control over prompt prefix stability, trimming and budgets.
- No engine payload or history limits; native token streaming.

Negative
- We own lease, heartbeat and resume logic and must prove it with a kill-test at every event boundary.
- No built-in durable timers, signals or human-wait steps.
- Run inspection tooling must be built on our own traces and log.

Neutral
- Event schema and run API become long-lived contracts and must be versioned from the start.

## Revisit when

- A tool with side effects is planned.
- A run must wait on a human or last hours to days.
- Sub-tasks must fan out and join.
- More than one resume-path defect occurs in a quarter.
- Measured tokens per step differ from the estimates by more than 2x (re-run the cost model).
