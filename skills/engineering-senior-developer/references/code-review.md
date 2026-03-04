# Code Review, Incident Response & Post-Mortems

## 1) Code Review Checklist

### Correctness
- [ ] Are edge cases handled? (empty inputs, null, boundary values, max size)
- [ ] Are all error paths handled explicitly? (no swallowed exceptions, no bare `catch {}`)
- [ ] Is concurrent access safe? (shared mutable state, race conditions, deadlocks)
- [ ] Are external calls idempotent or guarded with deduplication?
- [ ] Do retry/timeout paths behave correctly? (no infinite loops, no leaked resources)
- [ ] Are off-by-one errors possible in loops or pagination?
- [ ] Does the code handle partial failures? (what if step 2 of 3 fails?)

### Security
- [ ] Are all user inputs validated and sanitized before use?
- [ ] Are SQL queries parameterized? (no string concatenation for queries)
- [ ] Are auth checks enforced at the right layer? (not just client-side)
- [ ] Are secrets absent from source code, logs, and error messages?
- [ ] Are API responses filtered to exclude internal data the caller should not see?
- [ ] Are file uploads, redirects, and deserialization validated?
- [ ] Are CORS, CSP, and rate-limiting configured for new endpoints?

### Performance
- [ ] Are there N+1 query patterns? (fetching related data in a loop)
- [ ] Are lists or maps unbounded? (could they grow without limit in production?)
- [ ] Are new queries covered by indexes? (check the query plan)
- [ ] Is pagination enforced on list endpoints?
- [ ] Are expensive operations cached appropriately? (with invalidation strategy)
- [ ] Are large payloads streamed instead of buffered in memory?
- [ ] Are database transactions held open for the minimum necessary duration?

### Maintainability
- [ ] Do names accurately describe behavior? (no misleading function/variable names)
- [ ] Does each function/class have a single clear responsibility?
- [ ] Are magic numbers and strings extracted into named constants?
- [ ] Is there adequate test coverage for the changed code paths?
- [ ] Are public interfaces documented? (especially non-obvious parameters and return values)
- [ ] Is dead code removed rather than commented out?
- [ ] Are dependencies justified? (no new library for something trivially implementable)

### Operational Readiness
- [ ] Are new code paths instrumented with metrics and logging?
- [ ] Are feature flags or gradual rollout mechanisms in place for risky changes?
- [ ] Is the change backward-compatible with in-flight requests during deploy?
- [ ] Are database migrations reversible or safely additive?
- [ ] Is the rollback plan documented or obvious?

---

## 2) Incident Response Runbook — Database Connection Pool Exhaustion

### Detection
**Alert:** `db.connection_pool.available < 2 for 3 minutes` triggered on PagerDuty.
**Dashboard:** Grafana panel "DB Connection Pool" shows available connections at 0, wait queue growing. Application logs show `Error: connection pool timeout after 30000ms`.

### Severity Assessment
| Signal | Value | Implication |
|---|---|---|
| Error rate (5xx) | >25% of requests | User-facing impact |
| Affected services | order-service, payment-service | Revenue path impacted |
| Duration so far | 8 minutes | Assign Sev-1 if not resolving |

**Severity: Sev-1** — Revenue-impacting, customer-facing degradation.

### Immediate Mitigation (first 10 minutes)
1. **Check for long-running queries:**
   ```sql
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
   FROM pg_stat_activity
   WHERE state != 'idle' ORDER BY duration DESC LIMIT 20;
   ```
2. **Kill stuck queries** if safe (read-only or known-safe):
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity
   WHERE duration > interval '5 minutes' AND query NOT LIKE '%backup%';
   ```
3. **Temporarily increase pool size** if the database can handle it:
   Update `DB_POOL_MAX` from 20 to 40 via config and restart pods incrementally.
4. **Divert traffic** if mitigation is not working: enable maintenance page or shift to read-replica for non-write paths.

### Root Cause Investigation
- Check recent deploys: did a new code path introduce a connection leak? (`git log --since="6 hours ago" --oneline`)
- Check for missing connection release: search for `db.query()` calls without `.release()` or outside a `using` / `try-finally` block.
- Check for transaction deadlocks: `SELECT * FROM pg_locks WHERE NOT granted;`
- Check for traffic spike: compare request rate to normal baseline in metrics dashboard.

### Resolution
- Identify the leaking code path and deploy a fix (or revert the offending commit).
- Restart affected pods to reclaim leaked connections.
- Verify pool utilization returns to baseline on the dashboard.

### Post-Incident Tasks
- [ ] Write post-mortem within 48 hours.
- [ ] Add connection pool utilization alert with lower threshold for early warning.
- [ ] Add integration test that verifies connections are released under error conditions.
- [ ] Audit all database query paths for proper connection release.

---

## 3) Post-Mortem — Payment Processing Outage 2024-01-15

### Summary
On January 15, 2024, the payment processing service experienced a complete outage lasting 47 minutes. Customers could not complete purchases. The root cause was an unindexed database query introduced in the previous day's deploy that caused full table scans under production load, exhausting database connections and CPU.

### Impact
- **Duration:** 47 minutes (14:23 UTC to 15:10 UTC).
- **Users affected:** ~12,400 users received errors attempting to check out.
- **Failed transactions:** 3,847 orders failed to process.
- **Estimated revenue impact:** $184,000 in delayed or lost sales.
- **SLA impact:** Monthly uptime dropped from 99.97% to 99.89% (below 99.95% SLA).

### Timeline (all times UTC)
| Time | Event |
|---|---|
| 13:45 | Deploy `payment-service v2.41.0` containing new fraud-check query. |
| 14:15 | Database CPU rises above 80%. Connection pool wait times increasing. |
| 14:23 | Alert fires: `payment.error_rate > 10%`. On-call engineer paged. |
| 14:28 | Engineer confirms elevated 5xx rate. Begins investigating. |
| 14:35 | Identifies `fraud_checks` query doing full table scan on 48M row table. |
| 14:40 | Decision: rollback deploy. Initiates revert to `v2.40.3`. |
| 14:52 | Rollback deploy completes. Database CPU falling. |
| 15:02 | Error rate returns to baseline. Connection pool recovering. |
| 15:10 | All systems nominal. Incident closed. |

### Root Cause
The `v2.41.0` deploy included a new fraud-detection query that filtered on `transactions.risk_score` — a column with no index. Under low-volume testing this query ran in ~200ms. At production volume (48M rows), it triggered full table scans averaging 12 seconds, consuming all available database connections and CPU.

### Contributing Factors
1. **No query plan review in CI** — the query was syntactically correct and passed unit tests with a small dataset. No process caught the missing index.
2. **Staging environment has 500x less data** — the performance problem was invisible in staging.
3. **No per-query timeout** — the application-level statement timeout was set to 30 seconds (too generous), allowing slow queries to pile up.

### Action Items
| Action | Owner | Due |
|---|---|---|
| Add index on `transactions.risk_score` | @db-team | 2024-01-17 |
| Set statement timeout to 5s for the payment service | @platform | 2024-01-19 |
| Add CI step that runs `EXPLAIN ANALYZE` on new queries against a production-sized dataset | @devtools | 2024-02-01 |
| Add staging data generator to produce realistic data volumes | @devtools | 2024-02-15 |
| Add per-query latency metrics with alerting at p99 > 1s | @payment-team | 2024-01-22 |

### Lessons Learned
- **Query performance testing must happen at production scale.** Unit tests with 10 rows will never catch a missing index on a 48M row table.
- **Deploy observability matters as much as pre-deploy testing.** The 30-minute gap between deploy and alert detection was too long. Canary deploys with automatic rollback on error rate spike would have caught this in under 5 minutes.
- **Statement timeouts are a safety net, not optional.** A 5-second timeout would have prevented connection pool exhaustion entirely — queries would fail fast instead of piling up.

---

## 4) On-Call Handoff Template

```markdown
# On-Call Handoff — [Date]

## Active Incidents
- [ ] [INC-1234] Brief description. Current status. Link to incident channel.

## Recent Deploys (last 48h)
- `order-service v3.12.0` — deployed 2024-01-14 16:00 UTC. Adds bulk discount logic. Rollback: revert to v3.11.2.
- `auth-service v1.8.1` — deployed 2024-01-14 09:00 UTC. Patches token refresh bug.

## Known Issues
- Intermittent 502s from `inventory-service` under high load. Tracked in JIRA-5678. Mitigation: pod auto-scaling is active.
- Cache warming job for product catalog runs slow on Mondays. Usually resolves by 08:00 UTC.

## Escalation Contacts
- **Database issues:** @db-oncall (Slack) or page via PagerDuty "Database" service.
- **Payment/Stripe issues:** @payments-lead (phone number in PagerDuty).
- **Infrastructure/AWS:** @platform-oncall.

## Upcoming Maintenance
- **2024-01-16 02:00-04:00 UTC:** RDS failover test for `orders-db`. Expect ~30s of read-only mode.
- **2024-01-17:** CDN certificate rotation. Automated, but monitor for TLS errors.
```
