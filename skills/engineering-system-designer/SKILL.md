---
name: engineering-system-designer
description: "Design distributed systems, define architecture for scalability and reliability, or create system design documents. Use when you need component diagrams, data flow analysis, capacity planning, database sharding strategies, API contract design, failure mode analysis, CAP theorem tradeoffs, monolith-to-microservice migration, or architecture decision records for new or existing systems."
metadata:
  version: "1.0.0"
---

# System Design Guide

## Overview
This guide covers the process of turning product requirements into deployable, observable, and resilient distributed system architectures. Use it for greenfield architecture, scaling existing systems, design reviews, architecture decision records, or monolith-to-services migrations.

## Design Process

### 1. Requirements
Clarify functional needs, non-functional targets (latency, throughput, durability), read/write ratio, peak traffic patterns, and geographic distribution.

### 2. Capacity estimation
Calculate QPS, storage growth, and bandwidth. Project at 1x, 5x, and 10x load. Identify the bottleneck resource.

### 3. High-level architecture
Map components, data stores, queues, caches, and external dependencies. Define sync vs async boundaries.

### 4. Component deep-dive
Specify technology choices with justification. Define partitioning, replication, consistency model, and cache invalidation per store.

### 5. Data model and API design
Design schemas for primary access patterns. Define API contracts with error codes and rate limits. Plan migration strategy.

### 6. Failure modes
List every component failure and its blast radius. Define circuit breakers, retries, timeouts, and fallbacks.

### 7. Monitoring
Specify metrics, alerts, and dashboards required before launch.

## Decision Frameworks

### SQL vs NoSQL
- Use SQL when you need transactions across multiple entities, complex joins for reporting, or strong schema enforcement.
- Use NoSQL when your access patterns are key-value lookups, your schema changes frequently, or you need horizontal write scaling beyond a single node.

### Sync vs Async
- Use synchronous communication when the caller needs the result to proceed and latency under 200ms is achievable.
- Use asynchronous messaging when the operation can be completed later, you need to absorb traffic spikes, or downstream services have variable latency.

### Monolith vs Microservices
- Start with a monolith. Extract a service only when you have a clear scaling bottleneck, an independent deployment cadence requirement, or a team ownership boundary that causes merge conflicts.
- Never extract more than one service at a time. Validate operational readiness before the next extraction.

## Design Principles
- **CAP theorem awareness**: Know which two of consistency, availability, and partition tolerance your system prioritizes, and document the tradeoff explicitly.
- **Start simple**: Begin with the fewest components that satisfy requirements. Add complexity only when measurements demand it.
- **Design for failure**: Every component will fail. Define what happens when it does before writing any code.
- **Prefer boring technology**: Choose well-understood tools with strong operational track records over novel alternatives unless a clear, quantified advantage exists.
- **Make decisions reversible**: Favor designs where components can be swapped, scaled, or removed independently without system-wide rewrites.

## Reference: System Design Document Template
Every system design document should contain:
- Problem statement and functional requirements.
- Non-functional requirements with specific numeric targets.
- Capacity estimation with calculations shown.
- High-level architecture diagram description (components, data flow, protocols).
- Data model with access patterns and indexing strategy.
- API contracts for all service boundaries.
- Failure mode analysis for every component.
- Monitoring plan with specific metrics and alert thresholds.
- Cost estimate for infrastructure at launch and at 10x scale.

## Scripts

- `scripts/capacity_calculator.py` -- Calculate QPS, storage, and bandwidth from traffic assumptions. Run with `--help` for options.

See [Code Examples](references/code-examples.md) for full implementation patterns including capacity estimation, API contracts, database schema with sharding, and circuit breaker.

See [Worked Examples](references/worked-examples.md) for complete system design walkthroughs of a URL shortener and a WhatsApp-like chat system, covering requirements through production architecture.

See [Failure Analysis](references/failure-analysis.md) for failure mode analysis templates, cache strategy comparisons, load shedding, bulkhead pattern, and chaos engineering checklists.

See [Scaling Patterns](references/scaling-patterns.md) for consistent hashing, database sharding, CQRS, rate limiting, back-pressure handling, and AWS cost estimation templates.
