# C4 Model - Diagram Guide

The C4 model (Simon Brown) describes a system at four levels of zoom, plus supplementary views. Draw the levels that carry a decision; skip the ones that would only restate the level above.

## The levels

| Level | Shows | Audience | Draw when |
|---|---|---|---|
| 1. System Context | The system as one box, its users and the external systems it depends on | Everyone | Always. Once, shared by all options. |
| 2. Container | Separately deployable/runnable units and data stores (web app, API, worker, database, queue, bucket) with technology and protocols | Technical | Always. One per option - this is where options visibly differ. |
| 3. Component | The major building blocks inside one container and their responsibilities | Developers | For the one or two containers where the important decisions live. |
| 4. Code | Classes, schemas, interfaces | Developers | Only when a data model or key interface is itself the decision. |

Supplementary views:

- **Dynamic** - how elements collaborate at runtime for one scenario. Draw for the critical path (the hot read, the write that must not be lost, the failure path).
- **Deployment** - how containers map to infrastructure: regions, zones, clusters, managed services. Draw once per option.
- **System Landscape** - several systems together. Only for enterprise-wide problems.

"Container" in C4 means a runnable unit or data store, not a Docker container.

## Notation rules

- Every element has a **name, type, technology (levels 2-3) and a one-line responsibility**.
- Every relationship is **one-directional and labelled with intent and protocol**: "Publishes order events [Kafka]", not "uses".
- Give every diagram a **title** stating level and scope.
- Keep a diagram under about 15 elements. Beyond that, split by scope.
- Do not mix levels of abstraction in one diagram.
- Mark external systems and data stores distinctly (`System_Ext`, `ContainerDb`, `ContainerQueue`).
- Use the same element aliases and names across all diagrams of an option.

## Mermaid syntax

Diagrams are written as Mermaid so they render on GitHub and in most Markdown viewers. Rules that prevent render failures:

- All labels in double quotes. No double quotes inside a label; avoid `<`, `>`, `{`, `}` and line breaks in labels.
- Aliases are plain identifiers: letters, digits, underscore.
- Arguments are positional: `Container(alias, "Label", "Technology", "Description")`.
- Every `{` opened by a boundary is closed on its own line.
- One statement per line.

### Level 1 - System Context

```mermaid
C4Context
    title System Context - Order Platform
    Person(customer, "Customer", "Places and tracks orders")
    Person(support, "Support Agent", "Resolves order issues")
    System(orders, "Order Platform", "Accepts, prices and fulfils orders")
    System_Ext(payments, "Payment Provider", "Card authorisation and capture")
    System_Ext(wms, "Warehouse System", "Picks and ships stock")
    Rel(customer, orders, "Places orders", "HTTPS")
    Rel(support, orders, "Manages orders", "HTTPS")
    Rel(orders, payments, "Authorises payments", "HTTPS/JSON")
    Rel(orders, wms, "Sends fulfilment requests", "AMQP")
    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

### Level 2 - Container

```mermaid
C4Container
    title Container - Order Platform (Option A: modular monolith)
    Person(customer, "Customer", "Places and tracks orders")
    System_Ext(payments, "Payment Provider", "Card authorisation and capture")
    System_Boundary(orders, "Order Platform") {
        Container(web, "Web App", "React", "Storefront and order tracking UI")
        Container(api, "Order API", "Kotlin, Spring Boot", "Order lifecycle, pricing, payment orchestration")
        Container(worker, "Outbox Worker", "Kotlin", "Relays committed events to the broker")
        ContainerDb(db, "Order DB", "PostgreSQL", "Orders, line items, outbox")
        ContainerDb(cache, "Cache", "Redis", "Catalogue and session data")
        ContainerQueue(bus, "Event Bus", "Kafka", "Order domain events")
    }
    Rel(customer, web, "Uses", "HTTPS")
    Rel(web, api, "Calls", "HTTPS/JSON")
    Rel(api, db, "Reads and writes", "SQL")
    Rel(api, cache, "Reads through", "RESP")
    Rel(api, payments, "Authorises", "HTTPS/JSON")
    Rel(worker, db, "Polls outbox", "SQL")
    Rel(worker, bus, "Publishes events", "Kafka")
    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

### Level 3 - Component

```mermaid
C4Component
    title Component - Order API
    ContainerDb(db, "Order DB", "PostgreSQL", "Orders, line items, outbox")
    System_Ext(payments, "Payment Provider", "Card authorisation and capture")
    Container_Boundary(api, "Order API") {
        Component(ctrl, "Order Controller", "Spring MVC", "Validates and routes requests")
        Component(svc, "Order Service", "Domain service", "Order state machine and invariants")
        Component(pricing, "Pricing Engine", "Domain service", "Applies price rules and promotions")
        Component(pay, "Payment Gateway Adapter", "HTTP client", "Idempotent calls with timeout and circuit breaker")
        Component(repo, "Order Repository", "JPA", "Persists aggregates and outbox rows in one transaction")
    }
    Rel(ctrl, svc, "Invokes")
    Rel(svc, pricing, "Prices order")
    Rel(svc, pay, "Requests authorisation")
    Rel(svc, repo, "Saves")
    Rel(repo, db, "Reads and writes", "SQL")
    Rel(pay, payments, "Authorises", "HTTPS/JSON")
```

### Dynamic view

Use a sequence diagram: it renders reliably and shows ordering, sync vs async, and where latency accrues. Participants must be elements from the Container or Component diagram, with the same names. Annotate the latency budget on the critical steps.

```mermaid
sequenceDiagram
    title Dynamic - Place order (happy path, budget 300 ms p99)
    actor Customer
    participant Web as Web App
    participant API as Order API
    participant Pay as Payment Provider
    participant DB as Order DB
    participant Bus as Event Bus
    Customer->>Web: Submit order
    Web->>API: POST /orders with idempotency key
    API->>Pay: Authorise (timeout 150 ms)
    Pay-->>API: Authorised
    API->>DB: Commit order and outbox row (10 ms)
    API-->>Web: 201 Created
    DB-)Bus: OrderPlaced via outbox relay (async)
```

### Deployment view

```mermaid
C4Deployment
    title Deployment - Order Platform (Option A, production)
    Deployment_Node(cdn, "CDN", "Edge network") {
        Container(web, "Web App", "React", "Static assets")
    }
    Deployment_Node(region, "Primary Region", "Cloud region, 3 zones") {
        Deployment_Node(k8s, "Kubernetes Cluster", "Managed, autoscaled 6 to 30 pods") {
            Container(api, "Order API", "Kotlin, Spring Boot", "Stateless, spread across zones")
            Container(worker, "Outbox Worker", "Kotlin", "2 replicas, leader elected")
        }
        Deployment_Node(rds, "Managed PostgreSQL", "Multi-zone, 1 primary and 2 replicas") {
            ContainerDb(db, "Order DB", "PostgreSQL", "Synchronous standby in second zone")
        }
    }
    Rel(web, api, "Calls", "HTTPS")
    Rel(api, db, "Reads and writes", "SQL")
    Rel(worker, db, "Polls outbox", "SQL")
```

If a `C4Deployment` diagram becomes hard to read, use a `flowchart TB` with one `subgraph` per region/zone instead - legibility beats notation purity.

### Level 4 - Code (only when needed)

Use `erDiagram` for a data model or `classDiagram` for a key interface.

```mermaid
erDiagram
    ORDER ||--|{ ORDER_LINE : contains
    ORDER ||--o{ OUTBOX_EVENT : emits
    ORDER {
        uuid id PK
        uuid customer_id
        string status
        timestamp created_at
    }
    ORDER_LINE {
        uuid id PK
        uuid order_id FK
        string sku
        int quantity
    }
    OUTBOX_EVENT {
        uuid id PK
        uuid order_id FK
        string type
        timestamp published_at
    }
```

## Review checklist

- Could someone outside the team tell what each box does and why each arrow exists?
- Does every option's Container diagram make its distinguishing decision visible?
- Are data stores, queues and external systems shown with ownership clear (which container writes to which store)?
- Do the diagrams and the prose name the same elements?
- Does the dynamic view cover the scenario behind the top driver?
