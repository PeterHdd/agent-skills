# Design Documents, ADRs & RFCs

## 1) Design Document — Add Payment Processing to E-Commerce Platform

### Context & Problem

Our e-commerce platform currently redirects users to a third-party hosted checkout page (Stripe Checkout) for all payments. This adds 3-5 seconds of latency per transaction, prevents us from customizing the payment UX, and blocks planned features like split payments and saved payment methods. Conversion analytics show a 12% cart abandonment rate at the redirect step. We need to bring payment processing in-house using Stripe's API directly while maintaining PCI DSS compliance.

### Goals

- Integrate Stripe Payment Intents API for direct on-site card payments.
- Support credit/debit cards at launch; Apple Pay and Google Pay in a fast-follow.
- Reduce payment flow latency from ~5s to under 1s.
- Maintain PCI DSS SAQ-A-EP compliance (no raw card data touches our servers).
- Enable saved payment methods for returning customers within 30 days of launch.

### Non-Goals

- Building our own payment gateway or tokenization.
- Supporting cryptocurrency, wire transfers, or buy-now-pay-later at launch.
- Migrating historical transaction records from the old Stripe Checkout integration.

### Proposed Solution

**Architecture Overview:**
Client-side Stripe Elements collects card details and produces a `PaymentMethod` token. Our backend creates a `PaymentIntent` with the token, confirms the charge, and records the outcome. Webhooks handle async events (disputes, refunds, delayed confirmations).

```
Browser (Stripe Elements) --> POST /api/payments/intent --> Payment Service
Payment Service --> Stripe API (create + confirm PaymentIntent)
Stripe --> Webhook /api/webhooks/stripe --> Payment Service --> Order Service
```

**Key components:**
1. **Payment Service** — new service owning all Stripe API interactions, idempotency keys, and payment state machine (pending -> processing -> succeeded/failed).
2. **Webhook Handler** — validates Stripe signatures, deduplicates events by `event.id`, dispatches to order fulfillment.
3. **Client SDK** — thin wrapper around Stripe Elements for our checkout page with error handling and retry UI.

### Alternatives Considered

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| Keep Stripe Checkout (status quo) | Zero PCI scope, simple | Slow UX, no customization, blocks saved cards | Rejected |
| Braintree Drop-In UI | Similar to Stripe Elements | Migration cost, team has no Braintree experience | Rejected |
| Adyen with server-side encryption | Supports more payment methods | Higher PCI scope (SAQ-D), complex integration | Rejected |
| Stripe Elements (chosen) | Low PCI scope, full UX control, team familiarity | More code than hosted checkout | **Selected** |

### Data Model Changes

```sql
-- New table for payment records
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    stripe_payment_intent_id TEXT UNIQUE NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    currency TEXT NOT NULL DEFAULT 'usd',
    status TEXT NOT NULL DEFAULT 'pending',
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status) WHERE status IN ('pending', 'processing');
```

### API Changes

```
POST /api/payments/intent
  Request:  { orderId: string, paymentMethodId: string, idempotencyKey: string }
  Response: { paymentId: string, status: "succeeded" | "requires_action" | "failed", clientSecret?: string }

POST /api/webhooks/stripe
  Stripe signature-verified webhook endpoint. No public documentation.
```

### Rollback Plan

1. Feature flag `payments.use_direct_integration` gates the new flow. Default off.
2. If critical issues arise, disable the flag to revert to Stripe Checkout redirect.
3. No database rollback needed: the `payments` table is additive. Old flow ignores it.
4. Client bundle includes both checkout paths; flag determines which renders.

### Metrics & Monitoring

- `payment.intent.created` / `payment.intent.succeeded` / `payment.intent.failed` counters.
- `payment.latency_ms` histogram (p50, p95, p99) — alert if p99 > 3000ms.
- `webhook.received` / `webhook.processed` / `webhook.failed` counters — alert if failed > 1% of received over 5m window.
- Stripe Dashboard cross-referenced with internal records daily via reconciliation job.

### Timeline

- **Week 1-2:** Payment Service skeleton, Stripe API integration, unit tests.
- **Week 3:** Webhook handler, idempotency, integration tests with Stripe test mode.
- **Week 4:** Client-side Stripe Elements integration, E2E tests.
- **Week 5:** Internal dogfood with 1% of traffic via feature flag. Monitoring bake.
- **Week 6:** Ramp to 100%. Remove old checkout code path after 2-week stabilization.

---

## 2) Architecture Decision Record — Use PostgreSQL Over MongoDB for Order Data

**ADR-0042: Use PostgreSQL for Order Data Storage**

**Status:** Accepted (2024-09-12)

**Context:**
Our order system currently stores order data in MongoDB. As the business grew, we encountered increasing issues: lack of transactions across collections leads to inconsistent order states during payment + inventory updates, ad-hoc queries for finance reporting require complex aggregation pipelines that time out, and the flexible schema has led to 14 different implicit "shapes" of order documents with no enforcement. The team spends roughly 20% of incident response time on data inconsistency bugs traceable to missing transactional guarantees. We are evaluating whether to stay on MongoDB with stricter application-level controls or migrate to PostgreSQL.

**Decision:**
We will migrate order data from MongoDB to PostgreSQL. Orders, line items, and payment records will be stored in normalized relational tables with foreign key constraints and transactional writes. We will use the expand-migrate-contract pattern over 8 weeks: dual-write for 2 weeks, backfill and verify, then cut reads over.

**Consequences:**

*Positive:*
- ACID transactions eliminate the class of data inconsistency bugs (~3 incidents/quarter).
- Finance team can query order data directly with standard SQL, removing the need for custom ETL.
- Schema enforcement via constraints catches bugs at write time rather than downstream.
- Team already operates PostgreSQL for 4 other services; no new operational knowledge needed.

*Negative:*
- Migration will take 6-8 weeks of engineering time including dual-write, backfill, and verification.
- Loses MongoDB's flexible document model; future schema changes require migrations.
- Some queries that leveraged nested document structure will need joins or materialized views.

**Compliance:**
Order data includes PII (customer names, emails, addresses). PostgreSQL deployment will use the same encryption-at-rest (AWS RDS) and column-level encryption for sensitive fields that MongoDB currently uses. No change to data classification or retention policies.

---

## 3) RFC Template — Lightweight Request for Comments

```markdown
# RFC: [Title]

**Author:** [Name]
**Date:** [YYYY-MM-DD]
**Status:** Draft | In Review | Accepted | Rejected

## Problem
What is broken, missing, or suboptimal? Include data: error rates, user complaints,
developer friction metrics. Be specific — "authentication is slow" is weak;
"P95 login latency is 4.2s, 3x our 1.5s SLO, due to synchronous LDAP lookup" is strong.

## Proposal
What do you want to do? Include enough technical detail that a senior engineer could
evaluate feasibility. Diagrams, pseudocode, or API sketches help. Call out what this
does NOT cover.

## Impact
- **Services affected:** list them.
- **Migration required:** yes/no, estimated effort.
- **Risk:** what could go wrong, and what is the mitigation.
- **Cost:** infrastructure, third-party, engineering time.

## Open Questions
- [ ] Question 1 — who is responsible for answering, by when.
- [ ] Question 2 — dependency on another team's decision.
```
