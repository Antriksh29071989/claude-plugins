# Architecture Literature Map

A map from problem type to the books worth applying. The books themselves are not bundled; this file records what each one is authoritative on so the right model is applied and cited. Cite as *Author, Title, chapter/topic*. Chapter numbers below refer to the edition noted; if unsure of a chapter, cite the topic only.

## Pick by driver

| If the problem is dominated by... | Start with |
|---|---|
| Data volume, consistency, replication, partitioning | Kleppmann (DDIA); Petrov |
| Choosing an architecture style | Richards & Ford (Fundamentals) |
| Splitting a system / distributed transactions / data ownership | Ford et al. (Hard Parts); Newman; Richardson |
| Domain complexity, service boundaries | Evans; Vernon |
| Reliability, overload, cascading failure | Nygard (Release It!); Google SRE book |
| Messaging and integration | Hohpe & Woolf |
| Quality-attribute analysis and evaluation method | Bass, Clements & Kazman |
| Long-term change, migration | Ford, Parsons & Kua; Newman (Monolith to Microservices) |
| Team structure shaping the architecture | Skelton & Pais |
| Worked large-scale examples | Xu (System Design Interview) |
| Diagramming and communicating | Brown (C4) |

## The books

### Martin Kleppmann - *Designing Data-Intensive Applications* (1st ed., 2017)
The default reference for anything storing or moving data. Chapters: 1 Reliable, Scalable and Maintainable Applications (load parameters, percentiles, tail latency); 2 Data Models and Query Languages; 3 Storage and Retrieval (LSM-trees vs B-trees, OLTP vs OLAP, column stores); 4 Encoding and Evolution (schema compatibility); 5 Replication (single-leader, multi-leader, leaderless, replication lag anomalies, quorums); 6 Partitioning (key-range vs hash, hot spots, secondary indexes, rebalancing); 7 Transactions (isolation levels, write skew); 8 The Trouble with Distributed Systems (unreliable networks and clocks); 9 Consistency and Consensus (linearizability, ordering, total order broadcast); 10 Batch Processing; 11 Stream Processing (logs, change data capture, event sourcing, exactly-once semantics); 12 The Future of Data Systems (derived data, unbundling the database). A 2nd edition exists with revised chapter structure - name the edition when citing a chapter.

### Mark Richards & Neal Ford - *Fundamentals of Software Architecture*
Architecture characteristics (the "-ilities") and how to identify the few that matter; modularity and component identification; a catalogue of styles with per-characteristic ratings - layered, pipeline, microkernel, service-based, event-driven, space-based, orchestration-driven SOA, microservices. Source of the two laws: everything in architecture is a trade-off, and why is more important than how. Use it to justify the style chosen for each option.

### Neal Ford, Mark Richards, Pramod Sadalage, Zhamak Dehghani - *Software Architecture: The Hard Parts*
Trade-off analysis for distributed architectures: granularity disintegrators and integrators (when to split or merge a service), data ownership and decomposition of a shared database, distributed transactions and the saga pattern catalogue (combinations of communication, consistency and coordination), orchestration vs choreography, contracts, architecture quantum. Use when an option involves more than one deployable owning data.

### Sam Newman - *Building Microservices* (2nd ed.) and *Monolith to Microservices*
Service boundaries, communication styles, deployment, testing, observability, and the cost side of microservices. The second title covers incremental migration: strangler fig, branch by abstraction, parallel run, splitting the database. Use for any staged or migration option.

### Chris Richardson - *Microservices Patterns*
Concrete pattern mechanics: saga, transactional outbox, CQRS, API composition, API gateway/BFF, event sourcing, service discovery.

### Michael Nygard - *Release It!* (2nd ed.)
Production failure. Stability antipatterns (integration points, cascading failures, chain reactions, blocked threads, slow responses, unbounded result sets, self-denial attacks) and stability patterns (timeouts, circuit breaker, bulkheads, steady state, fail fast, let it crash, handshaking, shed load, back pressure, governor). Use to write every option's failure-mode section.

### Betsy Beyer et al. (Google) - *Site Reliability Engineering* and *The Site Reliability Workbook*
SLIs, SLOs and error budgets; monitoring distributed systems (the four golden signals); handling overload; addressing cascading failures; load balancing at the front end and in the datacenter; managing critical state with distributed consensus; data integrity. Use to set availability targets and to reason about operational cost.

### Gregor Hohpe & Bobby Woolf - *Enterprise Integration Patterns*
The vocabulary of messaging: channels (point-to-point, publish-subscribe, dead letter), message construction, routing (content-based router, splitter, aggregator, scatter-gather, process manager), transformation, endpoints (competing consumers, idempotent receiver). Use to name and design asynchronous flows precisely.

### Eric Evans - *Domain-Driven Design*; Vaughn Vernon - *Implementing Domain-Driven Design*
Strategic design: bounded contexts, context mapping (anticorruption layer, shared kernel, customer/supplier, conformist), ubiquitous language. Tactical design: aggregates as consistency boundaries, domain events. Use to draw container and component boundaries that follow the domain rather than the technology.

### Martin Fowler - *Patterns of Enterprise Application Architecture*
Layering, domain logic organisation (transaction script, domain model, table module), data source patterns (active record, data mapper, repository, unit of work), concurrency (optimistic and pessimistic offline lock). Use at Component level inside a single application.

### Len Bass, Paul Clements, Rick Kazman - *Software Architecture in Practice*
Quality-attribute scenarios (source, stimulus, environment, artifact, response, response measure), architectural tactics per attribute (availability, performance, security, modifiability, deployability and more), and evaluation via ATAM (sensitivity points, trade-off points, risks). Use for the structure of the quality analysis and the comparison.

### Neal Ford, Rebecca Parsons, Patrick Kua - *Building Evolutionary Architectures*
Fitness functions as executable checks on architecture characteristics; incremental change; appropriate coupling. Use to turn each driver into something measurable after the decision is made, and for the evolution section.

### Robert C. Martin - *Clean Architecture*; Alistair Cockburn - Hexagonal Architecture (ports and adapters)
The dependency rule, boundaries between policy and detail, component cohesion and coupling principles. Use at Component and Code level.

### Matthew Skelton & Manuel Pais - *Team Topologies*
Conway's law applied deliberately: stream-aligned, platform, enabling and complicated-subsystem teams; cognitive load as a limit on what one team can own. Use to test whether an option can be staffed.

### Alex Petrov - *Database Internals*
Storage engines (B-tree variants, LSM), and distributed internals: failure detection, leader election, replication, anti-entropy, distributed transactions, consensus. Use when a choice between specific datastores is the decision.

### Brendan Burns - *Designing Distributed Systems*
Reusable container patterns: sidecar, ambassador, adapter; replicated load-balanced services, sharded services, scatter/gather; work queues and event-driven batch.

### Roberto Vitillo - *Understanding Distributed Systems*
Compact treatment of communication, coordination, scalability, resiliency and operations; a good bridge between DDIA and practical cloud design.

### Alex Xu - *System Design Interview* (vol. 1 and 2)
Worked designs with estimation: rate limiter, consistent hashing, key-value store, unique ID generator, URL shortener, web crawler, notification system, news feed, chat, search autocomplete, video streaming, file storage, proximity service, payment system, and others. Use as a sanity check on components and estimates, not as a primary authority.

### Simon Brown - *The C4 Model* / *Software Architecture for Developers*
Diagram abstractions and notation rules. See `c4-model.md`.

### Martin Kleppmann, Jay Kreps and the papers
For specifics, primary papers outrank books. See `industry-patterns.md`.

## How to apply

- Use a book for its **model and its warnings**, not for an endorsement. Each pattern's source also documents its cost; carry that cost into the option's analysis.
- When two sources disagree (for example on microservice granularity), present the disagreement - it usually marks a real trade-off in the problem.
- Prefer two or three sources applied in depth over a long list of citations.
