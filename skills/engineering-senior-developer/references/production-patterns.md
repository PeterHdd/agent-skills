# Production Engineering Patterns

## 1) Feature Flag System with Percentage Rollout and User Targeting

```ts
interface FeatureFlag {
  name: string;
  enabled: boolean;               // kill switch — false overrides everything
  rolloutPercent: number;          // 0-100, percentage of users who see the feature
  allowList: Set<string>;          // user IDs that always get the feature
  denyList: Set<string>;           // user IDs that never get the feature
}

const flags = new Map<string, FeatureFlag>();

export function registerFlag(flag: FeatureFlag): void {
  flags.set(flag.name, flag);
}

export function isEnabled(flagName: string, userId: string): boolean {
  const flag = flags.get(flagName);
  if (!flag || !flag.enabled) return false;        // kill switch
  if (flag.denyList.has(userId)) return false;      // explicit deny
  if (flag.allowList.has(userId)) return true;      // explicit allow

  // Deterministic percentage: hash the user+flag so the same user gets a
  // consistent result without storing state.
  const hash = simpleHash(`${flagName}:${userId}`);
  return (hash % 100) < flag.rolloutPercent;
}

function simpleHash(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    hash = ((hash << 5) - hash + input.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

// Usage:
// registerFlag({ name: "new-checkout", enabled: true, rolloutPercent: 10,
//                allowList: new Set(["user-beta-1"]), denyList: new Set() });
// if (isEnabled("new-checkout", req.userId)) { ... }
```

## 2) Graceful Shutdown — Node.js / Express

```ts
import http from "node:http";
import type { Express } from "express";

export function enableGracefulShutdown(
  app: Express,
  deps: { db: { close(): Promise<void> }; logger: { flush(): Promise<void> } },
  opts = { drainTimeoutMs: 15_000 }
): void {
  const server = app.listen(Number(process.env.PORT) || 3000);
  const connections = new Set<import("net").Socket>();

  server.on("connection", (conn) => {
    connections.add(conn);
    conn.on("close", () => connections.delete(conn));
  });

  let shuttingDown = false;

  async function shutdown(signal: string): Promise<void> {
    if (shuttingDown) return;
    shuttingDown = true;
    console.log(`Received ${signal}. Starting graceful shutdown...`);

    // 1. Stop accepting new connections.
    server.close();

    // 2. Health check endpoint returns 503 so load balancer stops routing.
    app.use((_req, res) => res.status(503).json({ error: "shutting down" }));

    // 3. Drain in-flight requests with a hard timeout.
    const drainTimeout = setTimeout(() => {
      console.warn("Drain timeout reached. Forcibly closing connections.");
      for (const conn of connections) conn.destroy();
    }, opts.drainTimeoutMs);

    // Wait for server to finish open requests.
    await new Promise<void>((resolve) => server.on("close", resolve));
    clearTimeout(drainTimeout);

    // 4. Close downstream dependencies.
    await deps.db.close();
    await deps.logger.flush();

    console.log("Shutdown complete.");
    process.exit(0);
  }

  process.on("SIGTERM", () => shutdown("SIGTERM"));
  process.on("SIGINT", () => shutdown("SIGINT"));
}
```

## 3) Database Migration Safety — Expand-Migrate-Contract

The pattern for renaming `invoices.ref` to `invoices.external_reference` without downtime.

**Step 1 — Expand: add the new column (nullable, no breaking change).**
```sql
-- Migration 001_add_external_reference.sql
ALTER TABLE invoices ADD COLUMN external_reference TEXT NULL;
```

**Step 2 — Dual-write: application writes to both columns.**
```ts
// In the repository layer during the transition period:
async function createInvoice(data: InvoiceInput): Promise<Invoice> {
  return db.query(
    `INSERT INTO invoices (customer_id, amount, ref, external_reference)
     VALUES ($1, $2, $3, $3)
     RETURNING *`,
    [data.customerId, data.amount, data.ref]
  );
}

async function updateInvoiceRef(id: string, newRef: string): Promise<void> {
  await db.query(
    `UPDATE invoices SET ref = $1, external_reference = $1 WHERE id = $2`,
    [newRef, id]
  );
}
```

**Step 3 — Backfill: copy existing data from old column to new column.**
```sql
-- Migration 002_backfill_external_reference.sql
-- Run in batches in production to avoid locking the table.
UPDATE invoices
SET external_reference = ref
WHERE external_reference IS NULL
  AND id IN (SELECT id FROM invoices WHERE external_reference IS NULL LIMIT 5000);
-- Repeat until 0 rows updated. Monitor replication lag between batches.
```

**Step 4 — Switch reads: application reads from new column, still writes both.**
```sql
-- Migration 003_add_not_null_constraint.sql
-- Only after backfill is verified complete:
ALTER TABLE invoices ALTER COLUMN external_reference SET NOT NULL;
```

**Step 5 — Contract: drop old column after all consumers are updated.**
```sql
-- Migration 004_drop_old_ref.sql
-- Deploy AFTER all application code stops referencing `ref`.
ALTER TABLE invoices DROP COLUMN ref;
```

## 4) Structured Logging with Correlation IDs

```ts
import { randomUUID } from "node:crypto";
import type { Request, Response, NextFunction } from "express";

export interface Logger {
  info(msg: string, data?: Record<string, unknown>): void;
  warn(msg: string, data?: Record<string, unknown>): void;
  error(msg: string, data?: Record<string, unknown>): void;
}

// AsyncLocalStorage keeps the correlation ID available throughout the request
// lifecycle without passing it through every function signature.
import { AsyncLocalStorage } from "node:async_hooks";

interface RequestContext {
  correlationId: string;
  method: string;
  path: string;
}

const store = new AsyncLocalStorage<RequestContext>();

export function correlationMiddleware(req: Request, _res: Response, next: NextFunction): void {
  const correlationId = (req.headers["x-correlation-id"] as string) || randomUUID();
  const ctx: RequestContext = { correlationId, method: req.method, path: req.path };

  // Set response header so callers can trace the request.
  _res.setHeader("x-correlation-id", correlationId);

  store.run(ctx, () => next());
}

export function createLogger(service: string): Logger {
  function emit(level: string, msg: string, data?: Record<string, unknown>): void {
    const ctx = store.getStore();
    const entry = {
      timestamp: new Date().toISOString(),
      level,
      service,
      correlationId: ctx?.correlationId ?? "no-context",
      method: ctx?.method,
      path: ctx?.path,
      msg,
      ...data,
    };
    process.stdout.write(JSON.stringify(entry) + "\n");
  }

  return {
    info: (msg, data) => emit("info", msg, data),
    warn: (msg, data) => emit("warn", msg, data),
    error: (msg, data) => emit("error", msg, data),
  };
}

// Usage:
// app.use(correlationMiddleware);
// const log = createLogger("order-service");
// log.info("Order created", { orderId: "abc-123", amount: 4999 });
// Output: {"timestamp":"...","level":"info","service":"order-service",
//          "correlationId":"a1b2c3","method":"POST","path":"/orders",
//          "msg":"Order created","orderId":"abc-123","amount":4999}
```

## 5) Circuit Breaker Wrapper

```ts
type AsyncFn<T> = () => Promise<T>;

interface CircuitBreakerOpts {
  failureThreshold: number;   // failures before opening circuit
  cooldownMs: number;         // time in open state before trying half-open
  onOpen?: () => void;        // callback when circuit opens
}

enum State { CLOSED, OPEN, HALF_OPEN }

export function createCircuitBreaker<T>(
  fn: AsyncFn<T>,
  opts: CircuitBreakerOpts
): AsyncFn<T> {
  let state = State.CLOSED;
  let failureCount = 0;
  let lastFailureTime = 0;

  return async function circuitBreakerCall(): Promise<T> {
    if (state === State.OPEN) {
      const elapsed = Date.now() - lastFailureTime;
      if (elapsed < opts.cooldownMs) {
        throw new Error("Circuit breaker is OPEN. Request rejected.");
      }
      state = State.HALF_OPEN;
    }

    try {
      const result = await fn();
      // Success: reset to closed.
      failureCount = 0;
      state = State.CLOSED;
      return result;
    } catch (err) {
      failureCount++;
      lastFailureTime = Date.now();

      if (failureCount >= opts.failureThreshold) {
        state = State.OPEN;
        opts.onOpen?.();
      }
      throw err;
    }
  };
}

// Usage:
// const fetchUser = createCircuitBreaker(
//   () => httpClient.get("/users/123"),
//   { failureThreshold: 5, cooldownMs: 30_000,
//     onOpen: () => metrics.increment("circuit.user-service.opened") }
// );
```

## 6) Retry with Exponential Backoff and Jitter

```ts
interface RetryOpts {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs?: number;
  shouldRetry?: (error: unknown) => boolean;  // only retry transient errors
}

export async function withRetry<T>(fn: () => Promise<T>, opts: RetryOpts): Promise<T> {
  const { maxAttempts, baseDelayMs, maxDelayMs = 30_000, shouldRetry = () => true } = opts;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err) {
      const isLastAttempt = attempt === maxAttempts;
      if (isLastAttempt || !shouldRetry(err)) throw err;

      // Exponential backoff: 200ms, 400ms, 800ms, ...
      const exponentialDelay = baseDelayMs * 2 ** (attempt - 1);
      // Jitter: randomize within [0, exponentialDelay] to prevent thundering herd.
      const jitter = Math.random() * exponentialDelay;
      const delay = Math.min(exponentialDelay + jitter, maxDelayMs);

      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
  throw new Error("unreachable");
}

// Usage:
// const data = await withRetry(() => fetch("https://api.example.com/data"), {
//   maxAttempts: 4,
//   baseDelayMs: 200,
//   shouldRetry: (err) => err instanceof Error && "status" in err && (err as any).status >= 500,
// });
```
