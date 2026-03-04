# Technical Leadership Patterns

## 1) PR Review SLA and Workflow

### Review Turnaround SLA

```
PR SIZE (lines changed)   REVIEW SLA          REVIEWER COUNT
──────────────────────    ──────────────────   ──────────────
< 50 lines (trivial)     < 2 business hours   1 reviewer
50-400 lines (normal)    < 4 business hours   1 reviewer
400-800 lines (large)    < 8 business hours   2 reviewers
> 800 lines (too large)  Push back — ask to   N/A
                          split the PR

RULES:
  - Clock starts when PR is marked "Ready for Review", not when draft is opened.
  - SLA is for first meaningful review pass, not rubber-stamp approval.
  - If reviewer is blocked, they should comment within 1 hour: "Will review by [time]".
  - Stale reviews (no activity for 24h) get auto-reassigned.
  - Author responds to all review comments within 4 business hours.
```

### Review Comment Categories

```
Use prefixes on review comments so the author knows what action is needed:

MUST-FIX:   Blocks merge. Bug, security issue, data loss risk, or contract violation.
            "MUST-FIX: This SQL query is not parameterized — SQL injection risk."

SUGGESTION: Non-blocking. Author decides. Better approach, readability improvement.
            "SUGGESTION: Consider using a Map here instead of filter+find for O(1) lookup."

QUESTION:   Clarification needed. Author should explain or add a comment in the code.
            "QUESTION: Why do we retry 5 times here? Is there a specific failure mode?"

LEARNING:   Teaching moment. Not a change request. Shares context or technique.
            "LEARNING: This pattern is called 'circuit breaker' — see [link] for deep dive."

NIT:        Style/cosmetic. Fix if easy, skip if not. Never block merge for nits.
            "NIT: Inconsistent spacing in this block."

PRAISE:     Positive feedback. Call out good patterns. Important for team morale.
            "PRAISE: Great error handling here — the retry with idempotency key is solid."
```

---

## 2) Tech Debt Tracking

### ADR-Linked Tech Debt Register

```markdown
# Tech Debt Register

| ID     | Severity | ADR Link  | Description                          | Owner        | Created    | Target     |
|--------|----------|-----------|--------------------------------------|--------------|------------|------------|
| TD-001 | HIGH     | ADR-0042  | MongoDB order data lacks ACID txns   | @order-team  | 2024-09-01 | 2024-11-15 |
| TD-002 | MEDIUM   | ADR-0038  | Auth service uses HS256 JWT signing  | @auth-team   | 2024-08-15 | 2025-Q1    |
| TD-003 | LOW      | —         | Unused feature flag cleanup (47 flags)| @platform   | 2024-10-01 | 2025-Q1    |
| TD-004 | HIGH     | ADR-0045  | No statement timeout on payment DB   | @payment-team| 2024-01-16 | 2024-02-01 |
| TD-005 | MEDIUM   | —         | Test suite takes 18 min (target: 5m) | @devtools    | 2024-07-20 | 2025-Q1    |
```

### Severity Scoring

```
SEVERITY   CRITERIA                                              POINTS   ACTION TIMELINE
────────   ─────────────────────────────────────────────────     ──────   ──────────────
CRITICAL   Causes incidents. Data loss risk. Security vuln.      10       Fix this sprint
HIGH       Slows development 2x+. Causes regular incidents.      7        Fix within 4 weeks
MEDIUM     Developer friction. Workarounds exist but are messy.  4        Fix within 1 quarter
LOW        Cosmetic. "We should fix this someday."               2        Backlog — fix if convenient

TRIAGE RULE:
  Total tech debt score = SUM of all item points.
  Allocate 20% of sprint capacity to tech debt when total > 30 points.
  Allocate 30% when total > 50 points.
  Stop feature work and focus on debt when total > 80 points.
```

---

## 3) On-Call Runbook Template

```markdown
# Runbook: [Service/Alert Name]

## Alert Details
- **Alert name:** `order_service_error_rate_high`
- **Threshold:** 5xx error rate > 5% over 5-minute window
- **Severity:** SEV-2 (user-facing degradation)
- **Dashboard:** [Link to Grafana dashboard]
- **Logs:** [Link to log query pre-filtered for this service]

## Detection Checklist (first 2 minutes)
- [ ] Check the alert dashboard — is the error rate still elevated?
- [ ] Check recent deploys: `kubectl rollout history deployment/order-service`
- [ ] Check downstream dependencies: are payment-service, inventory-service healthy?
- [ ] Check infrastructure: CPU, memory, disk, connection pool on the pod dashboard.

## Triage Decision Tree (minutes 2-5)
```
Is there a deploy in the last 2 hours?
├─ YES → Check the diff. Is the error related to new code?
│   ├─ YES → Rollback: kubectl rollout undo deployment/order-service
│   └─ NO → Continue to next check
└─ NO
   Is a downstream dependency degraded?
   ├─ YES → Check if circuit breaker is open. Page the owning team.
   │   Mitigation: enable fallback/cached response if available.
   └─ NO
      Is there a traffic spike (> 2x normal)?
      ├─ YES → Scale up: kubectl scale deployment/order-service --replicas=10
      └─ NO → Investigate application logs for error pattern.
```

## Mitigation Actions
| Action                        | Command / Steps                                    | Risk  |
|-------------------------------|----------------------------------------------------|-------|
| Rollback last deploy          | `kubectl rollout undo deployment/order-service`    | Low   |
| Scale up pods                 | `kubectl scale deployment/order-service --replicas=N` | Low |
| Enable maintenance mode       | Set feature flag `order_service_maintenance=true`  | Med   |
| Kill long-running DB queries  | See SQL in incident response runbook               | Med   |
| Restart all pods              | `kubectl rollout restart deployment/order-service` | Med   |
| Failover to read replica      | Update config: `DB_HOST=replica.db.internal`       | High  |

## Resolution
- [ ] Confirm error rate returns to baseline (< 0.5% for 10 minutes).
- [ ] Confirm no data inconsistency from the incident.
- [ ] Notify stakeholders in #incidents Slack channel.

## Postmortem Trigger
File a postmortem if ANY of these are true:
- Incident lasted > 15 minutes.
- Revenue impact > $1,000.
- Customer data was affected.
- Same root cause as a previous incident.
```

---

## 4) Sprint Planning Patterns

### Story Point Calibration

```
Define reference stories that the team agrees on. All future estimates
are relative to these anchors.

POINTS   REFERENCE STORY                                          TIME PROXY
──────   ──────────────────────────────────────────────────────   ──────────
1        Add a new field to an existing API response               < 2 hours
2        Add a new endpoint with validation and tests              2-4 hours
3        Build a CRUD feature with DB migration and tests          1-2 days
5        Integrate a third-party API with error handling,          2-3 days
         retries, and monitoring
8        Design and build a new service/module with multiple       3-5 days
         endpoints, data model, and integration tests
13       Cross-service feature requiring API contracts, data       1-2 weeks
         migration, and coordinated rollout

RULES:
  - Never estimate > 13 points. If it feels > 13, break it down.
  - Estimates are for the whole team effort (code + review + QA + deploy).
  - If 3 people disagree by > 2x, discuss — there's a hidden assumption.
  - Track actual vs estimated over 5 sprints to calibrate.
```

### Velocity Tracking

```
Sprint velocity = total story points completed (not started, not in review — DONE).

HEALTHY PATTERNS:
  Velocity is stable (within +/- 20%) over 4-sprint rolling average.
  Team completes 80-90% of committed stories per sprint.

WARNING SIGNS:
  Velocity drops > 30% for 2 sprints → investigate: tech debt? unclear requirements?
  Velocity increases > 40% suddenly → are stories being underestimated?
  Completion rate < 70% consistently → team is overcommitting. Reduce capacity by 20%.

SPRINT CAPACITY FORMULA:
  Available points = (rolling 4-sprint avg velocity) * (available dev days / total dev days)
  Example: avg velocity 34, team has 8 of 10 dev days (2 days PTO) → capacity = 34 * 0.8 = 27 points
  Commit to 27 points, not 34.
```

---

## 5) Knowledge Sharing

### Brown Bag Session Template

```markdown
# Brown Bag: [Topic Title]
**Presenter:** [Name]
**Date:** [YYYY-MM-DD]
**Duration:** 30 minutes (20 min talk + 10 min Q&A)

## Why This Matters
- [1-2 sentences: why should the audience care? What problem does this solve?]

## Key Concepts (3-5 max)
1. **[Concept]** — [One-sentence explanation]
2. **[Concept]** — [One-sentence explanation]
3. **[Concept]** — [One-sentence explanation]

## Live Demo / Code Walkthrough
- [Describe what you will show — a working example is worth 100 slides]
- [Link to demo repo or branch]

## Takeaways
- [What should attendees do differently after this session?]
- [Link to further reading]

## Recording
- [Link to recording — always record for async team members]
```

### Decision Log Format

```markdown
# Decision Log

| Date       | Decision                              | Context (why)                          | Decided By     | Revisit Date |
|------------|---------------------------------------|----------------------------------------|----------------|--------------|
| 2024-10-01 | Use Kafka for event streaming         | Need replay capability for analytics   | @eng-leads     | 2025-04-01   |
| 2024-09-15 | Adopt TypeScript for all new services | 3 production bugs from type errors/mo  | @team-vote     | Never        |
| 2024-09-01 | 20% sprint time for tech debt         | Tech debt score exceeded 50 points     | @eng-manager   | Per sprint   |
| 2024-08-20 | Require 2 reviewers for DB migrations | Post-mortem action item from INC-789   | @postmortem    | 2025-02-20   |

RULES:
  - Every non-trivial technical decision gets a row.
  - "Revisit Date" prevents decisions from becoming permanent by default.
  - Decisions are NOT permanent — they should be revisited when context changes.
  - Link to ADR when the decision is complex enough to warrant one.
```

---

## 6) Mentoring: Code Review as Teaching

### The 30-60-10 Review Rule

```
When reviewing a junior engineer's PR, allocate your comments:

30% — MUST-FIX: Actual bugs, security issues, or correctness problems.
      These protect the codebase. Be direct, explain the impact.

60% — LEARNING: Teaching moments. Explain WHY, not just WHAT.
      Bad:  "Use a Map here."
      Good: "LEARNING: A Map gives O(1) lookup vs O(n) for Array.find().
             With 10k items, that is the difference between 0.001ms and 10ms.
             Here is the refactored version: [code snippet]"

10% — PRAISE: Reinforce good patterns. Engineers repeat what gets praised.
      "PRAISE: Love that you added the circuit breaker here —
       this will prevent cascading failures to the payment service."
```

### Pairing Framework for New Team Members

```
WEEK 1-2: Shadow mode.
  - New engineer watches senior engineer work on real tasks.
  - Senior narrates decision-making process out loud.
  - New engineer asks questions freely. No code expectations.

WEEK 3-4: Driver mode.
  - New engineer drives (writes code), senior navigates.
  - Senior reviews in real-time, teaching patterns as they come up.
  - Target: 1 small PR merged per day with guidance.

WEEK 5-8: Solo with safety net.
  - New engineer works independently on scoped tasks.
  - Senior does thorough (LEARNING-heavy) code reviews.
  - Target: 2-3 PRs per week with decreasing review comment density.

WEEK 9+: Full contributor.
  - Normal review process. Senior is available for questions.
  - New engineer starts reviewing OTHER people's PRs (builds judgment).
```

---

## 7) Dependency Upgrade Strategy

### Automated Upgrades (Renovate Config)

```json5
// renovate.json — Practical config for a production service
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "schedule": ["before 8am on Monday"],  // batch all updates to start of week
  "prConcurrentLimit": 5,                // don't flood with PRs
  "packageRules": [
    {
      // Auto-merge patch updates for non-critical deps (test, lint, types)
      "matchUpdateTypes": ["patch"],
      "matchPackagePatterns": ["eslint", "@types/*", "prettier", "jest"],
      "automerge": true,
      "automergeType": "branch"
    },
    {
      // Group all AWS SDK updates into one PR
      "matchPackagePatterns": ["@aws-sdk/*"],
      "groupName": "AWS SDK",
      "schedule": ["before 8am on the first day of the month"]
    },
    {
      // Major version bumps always need manual review
      "matchUpdateTypes": ["major"],
      "automerge": false,
      "labels": ["dependency-major", "needs-review"],
      "assignees": ["@tech-lead"]
    },
    {
      // Critical security patches merge ASAP, no schedule restriction
      "matchCategories": ["security"],
      "schedule": ["at any time"],
      "automerge": true,
      "prPriority": 10,
      "labels": ["security"]
    },
    {
      // Pin database drivers — never auto-upgrade
      "matchPackageNames": ["pg", "ioredis", "mongoose"],
      "enabled": false  // manual upgrades only for data-layer deps
    }
  ]
}
```

### Manual Review Criteria

```
AUTO-MERGE (no human review needed):
  - Patch version of dev dependencies (eslint, prettier, jest, @types/*)
  - Patch version of well-tested libraries with good semver discipline
  - Security patches flagged by Dependabot/Renovate

REVIEW REQUIRED (tech lead or domain owner):
  - Any MAJOR version bump (breaking changes expected)
  - Minor version of database drivers (pg, ioredis, prisma)
  - Minor version of auth libraries (jsonwebtoken, passport)
  - Any change to the Node.js/runtime version
  - Framework upgrades (Express, Next.js, NestJS)

REVIEW CHECKLIST for manual upgrades:
  [ ] Read the CHANGELOG for breaking changes
  [ ] Check GitHub issues for known regressions in the new version
  [ ] Run full test suite (not just unit — include integration and E2E)
  [ ] Check bundle size impact (for frontend deps)
  [ ] Check if peer dependencies changed
  [ ] Test in staging for 24 hours before promoting to production
  [ ] If database driver: test connection pooling, query performance, failover
```

### Upgrade Scheduling

```
FREQUENCY        SCOPE                          PROCESS
─────────────    ──────────────────────────     ────────────────────────────────────
Weekly           Automated patches              CI merges automatically if green
Monthly          Minor version bumps            Batch into 1 PR, review + staging
Quarterly        Major version upgrades         Dedicated sprint task, migration plan
Immediately      Security vulnerabilities        Drop current work, patch, deploy
Annually         Runtime version (Node.js)      Plan as a project, 1-2 sprint effort
```
