# Option 1 - Event-logged loop in one service

## Thesis

Run the ReAct loop as ordinary async code inside one deployable, and make it crash-safe by appending every step to an append-only event log in PostgreSQL. Interactive tasks run in the API process and stream straight to the user; long tasks run the *same* loop in a worker pool fed by a managed queue. Recovery is "reload the log, redo the step that was in flight". That is only safe because every tool is read-only: repeating a lookup has no side effect, so at-least-once execution is good enough and no workflow engine is needed. The trade: the team owns a small amount of recovery machinery (leases, heartbeats, resume) instead of renting it.

## Style and lineage

- **Style:** service-based / modular monolith - one codebase, two process roles (Richards & Ford, *Fundamentals of Software Architecture*, service-based style: high simplicity and cost ratings, moderate scalability and fault tolerance).
- **State model:** the run is an event-sourced log; current state is derived by replay (Kleppmann, *DDIA* 1st ed., ch. 11, event sourcing and logs as the source of truth).
- **Queue consumption:** competing consumers with an idempotent receiver (Hohpe & Woolf, *Enterprise Integration Patterns*).
- **Stability:** timeouts, circuit breaker, bulkheads, shed load, governor on every outbound call (Nygard, *Release It!*).

## Container view

```mermaid
C4Container
    title Container - Agent Platform (Option 1: event-logged loop)
    Person(user, "End User", "Asks questions and starts research tasks")
    System_Ext(llm, "LLM API", "Hosted model inference with streaming and tool calling")
    System_Ext(sources, "Data Sources", "Internal APIs, search indexes and databases behind read-only tools")
    System_Ext(idp, "Identity Provider", "Issues user tokens")
    System_Boundary(platform, "Agent Platform") {
        Container(client, "Client App", "Web or mobile", "Chat UI, renders streamed steps and answers")
        Container(api, "Agent API", "Python async service", "Auth, run lifecycle, runs interactive loops in-process, SSE streaming")
        Container(worker, "Task Worker", "Same image, worker role", "Runs long tasks pulled from the queue, heartbeats a lease")
        ContainerQueue(queue, "Task Queue", "Managed queue", "Long-task run ids with visibility timeout")
        ContainerDb(store, "Run Store", "PostgreSQL", "Runs and append-only step events, partitioned by day")
        ContainerDb(cache, "Stream and Limits", "Redis", "Per-run event streams for resume, LLM token buckets, tenant concurrency")
        ContainerDb(blob, "Artifact Store", "Object storage", "Large tool results and archived transcripts")
    }
    Rel(user, client, "Uses", "HTTPS")
    Rel(client, api, "Starts runs, subscribes to events", "HTTPS, SSE")
    Rel(client, idp, "Signs in", "OIDC")
    Rel(api, store, "Appends and reads step events", "SQL")
    Rel(api, cache, "Publishes run events, takes rate tokens", "RESP")
    Rel(api, queue, "Enqueues long runs", "HTTPS")
    Rel(worker, queue, "Leases run ids", "HTTPS")
    Rel(worker, store, "Appends and reads step events", "SQL")
    Rel(worker, cache, "Publishes run events, takes rate tokens", "RESP")
    Rel(api, llm, "Streams completions", "HTTPS")
    Rel(worker, llm, "Streams completions", "HTTPS")
    Rel(api, sources, "Read-only tool calls as the user", "HTTPS")
    Rel(worker, sources, "Read-only tool calls as the user", "HTTPS")
    Rel(worker, blob, "Stores large results", "HTTPS")
    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

| Container | Technology | Responsibility | Scales by | State |
|---|---|---|---|---|
| Agent API | Async Python (or TypeScript) on a managed container service | Auth, run lifecycle, interactive loop, SSE | Concurrent streams; add instances | Stateless |
| Task Worker | Same image, worker entrypoint | Long-task loop, lease heartbeat | Queue depth | Stateless |
| Task Queue | Managed queue (SQS-class) | Hand-off and redelivery of long runs | Managed | Run ids only |
| Run Store | Managed PostgreSQL, multi-zone | Source of truth: runs, step events | Vertical, then partition by day and archive | Durable |
| Stream and Limits | Managed Redis | Resume buffer, rate tokens, concurrency counters | Vertical | Ephemeral (rebuildable) |
| Artifact Store | Object storage | Tool results over 16 KB, archived runs | Managed | Durable |

## Component view

The loop lives in one library, `agent-core`, used unchanged by both process roles. This is where the decisions are.

```mermaid
C4Component
    title Component - agent-core (inside Agent API and Task Worker)
    ContainerDb(store, "Run Store", "PostgreSQL", "Runs and step events")
    ContainerDb(cache, "Stream and Limits", "Redis", "Streams and token buckets")
    System_Ext(llm, "LLM API", "Hosted model inference")
    System_Ext(sources, "Data Sources", "Read-only backends")
    Container_Boundary(core, "agent-core") {
        Component(ctrl, "Run Controller", "Async task", "Loads the log, owns the lease, drives steps until a stop condition")
        Component(loop, "ReAct Step", "Pure function", "State and model reply in, next action out. No I/O")
        Component(ctx, "Context Builder", "Module", "Cache-stable prefix, tail assembly, compaction of old tool results")
        Component(llmc, "LLM Client", "Module", "Streaming, timeouts, retry budget, rate tokens, circuit breaker, fallback model")
        Component(tools, "Tool Executor", "Module", "Schema validation, parallel calls, per-tool timeout, result truncation")
        Component(guard, "Guardrails", "Module", "Input and output checks, egress allowlist, tool-result quarantine markers")
        Component(budget, "Budget Governor", "Module", "Max steps, tokens, wall clock and cost per run and per tenant")
        Component(log, "Event Log", "Module", "Appends step events, publishes to the run stream, emits trace spans")
    }
    Rel(ctrl, loop, "Asks for next action")
    Rel(ctrl, ctx, "Builds request")
    Rel(ctrl, llmc, "Calls model")
    Rel(ctrl, tools, "Executes tool calls")
    Rel(ctrl, budget, "Checks before each step")
    Rel(ctrl, log, "Appends every event")
    Rel(tools, guard, "Screens arguments and results")
    Rel(llmc, llm, "Streams completions", "HTTPS")
    Rel(llmc, cache, "Takes rate tokens", "RESP")
    Rel(tools, sources, "Read-only calls", "HTTPS")
    Rel(log, store, "Inserts events", "SQL")
    Rel(log, cache, "Publishes events", "RESP")
```

Design rules that make this work:

- **`ReAct Step` is pure.** All I/O is in the controller. The same function can later be hosted inside a workflow engine (Option 2) without rewriting.
- **Append before acting on it.** A model reply is logged before its tool calls run; tool results are logged before the next model call. Resume re-executes at most one step.
- **The prefix never changes within a run.** System prompt and tool definitions are byte-stable and sorted so prompt caching hits; volatile data goes after the last cache breakpoint.
- **Hard stops.** Step, token, wall-clock and cost budgets end a run with a partial answer rather than looping.

## Critical flows

### Interactive run (budget: first token under 2 s, platform overhead under 50 ms per step)

```mermaid
sequenceDiagram
    title Dynamic - Interactive run, one ReAct step shown
    actor User
    participant Client as Client App
    participant API as Agent API
    participant Store as Run Store
    participant Redis as Stream and Limits
    participant LLM as LLM API
    participant Src as Data Sources
    User->>Client: Ask question
    Client->>API: POST /runs then GET /runs/id/events (SSE)
    API->>Store: Insert run and user event (5 ms)
    API->>Redis: Take rate tokens (1 ms)
    API->>LLM: Stream completion with cached prefix
    LLM-->>API: Reasoning and tool calls (first token 0.5 to 2 s)
    API-->>Client: Stream step progress
    API->>Store: Append model event (5 ms)
    par Parallel read-only tools
        API->>Src: Tool call A (timeout 5 s)
        API->>Src: Tool call B (timeout 5 s)
    end
    Src-->>API: Results
    API->>Store: Append tool result events (5 ms)
    Note over API,LLM: Loop repeats until the model answers or a budget stops it
    API->>LLM: Stream completion with results
    LLM-->>API: Final answer tokens
    API-->>Client: Stream answer
    API->>Store: Append final event, mark run done
```

### Long run surviving a worker crash

```mermaid
sequenceDiagram
    title Dynamic - Long run, worker lost mid-step
    participant API as Agent API
    participant Q as Task Queue
    participant W1 as Task Worker 1
    participant W2 as Task Worker 2
    participant Store as Run Store
    participant LLM as LLM API
    API->>Store: Insert run
    API->>Q: Enqueue run id
    Q->>W1: Deliver run id (visibility 60 s)
    loop Each step
        W1->>Q: Extend visibility (heartbeat every 20 s)
        W1->>LLM: Model call
        W1->>Store: Append events with expected sequence number
    end
    Note over W1: Worker killed by deploy or node loss
    Q->>W2: Redeliver after visibility timeout
    W2->>Store: Load events, rebuild state
    W2->>LLM: Redo the unfinished step
    W2->>Store: Append events with expected sequence number
    Note over W2,Store: A late write from Worker 1 fails the sequence check and is dropped
```

## Data design

- **Ownership:** only `agent-core` writes the Run Store. One writer per run at a time, enforced by the queue lease plus an optimistic check: `INSERT ... (run_id, seq)` with a unique key, so a zombie worker cannot fork the history.
- **Events, not snapshots.** Storing the full state at every step is quadratic: a 40-step run with ~55k tokens average context is about 8.8 MB per run, or 88 GB/day for long runs alone. Appending deltas is about 0.44 MB per long run, 8 GB/day in total.
- **Partitioning:** `run_event` range-partitioned by day; partitions older than 30 days exported to the Artifact Store and dropped. Key for any future sharding: `tenant_id, run_id`.
- **Consistency:** the event log is strongly consistent (single primary, synchronous standby). The Redis run stream is a best-effort copy; a client that reconnects past the buffer reads from PostgreSQL.

```mermaid
erDiagram
    RUN ||--|{ RUN_EVENT : has
    RUN {
        uuid id PK
        uuid tenant_id
        uuid user_id
        string mode
        string status
        int step_count
        bigint tokens_in
        bigint tokens_out
        timestamp created_at
    }
    RUN_EVENT {
        uuid run_id PK
        int seq PK
        string type
        jsonb payload
        string artifact_ref
        timestamp created_at
    }
```

## Deployment view

```mermaid
C4Deployment
    title Deployment - Option 1, production, single region
    Deployment_Node(edge, "Edge", "Managed load balancer with TLS") {
        Container(lb, "Load Balancer", "Managed", "Idle timeout raised for SSE")
    }
    Deployment_Node(region, "Cloud Region", "3 zones") {
        Deployment_Node(svc, "Managed Container Service", "Autoscaled, spread across zones") {
            Container(api, "Agent API", "Python async", "4 to 12 instances, 120 s drain")
            Container(worker, "Task Worker", "Same image", "6 to 30 instances, scaled on queue depth")
        }
        Deployment_Node(pg, "Managed PostgreSQL", "Multi-zone") {
            ContainerDb(store, "Run Store", "PostgreSQL", "Primary plus synchronous standby")
        }
        Deployment_Node(rd, "Managed Redis", "Multi-zone") {
            ContainerDb(cache, "Stream and Limits", "Redis", "Primary plus replica")
        }
        Deployment_Node(mq, "Managed Queue", "Regional") {
            ContainerQueue(queue, "Task Queue", "Managed queue", "With dead-letter queue")
        }
    }
    Rel(lb, api, "Routes", "HTTPS")
    Rel(api, store, "Reads and writes", "SQL")
    Rel(worker, store, "Reads and writes", "SQL")
    Rel(api, queue, "Enqueues", "HTTPS")
    Rel(worker, queue, "Leases", "HTTPS")
    Rel(api, cache, "Streams and limits", "RESP")
    Rel(worker, cache, "Streams and limits", "RESP")
```

## Quality-attribute analysis

### Reliability of task completion
- Process loss costs at most one step of rework: about 3 s interactive, up to 30 s on a long run, plus up to 60 s redelivery delay.
- Deploys: interactive runs finish inside a 120 s drain (average run 30 s); anything cut off resumes from the log when the client reconnects. Long runs are redelivered.
- Poison runs go to a dead-letter queue after 3 deliveries.
- Weak point: correctness of the resume path is the team's own code. It needs a kill-test in CI (terminate a worker at every event boundary and assert the run completes with one consistent history).

### Cost
- Platform overhead is negligible next to model spend (see below). Nothing in this option adds per-step fees.

### Latency
- Platform overhead per step: two PostgreSQL appends (~5 ms each), one Redis call (~1 ms), in-process dispatch. About 15 ms, against 2-5 s for the model call. The loop adds under 1% to a run.
- First token: one insert and one rate-token check precede the model call, about 10 ms.

### Scalability
- Peak load is ~370 concurrent runs and ~45 model calls/s. One async instance can hold several hundred idle-waiting runs; the instance counts above are for zone redundancy, not throughput.
- **First bottleneck is the LLM rate limit, not this system.** Second is PostgreSQL write volume: ~2 M event inserts/day now (trivial), ~20 M/day at 10x (still one primary). Partition-by-day keeps tables small.
- Path to 10x: more instances, a larger database instance, and a negotiated model rate limit. No redesign.

### Availability
Serial dependencies (assumed figures): load balancer 99.99% x compute 99.95% x PostgreSQL 99.95% x Redis 99.9% x LLM API 99.5% x data sources 99.9% = about **99.2%**, dominated by the LLM API. With a fallback model on an independent endpoint the LLM term becomes about 99.99% and the chain about **99.7%**. Redis can be made non-critical (fall back to polling PostgreSQL, fail open on rate tokens) to remove its term.

### Operability
- Five managed services, one codebase, one on-call runbook. No new technology for a typical web team.
- Every step is a trace span carrying run id, step, model, tokens, cache-read tokens, tool and latency.

## Cost

Model spend is common to all options and computed in the summary. Platform cost for this option (rough cloud list-price estimates, not quotes):

| Item | Launch (100k runs/day) | 10x | Assumption |
|---|---|---|---|
| Compute (API + workers) | $600 - $1,500 | $4k - $10k | 10-40 small instances at $50-$100/month |
| PostgreSQL, multi-zone | $800 - $1,500 | $3k - $6k | 30 days hot, ~250 GB then ~2.5 TB |
| Redis, multi-zone | $200 - $400 | $800 - $1,500 | Small HA pair |
| Queue, load balancer, egress | $150 - $400 | $1k - $3k | Text payloads only |
| Object storage | $10 - $80 | $100 - $800 | ~240 GB/month growth, a year retained |
| Tracing and logs | $1,000 - $5,000 | $8k - $30k | ~8 GB/day; vendor pricing varies widely, sample at 10x |
| **Platform subtotal** | **$2.8k - $8.9k** | **$17k - $51k** | Under 2% of model spend |
| People | 2-3 engineers to build over ~8 weeks; one on-call rotation | Same | Web-service skills only |

## Failure modes

| Failure | Effect | Blast radius | Detection | Mitigation |
|---|---|---|---|---|
| LLM API errors or slow | Steps fail or stall | All runs | Error rate, time-to-first-token | Timeout per call, retry with jitter under a retry budget, circuit breaker, fallback model; long runs park and retry |
| LLM rate limit hit | 429s | All tenants | 429 rate, token-bucket depth | Client-side token bucket in Redis, per-tenant concurrency caps, shed long runs before interactive |
| Tool backend down | Tool errors | Runs needing that tool | Per-tool error rate | Return the error to the model as a tool result, per-tool circuit breaker and bulkhead |
| Worker or API crash | One step lost | One run | Lease expiry | Redelivery and resume from the log |
| Bad deploy (prompt or code) | Wrong answers or loops | All new runs | Eval gate in CI, canary success and steps-per-run metrics | Versioned prompts and tools, canary at 5%, instant rollback; budgets cap runaway loops |
| PostgreSQL primary lost | Writes pause | All runs for 1-2 min | Managed failover alarm | Automatic failover; runs retry appends |
| Redis lost | Streams drop, limits unavailable | Live streams | Health check | Clients fall back to polling the log; limiter fails open with a static cap |
| Zone lost | Capacity drop | One third of instances | Platform alarms | Instances spread over 3 zones, standby promotion |
| Region lost | Outage | Everything | Platform alarms | Out of scope at launch: restore from backup in a second region (RTO hours, RPO minutes) |
| Prompt injection in tool results | Model follows hostile text | One run, bounded by read-only scope | Guardrail hits, unusual tool arguments | See security |

## Security and compliance

- **Trust boundaries:** client to API (user token), API to data sources (the *user's* delegated credential, never a platform super-user), platform to LLM API (provider key in a secrets manager).
- **Tool results are untrusted input.** Read-only tools cannot change data, but an agent that can read private data and also fetch arbitrary URLs can leak it. Controls: tools run with the caller's permissions, egress allowlist on any fetch-style tool, no tool that both reads private data and writes to an attacker-visible place, tool results delimited and labelled as data.
- **Tenancy:** `tenant_id` on every row with row-level security; per-tenant rate and cost budgets.
- **Data:** transcripts contain user data: encrypt at rest, 30-day hot retention, redact secrets before logging, confirm the LLM provider's retention terms match policy.

## Evolution

- **Easy later:** swapping models, adding tools, adding a fallback provider, moving long runs to a workflow engine (the step function is already pure and the log already has the shape of a workflow history).
- **One-way doors:** the event schema (version it from day one) and the public run/event API.
- **Trigger to move to Option 2:** the first tool with side effects; runs that must wait hours or days for a human; sub-tasks fanned out and joined; or more than one resume-path bug per quarter.

## Precedents

- Anthropic, OpenAI and Cognition all advise starting with a single loop and direct API calls, adding structure only when needed (see summary sources).
- LangGraph-based production agents (Uber, LinkedIn, Klarna, as claimed by LangChain) use the same shape: a loop with per-step checkpoints in PostgreSQL. This option keeps the shape without the framework, and stores deltas rather than full checkpoints.
- Manus reports cache hit rate as the key production metric and an append-only context as the way to protect it, which is why the log here is append-only.
- Counter-case: Replit moved an in-process agent to a workflow engine after failures lost all progress (vendor-authored). That agent has side effects; the lesson taken here is to never run the loop without the per-step log.

## Strengths / Weaknesses / When to choose this

- **Strengths:** fewest moving parts, lowest per-step overhead, no engine constraints on streaming or payload size, team already knows every component.
- **Weaknesses:** recovery logic is self-built; no built-in timers, signals or long waits; discipline needed to keep the step function pure.
- **Choose when:** tools are read-only or idempotent, runs last minutes not days, and the team is small.
