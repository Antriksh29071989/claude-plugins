# Quality Attributes and Estimation

Every option is judged on the same attributes. State each requirement as a scenario with a measure (Bass, Clements & Kazman): *under [environment], when [stimulus] occurs, the system [response] within [measure]*.

## Estimation

Do this first; it rules options in or out.

**Load**
- Daily active users x actions per user per day = requests/day. Divide by 86,400 for average rps (about 100k seconds per day is close enough).
- Peak is typically 2-10x average; state the factor used. Events (sales, launches) can exceed that.
- Read/write ratio. Fan-out per write (followers, subscribers, replicas, indexes).

**Data**
- Record size x records per day x retention = raw storage. Multiply by replication factor (commonly 3), add indexes (often 20-100% of raw) and headroom (30%+).
- Working set vs total: what fraction must be in memory or on fast storage?

**Network**
- rps x payload size = bandwidth. Egress to the internet is billed; inter-zone and inter-region traffic usually is too.

**Useful magnitudes** (order-of-magnitude, hardware-dependent - state them as approximate)

| Operation | Roughly |
|---|---|
| Main memory reference | 100 ns |
| NVMe/SSD random read | 20-150 us |
| Round trip within a datacenter/zone | 0.5 ms |
| Round trip between zones in a region | 1-2 ms |
| Spinning disk seek | 5-10 ms |
| Round trip across a continent | 30-80 ms |
| Round trip between continents | 100-250 ms |
| TLS handshake (new connection) | 1-2 extra round trips |

| Capacity rules of thumb | Roughly |
|---|---|
| Single relational primary, well-tuned, simple OLTP | thousands to low tens of thousands of writes/s |
| In-memory cache node | 100k+ simple ops/s |
| Log broker partition | tens of MB/s |
| One stateless app instance | hundreds to a few thousand rps, workload-dependent |

Treat these as starting assumptions and flag which ones a load test must confirm.

## The attributes

### Latency
- Specify percentiles (p50, p99, p99.9), not averages. Users experience the tail.
- **Budget per hop**: allocate the end-to-end target across network, each service, each data access. Sequential hops add; a request that fans out to N backends waits for the slowest, so tail latency amplifies with fan-out (Dean & Barroso, "The Tail at Scale").
- Tactics: caching (and its invalidation cost), precomputation/materialised views, colocating data with compute, edge/CDN, connection reuse, async for anything the user does not need to wait for, hedged requests, read replicas.
- Ask: what is on the synchronous path that does not need to be?

### Scalability
- Which dimension grows: requests, data volume, tenants, fan-out, geographic spread?
- Name the **first bottleneck** for each option and the load at which it appears. Name the second.
- Stateless tiers scale horizontally; state is the hard part - partitioning key, hot keys, rebalancing, cross-partition queries (DDIA, partitioning).
- Elasticity: how fast can capacity be added relative to how fast load arrives?
- Vertical scaling and read replicas go a long way. Sharding is a one-way door; show the numbers that justify it.

### Availability and resilience
- Target as an SLO. Downtime allowed per year: 99% = 3.65 days; 99.9% = 8.8 hours; 99.95% = 4.4 hours; 99.99% = 53 minutes; 99.999% = 5.3 minutes.
- **Serial dependencies multiply**: five hard dependencies at 99.9% each give about 99.5%. Redundant independent replicas: 1 - (1 - a)^n. Show this arithmetic for each option.
- Blast radius: what fails together? Zone, region, tenant, cell, deploy.
- Tactics (Nygard; SRE book; Amazon Builders' Library): timeouts everywhere, retries with backoff, jitter and a retry budget, idempotency, circuit breakers, bulkheads, load shedding, back pressure, graceful degradation, static stability, cell-based isolation.
- Recovery: RTO and RPO. Backups are only real if restore is tested.

### Consistency and data integrity
- What must be strongly consistent (money, inventory, uniqueness, permissions) and what tolerates staleness (feeds, counts, search)? Decide per data path, not per system.
- CAP describes behaviour under partition; PACELC adds the everyday trade: even without partition, lower latency or stronger consistency.
- Name the model: linearizable, serializable, snapshot isolation, read-your-writes, causal, eventual. Name the anomalies the chosen model permits.
- Across services: sagas with compensation, transactional outbox, idempotent consumers; avoid dual writes (Hard Parts; Richardson).
- Ordering, deduplication and exactly-once *effects* for any asynchronous flow.

### Cost
Estimate at launch scale and at 10x, as ranges, with pricing assumptions stated.
- **Compute**: instances/pods x hours, or invocations x duration for serverless. Reserved/committed vs on-demand vs spot.
- **Storage**: GB-months by tier, plus IOPS/throughput provisioning, backups and replicas.
- **Network**: internet egress, cross-zone and cross-region transfer, NAT, load balancers. Chatty cross-zone microservices and cross-region replication are common surprises.
- **Managed-service premium** vs the engineering time to self-run. Per-request pricing is cheap at low volume and expensive at sustained high volume; find the crossover.
- **Licences and third parties**: per-seat, per-host, per-GB-ingested (observability is frequently a top-three line item).
- **People**: engineers to build, on-call load, specialist skills to hire. Usually the largest cost and the one most often left out.
- Cost of change: migration effort and lock-in if the choice is wrong.
- Give unit economics where useful: cost per 1k requests, per tenant, per GB stored.

### Operability
- Deployment: frequency, rollback time, progressive delivery, schema migration strategy.
- Observability: metrics (latency, traffic, errors, saturation), logs, traces, and SLO-based alerting.
- Number of moving parts the on-call engineer must understand at 3 a.m.
- Does the team have the skills, or is this their first time running it?

### Security and compliance
- Trust boundaries on the Container diagram; authentication and authorisation at each crossing.
- Data classification, encryption in transit and at rest, key management, secrets.
- Tenancy isolation model: shared, pooled with row-level controls, siloed.
- Regulatory constraints (data residency, retention, audit, PCI/HIPAA/GDPR scope) - these can eliminate options outright.
- Threats worth a line each: abuse/rate limiting, injection at trust boundaries, privilege escalation between tenants, supply chain.

### Evolvability
- What is cheap to change later and what is a one-way door (data model, partition key, public API, sync-vs-async contracts, vendor-specific features)?
- Coupling: can parts be deployed, scaled and reasoned about independently where it matters?
- Fitness functions (Ford, Parsons & Kua): how each driver will be checked continuously after the decision.
- Fit with team structure (Conway's law; Skelton & Pais).

## Rating scale for the comparison matrix

Use alongside, never instead of, a concrete statement in each cell.

- **Strong** - meets the driver with margin at 10x scale.
- **Adequate** - meets the driver at stated scale; known path to 10x.
- **Weak** - meets it only with significant extra work or risk.
- **Fails** - cannot meet the driver; disqualifying if the driver is a hard requirement.
