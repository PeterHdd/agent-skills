# Distributed System Patterns

## Circuit Breaker

```typescript
import { EventEmitter } from "events";

type State = "CLOSED" | "OPEN" | "HALF_OPEN";

interface CircuitBreakerOptions {
  failureThreshold: number;   // failures before opening
  recoveryTimeout: number;    // ms before trying half-open
  successThreshold: number;   // successes in half-open to close
}

class CircuitBreaker extends EventEmitter {
  private state: State = "CLOSED";
  private failureCount = 0;
  private successCount = 0;
  private nextAttempt = 0;

  constructor(
    private readonly fn: (...args: unknown[]) => Promise<unknown>,
    private readonly opts: CircuitBreakerOptions
  ) {
    super();
  }

  async call(...args: unknown[]): Promise<unknown> {
    if (this.state === "OPEN") {
      if (Date.now() < this.nextAttempt) {
        throw new Error("Circuit is OPEN — request rejected");
      }
      this.transition("HALF_OPEN");
    }

    try {
      const result = await this.fn(...args);
      this.onSuccess();
      return result;
    } catch (err) {
      this.onFailure();
      throw err;
    }
  }

  private onSuccess(): void {
    if (this.state === "HALF_OPEN") {
      this.successCount++;
      if (this.successCount >= this.opts.successThreshold) {
        this.transition("CLOSED");
      }
    }
    if (this.state === "CLOSED") {
      this.failureCount = 0;
    }
  }

  private onFailure(): void {
    this.failureCount++;
    if (this.state === "HALF_OPEN" || this.failureCount >= this.opts.failureThreshold) {
      this.transition("OPEN");
    }
  }

  private transition(newState: State): void {
    if (this.state === newState) return;
    const prev = this.state;
    this.state = newState;
    this.failureCount = 0;
    this.successCount = 0;
    if (newState === "OPEN") {
      this.nextAttempt = Date.now() + this.opts.recoveryTimeout;
    }
    this.emit("stateChange", { from: prev, to: newState });
  }
}

// Usage
const breaker = new CircuitBreaker(fetchFromPaymentService, {
  failureThreshold: 5,
  recoveryTimeout: 30_000,
  successThreshold: 3,
});
breaker.on("stateChange", ({ from, to }) => console.log(`Circuit: ${from} → ${to}`));
```

## Saga Pattern — Orchestrated Order Flow

```typescript
interface SagaStep<T> {
  name: string;
  execute: (ctx: T) => Promise<T>;
  compensate: (ctx: T) => Promise<T>;
}

class SagaOrchestrator<T> {
  private steps: SagaStep<T>[] = [];

  addStep(step: SagaStep<T>): this {
    this.steps.push(step);
    return this;
  }

  async run(initialCtx: T): Promise<T> {
    const completed: SagaStep<T>[] = [];
    let ctx = initialCtx;

    for (const step of this.steps) {
      try {
        ctx = await step.execute(ctx);
        completed.push(step);
      } catch (err) {
        console.error(`Saga failed at "${step.name}":`, err);
        // Compensate in reverse order
        for (const done of completed.reverse()) {
          try {
            ctx = await done.compensate(ctx);
          } catch (compErr) {
            console.error(`Compensation failed at "${done.name}":`, compErr);
            // Log to dead-letter for manual resolution
          }
        }
        throw new Error(`Saga rolled back at step "${step.name}"`);
      }
    }
    return ctx;
  }
}

// E-commerce order saga
interface OrderCtx {
  orderId: string;
  userId: string;
  items: { sku: string; qty: number }[];
  paymentIntentId?: string;
}

const orderSaga = new SagaOrchestrator<OrderCtx>()
  .addStep({
    name: "createOrder",
    execute: async (ctx) => { await db.orders.insert({ id: ctx.orderId, status: "PENDING" }); return ctx; },
    compensate: async (ctx) => { await db.orders.update(ctx.orderId, { status: "CANCELLED" }); return ctx; },
  })
  .addStep({
    name: "reserveInventory",
    execute: async (ctx) => { await inventoryService.reserve(ctx.items); return ctx; },
    compensate: async (ctx) => { await inventoryService.release(ctx.items); return ctx; },
  })
  .addStep({
    name: "chargePayment",
    execute: async (ctx) => {
      const intent = await paymentService.charge(ctx.userId, ctx.items);
      return { ...ctx, paymentIntentId: intent.id };
    },
    compensate: async (ctx) => { await paymentService.refund(ctx.paymentIntentId!); return ctx; },
  })
  .addStep({
    name: "confirmOrder",
    execute: async (ctx) => { await db.orders.update(ctx.orderId, { status: "CONFIRMED" }); return ctx; },
    compensate: async (ctx) => { await db.orders.update(ctx.orderId, { status: "CANCELLED" }); return ctx; },
  });

// await orderSaga.run({ orderId: "ord_123", userId: "usr_456", items: [...] });
```

## Event-Driven Consumer with Idempotency

```sql
-- Processed events table for deduplication
CREATE TABLE processed_events (
    idempotency_key VARCHAR(255) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_processed_events_type ON processed_events(event_type, processed_at);
```

```typescript
import { Pool } from "pg";

interface IncomingEvent {
  idempotencyKey: string;
  type: string;
  payload: Record<string, unknown>;
}

async function handleEvent(pool: Pool, event: IncomingEvent): Promise<void> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    // Deduplication check — uses PK constraint as a lock
    const { rowCount } = await client.query(
      `INSERT INTO processed_events (idempotency_key, event_type)
       VALUES ($1, $2) ON CONFLICT (idempotency_key) DO NOTHING`,
      [event.idempotencyKey, event.type]
    );

    if (rowCount === 0) {
      console.log(`Duplicate event ${event.idempotencyKey} — skipping`);
      await client.query("ROLLBACK");
      return;
    }

    // Process the event within the same transaction
    switch (event.type) {
      case "order.placed":
        await client.query(
          `INSERT INTO orders (id, user_id, total) VALUES ($1, $2, $3)`,
          [event.payload.orderId, event.payload.userId, event.payload.total]
        );
        break;
      // ... other event types
    }

    await client.query("COMMIT");
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}
```

## Distributed Lock with Redis

```typescript
import Redis from "ioredis";
import { randomUUID } from "crypto";

const redis = new Redis();

async function acquireLock(key: string, ttlMs: number): Promise<string | null> {
  const token = randomUUID();
  const acquired = await redis.set(key, token, "PX", ttlMs, "NX");
  return acquired === "OK" ? token : null;
}

async function releaseLock(key: string, token: string): Promise<boolean> {
  // Lua script: only delete if the value matches our token
  const script = `
    if redis.call("get", KEYS[1]) == ARGV[1] then
      return redis.call("del", KEYS[1])
    else
      return 0
    end
  `;
  const result = await redis.eval(script, 1, key, token);
  return result === 1;
}

// Usage
async function withLock<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const token = await acquireLock(`lock:${key}`, ttlMs);
  if (!token) throw new Error(`Could not acquire lock: ${key}`);
  try {
    return await fn();
  } finally {
    await releaseLock(`lock:${key}`, token);
  }
}
```

## Outbox Pattern — Transactional Event Publishing

```sql
-- Outbox table: events written in the same transaction as business data
CREATE TABLE outbox (
    id BIGSERIAL PRIMARY KEY,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE NULL
);
CREATE INDEX idx_outbox_unpublished ON outbox(created_at) WHERE published_at IS NULL;
```

```typescript
import { Pool } from "pg";

// Write business data + outbox event in a single transaction
async function placeOrder(pool: Pool, order: { id: string; userId: string; total: number }) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query(
      `INSERT INTO orders (id, user_id, total, status) VALUES ($1, $2, $3, 'CREATED')`,
      [order.id, order.userId, order.total]
    );
    await client.query(
      `INSERT INTO outbox (aggregate_type, aggregate_id, event_type, payload)
       VALUES ('Order', $1, 'order.created', $2)`,
      [order.id, JSON.stringify({ orderId: order.id, userId: order.userId, total: order.total })]
    );
    await client.query("COMMIT");
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

// Polling publisher — runs on an interval (e.g., every 500ms)
async function publishOutboxEvents(pool: Pool, publish: (event: Record<string, unknown>) => Promise<void>) {
  const { rows } = await pool.query(
    `SELECT id, aggregate_type, aggregate_id, event_type, payload
     FROM outbox WHERE published_at IS NULL ORDER BY created_at LIMIT 100`
  );
  for (const row of rows) {
    await publish({
      aggregateType: row.aggregate_type,
      aggregateId: row.aggregate_id,
      type: row.event_type,
      payload: row.payload,
    });
    await pool.query(`UPDATE outbox SET published_at = NOW() WHERE id = $1`, [row.id]);
  }
}

// Start the poller
setInterval(() => publishOutboxEvents(pool, messageBroker.publish), 500);
```
