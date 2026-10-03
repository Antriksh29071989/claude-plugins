# Industry Precedents

Starting points for how large engineering organisations solved recurring problems. These are pointers recorded from memory: **verify against the primary source before citing specifics** (numbers, mechanisms, dates), and look for what the organisation has changed since. Add a source URL for everything that ends up in a deliverable.

Always ask whether the precedent transfers. Each of these was built for a specific scale, workload and staffing level, usually after a simpler design had been outgrown.

## Storage and databases

| Problem | Precedent | Key ideas |
|---|---|---|
| Always-writable key-value store | Amazon **Dynamo** (SOSP 2007) | Consistent hashing, sloppy quorum, hinted handoff, vector clocks, Merkle-tree anti-entropy; availability chosen over consistency |
| Managed KV with predictable latency | Amazon **DynamoDB** (USENIX ATC 2022) | Per-partition consensus replication, admission control, lessons on partition hot spots and capacity |
| Globally consistent relational data | Google **Spanner** (OSDI 2012), **F1** (VLDB 2013) | Synchronised clocks with bounded uncertainty (TrueTime), Paxos groups, externally consistent transactions |
| Wide-column at petabyte scale | Google **Bigtable** (OSDI 2006) | Tablets, SSTables/LSM, a lock service for coordination |
| Cloud-native relational | Amazon **Aurora** (SIGMOD 2017) | Storage decoupled from compute, quorum writes across zones, redo log as the unit of replication |
| Social graph, read-dominated | Meta **TAO** (USENIX ATC 2013) | Objects and associations API, write-through cache tiers over sharded MySQL, leader/follower regions |
| Cache in front of a database at scale | Meta **Scaling Memcache at Facebook** (NSDI 2013) | Leases against stale sets and thundering herds, regional pools, cold-cluster warm-up, invalidation pipeline |
| Photo/blob storage | Meta **Haystack** (OSDI 2010), **f4** (OSDI 2014) | Pack small files to cut metadata lookups; erasure-coded warm tier |
| Sharding relational databases | **Vitess** (YouTube, later Slack and others); Pinterest and Instagram sharding posts | Sharding middleware, shard-encoded IDs, online resharding |
| Chat/message history | Discord "How Discord Stores Billions/Trillions of Messages" | Partition by channel and time bucket; migration between wide-column stores driven by tail latency and operations |
| Time series | Meta **Gorilla** (VLDB 2015); Google **Monarch** (VLDB 2020) | Delta-of-delta and XOR compression, in-memory recent window, regional zones |

## Messaging, streams and workflows

| Problem | Precedent | Key ideas |
|---|---|---|
| High-throughput event log | LinkedIn **Kafka** (NetDB 2011); Jay Kreps, "The Log" (2013) | Partitioned append-only log, consumer-tracked offsets, log as the integration backbone |
| Stream processing semantics | Google **MillWheel** (VLDB 2013), **Dataflow model** (VLDB 2015) | Event time vs processing time, watermarks, windowing, exactly-once effects |
| Durable long-running workflows | Uber **Cadence** / **Temporal**; AWS Step Functions | Workflow state as replayable history instead of ad hoc sagas |
| Distributed priority queue | Meta **FOQS** (engineering blog) | Sharded MySQL-backed queue with priorities and delayed delivery |
| Feed / timeline delivery | Twitter timelines talks; Meta feed architecture | Fan-out on write for most accounts, fan-out on read for very high-follower accounts, hybrid merge at read time |

## Reliability and operations

| Problem | Precedent | Key ideas |
|---|---|---|
| Retries, timeouts, overload | **Amazon Builders' Library**: timeouts/retries/backoff with jitter; load shedding; avoiding fallback; avoiding insurmountable queue backlogs; making retries safe with idempotent APIs | Retry budgets, jitter, shed early, prefer one well-tested path over fallbacks |
| Limiting blast radius | Builders' Library: shuffle sharding, static stability with Availability Zones; AWS cell-based architecture guidance; Slack's move to cellular architecture | Cells, per-tenant shard combinations, no control-plane dependency on the recovery path |
| Cascading failure | Google SRE book: Handling Overload, Addressing Cascading Failures | Client-side throttling, criticality classes, deadline propagation |
| Resilience testing | Netflix chaos engineering (Chaos Monkey, later tooling); Netflix adaptive concurrency limits | Continuous failure injection; limits derived from measured latency |
| Peak-load readiness | Meta **Kraken** (OSDI 2016) | Live traffic shifting as a load test |
| Cluster scheduling | Google **Borg** (EuroSys 2015), and Kubernetes after it | Declarative jobs, bin packing, priority and preemption |
| Coordination and consensus | Google **Chubby** (OSDI 2006); **ZooKeeper** (USENIX ATC 2010); **Raft** (USENIX ATC 2014) | Small strongly consistent core for locks, leader election and configuration |
| Distributed tracing | Google **Dapper** (2010) | Sampled trace propagation with low overhead |
| Software load balancing | Google **Maglev** (NSDI 2016); Meta **Katran** | Consistent hashing with connection tracking on commodity hosts |
| Sharded-service placement | Google **Slicer** (OSDI 2016); Meta **Shard Manager** | Central assignment of key ranges to tasks, load-aware rebalancing |

## Cross-cutting building blocks

| Problem | Precedent | Key ideas |
|---|---|---|
| Authorisation at scale | Google **Zanzibar** (USENIX ATC 2019) | Relationship tuples, consistency tokens against stale permissions, global low-latency checks |
| Unique IDs | Twitter **Snowflake** | Time-ordered 64-bit IDs from timestamp, worker ID and sequence |
| Exactly-once payments APIs | Stripe engineering blog on idempotency keys | Client-supplied keys, stored request outcome, safe retries |
| Rate limiting | Stripe "Scaling your API with rate limiters"; Cloudflare posts | Token bucket, concurrency limiters, load shedders by criticality |
| Geospatial indexing | Google **S2**; Uber **H3** | Hierarchical cell indexing for proximity queries |
| Content delivery | Netflix **Open Connect** | Caches inside ISP networks, popularity-driven pre-positioning |
| Batch at scale | Google **MapReduce** (OSDI 2004), **GFS** (SOSP 2003) | Historically foundational; largely superseded by later systems, useful mainly for the reasoning |

## Structure and organisation

| Problem | Precedent | Key ideas |
|---|---|---|
| Too many microservices | Uber **DOMA** (domain-oriented microservice architecture) | Group services into domains with gateways and layers to tame dependency sprawl |
| Distributed design costing more than it earns | Amazon Prime Video monitoring-service post (2023) | Consolidating a serverless, orchestrated pipeline into a single process cut cost sharply for that workload |
| Scaling a monolith | Shopify modular monolith posts; Stack Overflow architecture posts | Enforced module boundaries inside one deployable; vertical scale plus caching carries far |
| API style and service ownership | Amazon two-pizza teams and the service-interface mandate | Teams own services end to end; all communication through service interfaces |

## Where to look for more

- Papers: USENIX (OSDI, NSDI, ATC), SOSP, VLDB, SIGMOD proceedings; research.google; Meta research publications; Amazon Science.
- Engineering blogs: AWS Architecture Blog and Builders' Library, Google Cloud architecture centre, Meta Engineering, Netflix Tech Blog, Uber Engineering, Stripe, LinkedIn Engineering, Discord, Slack, Shopify, Cloudflare, Airbnb, Pinterest, Dropbox.
- Reference architectures: AWS Well-Architected Framework, Azure Architecture Center, Google Cloud Architecture Framework.
- Talks: QCon/InfoQ, Strange Loop, re:Invent, SREcon.

Prefer primary sources over summaries of them, and recent retrospectives over original announcements.
