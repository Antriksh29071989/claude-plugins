---
name: design
description: Use when the user poses a software architecture or system design problem - "design a system for X", "how should we architect Y", "what architecture for Z", "compare approaches for scaling W", "should we use microservices / event-driven / a monolith", or asks for C4 diagrams, an ADR, or an architecture trade-off analysis. Produces 2-3 contrasting designs grounded in the architecture literature and in how large engineering organisations solved the same problem, with C4 diagrams, a quality-attribute analysis (latency, cost, scalability, availability, consistency, operability, security) and a recommendation.
argument-hint: <architecture problem to solve>
---

# Architecture Design

Problem to solve: $ARGUMENTS

Act as a principal architect. The deliverable is a decision the reader can defend: a small set of genuinely different designs, each drawn in C4, each judged against the same quality attributes, and a recommendation that states what it costs and when it stops being right.

Work through the phases in order. Keep the user informed with one short line per phase; put the substance in the output files, not in chat.

## Phase 1 - Frame the problem

1. If the current directory is an existing codebase the design must fit into, read enough of it to know the stack, deployment model, data stores and team conventions. A design that ignores what already exists is not an option, it is a rewrite proposal - say so if that is what you are proposing.
2. Extract from the request:
   - **Functional scope** - the 3-7 capabilities that matter, and what is explicitly out of scope.
   - **Quality attributes** - write each as a measurable scenario (see `references/quality-attributes.md`), e.g. "p99 read latency under 150 ms at 20k rps", not "fast".
   - **Constraints** - team size and skills, budget, deadline, compliance, existing platform, build-vs-buy stance.
3. Ask the user only for what would change the shape of the design and cannot be reasonably assumed (typically: scale, consistency needs, budget/team, regulatory limits). At most one round, at most four questions. Everything else becomes a stated assumption - list every assumption explicitly so the reader can challenge it.

## Phase 2 - Size it

Do back-of-envelope estimation before choosing anything, using `references/quality-attributes.md`: users and requests per second (average and peak), read/write ratio, payload sizes, storage growth per year, bandwidth, fan-out factors, and the latency budget split across hops. Show the arithmetic. These numbers decide which options are even viable; many problems that sound large fit on one well-provisioned database, and saying so is a valid finding.

## Phase 3 - Pick the architecture drivers

Rank the 3-5 quality attributes that will actually shape the design. Everything cannot be top priority; name what is deliberately traded away. The drivers are the columns of the final comparison.

## Phase 4 - Consult the literature

Read `references/books.md`. Select the books and chapters relevant to this problem's drivers and apply their models - do not just name-drop. For each option you later propose, be able to say which source the pattern comes from and what that source says its costs are. Cite as *Author, Title, chapter/topic*. If you are not certain a specific claim is in a specific chapter, cite the book and topic without the chapter rather than guessing.

## Phase 5 - Research how large organisations solved it

Read `references/industry-patterns.md` for starting points, then verify and extend with web research: primary papers, engineering blogs and conference talks from Google, Meta, Amazon, Netflix, Uber, Stripe, LinkedIn and others who faced this problem at scale.

- If the `industry-researcher` agent is available, delegate this to it with the problem statement, drivers and scale estimates. Otherwise research inline with WebSearch/WebFetch.
- For each precedent capture: the problem they had, their scale, what they built, what they traded away, what they later changed and why, and a source URL.
- Then ask the question that matters: **does the precedent apply at this problem's scale and team size?** Solutions built for a billion users with hundreds of infrastructure engineers are often wrong for a team of eight. Say explicitly which parts transfer and which do not. Organisations reversing course (moving back toward simpler designs) are as instructive as the original designs.
- Never invent a source. If web access is unavailable, say so and label precedents as "from memory, unverified".

## Phase 6 - Generate 2-3 options

Produce options that differ in **architectural style or in the central trade-off**, not in vendor choice. "Kafka vs RabbitMQ" is one option with a sub-decision; "synchronous request/response over a shared database" vs "event-driven with per-service stores" are two options. A useful spread is usually:

- **the simplest thing that meets the drivers** (often a modular monolith or a managed service),
- **the design optimised for the top driver** (scale, latency or availability),
- optionally **a hybrid or staged path** that starts simple and has a defined trigger for evolving.

Give two options when the space truly has two; do not pad to three with a strawman.

For every option provide, following `references/output-template.md`:

1. Name, one-paragraph thesis, architecture style and its source in the literature.
2. **C4 diagrams** per `references/c4-model.md`: System Context (shared across options, drawn once), Container diagram (per option - this is the main one), Component diagram for the one or two containers where the interesting decisions live, a dynamic view of the critical flow, and a deployment view. Level 4 (code) only where a data model or key interface is itself the decision.
3. Data design: stores, ownership, partitioning key, replication, consistency model per data path.
4. Quality-attribute analysis against every driver, with numbers from Phase 2: latency budget per hop, throughput ceiling and what the first bottleneck is, availability arithmetic from the dependency chain, consistency behaviour under partition.
5. **Cost**: itemised monthly estimate at launch scale and at 10x (compute, storage, network egress, managed-service premiums, licences) as ranges with stated pricing assumptions, plus the operational cost in people - on-call burden and the skills the team must have. Check current pricing on the web when a number materially affects the recommendation.
6. Failure modes: what breaks, blast radius, detection and mitigation - at minimum a dependency outage, overload, a bad deploy, and loss of a zone/region.
7. Security and compliance posture: trust boundaries, authN/authZ, data classification, tenancy isolation.
8. Evolution: what is easy to change later, what is a one-way door, and the measurable trigger for moving to the next stage.
9. Precedents: which organisations run something like this, with sources.

## Phase 7 - Compare and recommend

1. Build a trade-off matrix: options as columns, drivers as rows, each cell a concrete statement or number (not just a score), plus a rating so the matrix can be scanned.
2. Stress the options against each other honestly: argue the strongest case for each before choosing.
3. Recommend one. State why, what is given up, the conditions under which a different option becomes the right answer, and the top risks with how to retire each early (spike, load test, proof of concept).
4. Record it as an ADR (context, decision, consequences, alternatives rejected).

## Phase 8 - Write the deliverables

Write to `docs/architecture/<problem-slug>/` in the current project (create it; if the user named another location, use that). Structure and section contents are defined in `references/output-template.md`:

- `README.md` - the summary: problem, assumptions, drivers, estimates, the options in one paragraph each, comparison matrix, recommendation, risks, next steps, sources.
- `option-<n>-<short-name>.md` - one per option with its full C4 set and analysis.
- `adr-0001-<decision>.md` - the decision record.

Before finishing, re-read each Mermaid block against the syntax rules in `references/c4-model.md` - unbalanced braces and unquoted labels are the usual failures - and check that every element in a diagram appears in the prose and vice versa.

Finish in chat with a short brief: the recommendation in two sentences, the main thing traded away, the open questions for the user, and the path to the files.

## Standards

- Quantify. Every claim about speed, scale, availability or cost carries a number and the assumption behind it.
- Be honest about uncertainty. Mark estimates as estimates and unverified precedents as unverified.
- Prefer boring technology unless a driver demands otherwise; novelty must pay for itself.
- Match the design to the team that has to run it. Operational complexity is a cost, not a detail.
- Do not design for imagined scale. Design for the stated scale with a known path to 10x.
