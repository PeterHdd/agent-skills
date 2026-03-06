# Incident Triage

Use this when the task is "production is broken", "latency spiked", "deploy failed", or "alerts are firing".

## Repo-First Flow

1. Identify what changed last.
2. Identify whether impact is still increasing.
3. Choose mitigation before diagnosis if user-facing impact is active.

## First Checks

- Recent deploys: CI history, release controller events, image tags, feature flags.
- Runtime health: pod restarts, crash loops, container OOMs, health-check failures.
- Dependency health: database saturation, queue backlog, DNS, certificate expiry, third-party status pages.
- Blast radius: one endpoint, one service, one region, or all traffic.

## Rollback Decision Tree

- If the issue started within 4 hours of a deploy and symptoms match the touched service, roll back first.
- If there was no deploy and capacity is exhausted, stabilize with scaling or traffic shedding first.
- If state migrations already ran, check whether the deploy is code-reversible, schema-reversible, or feature-flag-only reversible before acting.

## Evidence To Capture

- Commit SHA, image tag, deploy timestamp.
- Error-rate graph and p95/p99 latency graph.
- Top failing endpoints or queues.
- Recent infrastructure changes.
- Exact mitigations attempted and their results.
