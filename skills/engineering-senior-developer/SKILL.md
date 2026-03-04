---
name: engineering-senior-developer
description: "Lead complex software implementation, architecture decisions, and reliable delivery across any modern technology stack. Use when you need pragmatic architecture tradeoffs, technical plan creation from ambiguous requirements, code quality improvements, production-safe rollout strategies, observability setup, or senior engineering judgment on maintainability, testing, and operational reliability."
metadata:
  version: "1.0.0"
---

# Senior Development Guide

## Overview
This guide covers the workflow, standards, and patterns for delivering production-grade software across web, backend, mobile, and platform work. Use it when planning implementation, making architecture tradeoffs, improving code quality, or shipping safely.

## Delivery Workflow

### 1. Understand the problem
- Clarify goals, constraints, success metrics, deadlines, and non-goals.
- Identify unknowns, dependencies, and failure modes.
- Propose a minimal viable technical approach first.
- Define acceptance criteria before implementation.

### 2. Plan implementation
- Break work into small, testable milestones.
- Define interfaces, data contracts, and migration strategy.
- Plan rollback behavior and failure containment.
- Decide what to instrument, monitor, and alert on.

### 3. Implement and verify
- Write clear code with meaningful naming and minimal side effects.
- Add/adjust tests at the right level (unit, integration, E2E).
- Validate backward compatibility and rollout safety.
- Include guardrails for retries, idempotency, and timeouts.

### 4. Ship and stabilize
- Document deployment and rollback procedures.
- Verify behavior in production using logs/metrics/traces.
- Follow up on regressions, incident learnings, and hardening tasks.
- Capture technical debt with clear ownership and priority.

## Engineering Standards
- APIs are explicit about contracts, errors, and compatibility.
- Data changes are migration-safe, reversible when feasible, and monitored.
- Every critical path has telemetry and alerting thresholds.
- Security controls are part of implementation, not post-work.
- Performance budgets exist for latency, throughput, and resource usage.

## Architecture Guidance
- Choose architecture based on current needs plus near-term growth.
- Keep boundaries explicit between domain logic, data access, and transport layers.
- Prefer contracts and typed interfaces over implicit coupling.
- Use feature flags or staged rollouts for risky changes.
- Record architecture decisions for non-trivial tradeoffs.

## Guidelines
- Prefer simple, reversible solutions over clever complexity.
- Optimize for maintainability and operational reliability.
- Match rigor to risk: high-risk changes require stronger validation.
- State assumptions explicitly; do not hide uncertainty.
- Keep changes scoped and production-safe.
- Default to evidence: metrics, tests, logs, traces.

## Scripts

- `scripts/review_checklist.py` -- Analyze a source file for common code review concerns: TODO/FIXME count, long functions, bare excepts, hardcoded secrets, leftover debug statements. Run with `--help` for options.

## References

- [Code Examples](references/code-examples.md) — TypeScript API handler, Python retry wrapper, migration-safe SQL, and CI quality gate.
- [Design Docs & ADRs](references/design-docs.md) — Design document template (filled-in payment processing example), Architecture Decision Record example, and lightweight RFC template.
- [Production Patterns](references/production-patterns.md) — Feature flags with percentage rollout, graceful shutdown, expand-migrate-contract database migrations, structured logging with correlation IDs, circuit breaker, and retry with exponential backoff. All TypeScript.
- [Code Review & Incident Response](references/code-review.md) — Code review checklist, incident response runbook, post-mortem template, and on-call handoff template.
- [Performance Profiling](references/performance-profiling.md) — Node.js profiling with clinic.js and Chrome DevTools, EXPLAIN ANALYZE workflow, pg_stat_statements top queries, N+1 detection, memory leak investigation (3-snapshot heap diff), CPU profiling with worker threads, and a full worked example from "endpoint is slow" to root cause fix.
- [Debugging Strategies](references/debugging-strategies.md) — Git bisect with automated test scripts, structured log correlation across services, HTTP traffic capture and replay, seed-based reproducible test data, race condition debugging with timestamp analysis and lock contention queries, production debug endpoints, verbose logging feature flags, canary deployments, and common bug pattern signatures.
- [Architecture Decisions](references/architecture-decisions.md) — Concrete decision matrices with scoring and thresholds for monolith vs microservices, database selection (PostgreSQL vs MySQL vs MongoDB vs DynamoDB vs Redis), queue selection (SQS vs RabbitMQ vs Kafka), caching strategy with hit rate thresholds and stampede prevention, API style (REST vs GraphQL vs gRPC), and auth strategy (sessions vs JWT vs OAuth2) with security checklists.
- [Team Patterns](references/team-patterns.md) — PR review turnaround SLA by PR size, review comment categories (must-fix/suggestion/learning/praise), tech debt register with severity scoring, on-call runbook template with triage decision tree, story point calibration with reference stories, velocity tracking formulas, brown bag and decision log templates, mentoring framework with pairing progression, and dependency upgrade strategy with Renovate config.
