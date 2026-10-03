# Output Template

Deliverables go in `docs/architecture/<problem-slug>/`. Keep headings as below so designs are comparable across problems. Omit a section only if it does not apply, and say why.

---

## `README.md` - Summary

```markdown
# <Problem title> - Architecture Options

> Status: Proposed · Date: <YYYY-MM-DD> · Recommendation: **Option <n> - <name>**

## 1. Problem
What is being built and why, in one paragraph. In scope / out of scope.

## 2. Assumptions
Numbered list. Mark each as *given by the user* or *assumed*.

## 3. Requirements
### Functional
### Quality-attribute scenarios
| # | Attribute | Scenario | Measure |
### Constraints

## 4. Estimates
Load, data and network arithmetic, shown. Which numbers need validating.

## 5. Architecture drivers
Ranked list of 3-5, with what is deliberately de-prioritised.

## 6. System context
C4 Level 1 diagram (shared by all options).

## 7. Options at a glance
One paragraph per option: thesis, style, where it comes from. Link to its file.

## 8. Comparison
| Driver | Option 1 | Option 2 | Option 3 |
Each cell: rating + a concrete statement or number.
Further rows: monthly cost at launch / at 10x, team and operational load, time to first production release, main risk, one-way doors.

## 9. Recommendation
The choice and the reasoning. What is traded away. Conditions under which another option becomes right.

## 10. Risks and how to retire them
| Risk | Likelihood | Impact | Early test (spike, load test, PoC) |

## 11. Next steps
Ordered, concrete, first two weeks.

## 12. Sources
### Literature
*Author, Title, chapter/topic* - what was applied from it.
### Industry precedents
Organisation, system, link - what transfers and what does not.
```

---

## `option-<n>-<short-name>.md` - One per option

```markdown
# Option <n> - <Name>

## Thesis
One paragraph: the central idea and the trade it makes.

## Style and lineage
Architecture style; literature source; who runs something similar.

## Container view
C4 Level 2 diagram, then a table:
| Container | Technology | Responsibility | Scales by | State |

## Component view
C4 Level 3 for the container(s) where the key decisions live.

## Critical flows
Dynamic view(s) with the latency budget annotated. Include one failure path.

## Data design
Stores, ownership, schema sketch (Level 4 only if needed), partition key, replication, consistency model per data path.

## Deployment view
Regions, zones, clusters, managed services, scaling units.

## Quality-attribute analysis
One subsection per driver, with numbers:
- Latency: budget per hop, expected p50/p99.
- Scalability: ceiling, first and second bottleneck, path to 10x.
- Availability: dependency-chain arithmetic, blast radius, RTO/RPO.
- Consistency: guarantees and permitted anomalies.

## Cost
| Item | Launch scale | 10x scale | Assumption |
Infrastructure subtotal, people/operations, unit cost.

## Failure modes
| Failure | Effect | Blast radius | Detection | Mitigation |
At minimum: dependency outage, overload, bad deploy, zone/region loss.

## Security and compliance
Trust boundaries, authN/authZ, data protection, tenancy.

## Evolution
Easy to change later; one-way doors; measurable trigger for the next stage.

## Strengths / Weaknesses / When to choose this
```

---

## `adr-0001-<decision>.md` - Decision record

```markdown
# ADR 0001: <Decision>

- Status: Proposed
- Date: <YYYY-MM-DD>

## Context
The forces at play: drivers, constraints, estimates.

## Decision
What will be done, stated actively.

## Alternatives considered
Each rejected option and the specific reason.

## Consequences
Positive, negative and neutral. What becomes harder.

## Revisit when
Measurable conditions that should reopen this decision.
```
