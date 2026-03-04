---
name: engineering-backend-architect
description: "Architect scalable backend systems, database schemas, APIs, and cloud infrastructure for robust server-side applications. Use when you need microservice vs monolith decisions, database indexing strategies, API versioning, event-driven architecture, ETL pipelines, WebSocket streaming, data modeling, query optimization, or cloud-native service design with high reliability and sub-20ms query performance."
metadata:
  version: "1.0.0"
---

# Backend Architecture Guide

## Overview
This guide covers scalable backend system design, database architecture, API development, and cloud infrastructure patterns. Use it when making decisions about data schemas, service boundaries, caching strategies, security architecture, or performance optimization.

## Architecture Decision Rules

### System Design
- When choosing between microservices and a monolith, start with a modular monolith unless the team already operates multiple services in production -- microservices add deployment and observability cost that slows small teams.
- When designing database schemas, add partial indexes on high-cardinality columns filtered by common WHERE clauses (e.g., `WHERE is_active = true`) because full-table indexes waste I/O on rows that queries never touch.
- When versioning APIs, use URL-prefix versioning (`/v1/`, `/v2/`) for public APIs and header versioning for internal APIs because URL prefixes are easier for external consumers to discover and cache.
- When building event-driven systems, ensure every event includes a unique idempotency key and a schema version field so consumers can safely retry and handle schema evolution.

### Reliability
- When a downstream service is unreliable, wrap calls in a circuit breaker (e.g., `opossum` for Node.js) -- open after 5 consecutive failures, half-open after 30 seconds, close after 3 successes.
- When designing backup strategies, combine continuous WAL archiving with daily base backups and test restores weekly against a staging database to verify RTO/RPO targets.
- When implementing health checks, expose `/health/live` (process is running) and `/health/ready` (dependencies are reachable) as separate endpoints because Kubernetes liveness and readiness probes serve different purposes.

### Performance
- When Redis is used for caching, set TTLs explicitly on every key and use cache-aside (lazy loading) rather than write-through unless write latency is more important than read consistency.
- When processing large datasets, use cursor-based pagination instead of OFFSET/LIMIT because OFFSET scans and discards rows, degrading linearly with page depth.
- When designing a new service, ensure it is stateless so any instance can handle any request; store session data in Redis or a database so horizontal scaling requires only adding instances behind the load balancer.
- When adding a new query path, run `EXPLAIN ANALYZE` before merging and reject any query that performs a sequential scan on a table with more than 10k rows -- add an index or rewrite the query.
- When introducing a cache layer, define an explicit invalidation strategy (TTL, event-driven purge, or versioned keys) in the design doc before implementation to prevent stale reads.

### Security
- When designing authentication, require token validation at the API gateway AND again in each downstream service to prevent lateral movement if one layer is compromised.
- When implementing authentication, issue short-lived JWTs (15 min) with opaque refresh tokens stored server-side because stolen JWTs cannot be revoked before expiry.
- When configuring service IAM roles, start with zero permissions and add only the specific actions needed; review and prune unused permissions quarterly using cloud provider access analyzer reports.
- When storing data, encrypt at rest with AES-256 (or provider-managed KMS keys) and enforce TLS 1.2+ for all service-to-service communication; reject plaintext connections at the load balancer.
- When accepting user input, validate and sanitize at the API boundary using a schema validator (e.g., Zod, Joi) and use parameterized queries exclusively -- never interpolate user input into SQL or NoSQL queries.

### Monitoring
- When deploying to production, require that every service emits latency histograms and error rate counters to the metrics system; set alerts for p95 latency exceeding 2x the baseline measured during load tests.

## Scripts

- `scripts/check_api_health.sh` -- Probe common health endpoints (/health, /healthz, /ready, etc.) on a base URL and report status, response time, and body preview. Run with `--help` for usage.
- `scripts/analyze_schema.py` -- Analyze a SQL file for CREATE TABLE statements and report table count, columns, missing indexes, missing primary keys, and foreign key relationships. Run with `--help` for options.

See [Code Examples](references/code-examples.md) for SQL schema, Express API, and rate limiter patterns.

See [Infrastructure](references/infrastructure.md) for Terraform and CloudWatch alarm configuration.

See [Distributed Patterns](references/distributed-patterns.md) for circuit breaker, saga, outbox, distributed lock, and idempotent event processing patterns.

See [Database Patterns](references/database-patterns.md) for connection pooling, read replica routing, migrations, sharding, query optimization, and caching.

See [API Patterns](references/api-patterns.md) for cursor pagination, rate limiting, versioning, validation, webhook delivery, and DataLoader batching.

## Reference

### Data Schema Design Checklist
- Define schemas with constraints (NOT NULL, CHECK, UNIQUE) at the database level.
- Use partial indexes on filtered queries to reduce I/O.
- Design for large-scale datasets (100k+ entities) with sub-20ms query targets.
- Plan ETL pipelines for data transformation and unification.
- Validate schema compliance and maintain backwards compatibility.
- Use parameterized queries exclusively for all user-facing input.

### Streaming and Real-Time
- Stream real-time updates via WebSocket with guaranteed ordering.
- Use cursor-based pagination for large result sets.
- Batch network requests where possible to reduce overhead.
