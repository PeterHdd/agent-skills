# Scaling & Data Patterns

## 1) Consistent Hashing with Virtual Nodes (TypeScript)

```typescript
import { createHash } from "crypto";

class ConsistentHashRing<T> {
  private ring: Map<number, T> = new Map();
  private sortedKeys: number[] = [];

  constructor(
    private nodes: T[],
    private virtualNodesPerNode: number = 150
  ) {
    for (const node of nodes) this.addNode(node);
  }

  private hash(key: string): number {
    const h = createHash("md5").update(key).digest();
    return h.readUInt32BE(0);
  }

  addNode(node: T): void {
    for (let i = 0; i < this.virtualNodesPerNode; i++) {
      const virtualKey = this.hash(`${node}:vn${i}`);
      this.ring.set(virtualKey, node);
      this.sortedKeys.push(virtualKey);
    }
    this.sortedKeys.sort((a, b) => a - b);
  }

  removeNode(node: T): void {
    for (let i = 0; i < this.virtualNodesPerNode; i++) {
      const virtualKey = this.hash(`${node}:vn${i}`);
      this.ring.delete(virtualKey);
    }
    this.sortedKeys = this.sortedKeys.filter((k) => this.ring.has(k));
  }

  getNode(key: string): T {
    if (this.sortedKeys.length === 0) throw new Error("Empty ring");
    const h = this.hash(key);
    // Binary search for first key >= h
    let lo = 0, hi = this.sortedKeys.length;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (this.sortedKeys[mid] < h) lo = mid + 1;
      else hi = mid;
    }
    // Wrap around to first node if past the end
    const idx = lo === this.sortedKeys.length ? 0 : lo;
    return this.ring.get(this.sortedKeys[idx])!;
  }
}

// Usage: const ring = new ConsistentHashRing(["cache-1", "cache-2", "cache-3"]);
//        const node = ring.getNode("user:12345"); // → "cache-2"
```

## 2) Database Sharding

### Comparison: Range-Based vs Hash-Based

| Aspect | Range-Based | Hash-Based |
|---|---|---|
| Key distribution | Sequential ranges (e.g., user_id 1-1M → shard 1) | `hash(key) % shard_count` |
| Data distribution | Uneven (hot ranges for recent data) | Even (uniform hash distribution) |
| Range queries | Efficient (single shard for contiguous ranges) | Expensive (scatter-gather across all shards) |
| Adding shards | Split a range; only move data from one shard | Rehash required; use consistent hashing to minimize movement |
| Hotspot risk | High (new users cluster on latest shard) | Low (hashing distributes evenly) |
| Best for | Time-series data, sequential access patterns | User data, session stores, key-value lookups |

### Hash-Based Shard Router (TypeScript)
```typescript
import { createHash } from "crypto";
import { Pool } from "pg";

class ShardRouter {
  private pools: Pool[];

  constructor(connectionStrings: string[]) {
    this.pools = connectionStrings.map(
      (cs) => new Pool({ connectionString: cs, max: 20 })
    );
  }

  get shardCount(): number {
    return this.pools.length;
  }

  private shardFor(key: string): number {
    const hash = createHash("sha256").update(key).digest();
    return hash.readUInt32BE(0) % this.shardCount;
  }

  getPool(shardKey: string): Pool {
    return this.pools[this.shardFor(shardKey)];
  }

  async query(shardKey: string, sql: string, params: unknown[]) {
    return this.getPool(shardKey).query(sql, params);
  }

  /** Scatter-gather: run query on all shards, merge results */
  async queryAll(sql: string, params: unknown[]) {
    const results = await Promise.all(
      this.pools.map((pool) => pool.query(sql, params))
    );
    return results.flatMap((r) => r.rows);
  }
}

// Usage:
// const router = new ShardRouter(["postgres://shard0/db", "postgres://shard1/db"]);
// await router.query("user:abc", "SELECT * FROM users WHERE id = $1", ["abc"]);
```

## 3) CQRS Pattern: Separate Read/Write Models (TypeScript)

### Write Side (PostgreSQL, normalized)
```typescript
import { Pool } from "pg";
import { EventEmitter } from "events";

interface OrderEvent {
  type: "OrderCreated" | "OrderShipped" | "OrderCancelled";
  orderId: string;
  payload: Record<string, unknown>;
  timestamp: Date;
}

const db = new Pool({ connectionString: process.env.WRITE_DB_URL });
const eventBus = new EventEmitter();

async function createOrder(order: {
  id: string; userId: string; items: { sku: string; qty: number; price: number }[];
}): Promise<void> {
  const client = await db.connect();
  try {
    await client.query("BEGIN");
    await client.query(
      "INSERT INTO orders (id, user_id, status, created_at) VALUES ($1, $2, 'pending', now())",
      [order.id, order.userId]
    );
    for (const item of order.items) {
      await client.query(
        "INSERT INTO order_items (order_id, sku, quantity, unit_price) VALUES ($1, $2, $3, $4)",
        [order.id, item.sku, item.qty, item.price]
      );
    }
    // Persist event to outbox table (transactional outbox pattern)
    const event: OrderEvent = {
      type: "OrderCreated",
      orderId: order.id,
      payload: { userId: order.userId, items: order.items },
      timestamp: new Date(),
    };
    await client.query(
      "INSERT INTO event_outbox (event_type, aggregate_id, payload) VALUES ($1, $2, $3)",
      [event.type, event.orderId, JSON.stringify(event.payload)]
    );
    await client.query("COMMIT");
    eventBus.emit("event", event);
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}
```

### Event Publisher (polls outbox, publishes to Kafka)
```typescript
import { Kafka } from "kafkajs";

const kafka = new Kafka({ brokers: [process.env.KAFKA_BROKER!] });
const producer = kafka.producer();

async function publishOutboxEvents(): Promise<void> {
  const result = await db.query(
    "SELECT id, event_type, aggregate_id, payload FROM event_outbox WHERE published = false ORDER BY id LIMIT 100"
  );
  for (const row of result.rows) {
    await producer.send({
      topic: "order-events",
      messages: [{ key: row.aggregate_id, value: JSON.stringify(row) }],
    });
    await db.query("UPDATE event_outbox SET published = true WHERE id = $1", [row.id]);
  }
}

// Run every 500ms: setInterval(publishOutboxEvents, 500);
```

### Read Side (Elasticsearch, denormalized)
```typescript
import { Client } from "@elastic/elasticsearch";

const es = new Client({ node: process.env.ELASTICSEARCH_URL });

async function handleOrderCreated(event: OrderEvent): Promise<void> {
  const { userId, items } = event.payload as {
    userId: string; items: { sku: string; qty: number; price: number }[];
  };
  const total = items.reduce((sum, i) => sum + i.qty * i.price, 0);
  await es.index({
    index: "orders",
    id: event.orderId,
    document: {
      orderId: event.orderId,
      userId,
      status: "pending",
      items,
      totalAmount: total,
      itemCount: items.length,
      createdAt: event.timestamp,
    },
  });
}

// Consumer subscribes to "order-events" Kafka topic and calls handleOrderCreated
```

## 4) Rate Limiting Algorithms Compared

| Algorithm | How It Works | Pros | Cons | Best For |
|---|---|---|---|---|
| Fixed window | Count requests in fixed time windows (e.g., per minute) | Simple; low memory (one counter per window) | Burst at window boundaries (2x allowed rate) | Simple APIs; non-critical rate limits |
| Sliding window log | Store timestamp of each request; count within trailing window | Precise; no boundary burst | High memory (stores every timestamp) | Low-volume, high-accuracy needs |
| Sliding window counter | Weighted average of current + previous fixed window | Near-precise; low memory (two counters) | Slight inaccuracy at boundaries | Production APIs (best balance) |
| Token bucket | Tokens added at fixed rate; request consumes a token | Allows controlled bursts; smooth rate | Slightly more complex state | APIs needing burst tolerance |

### Sliding Window Rate Limiter with Redis Sorted Sets (TypeScript)
```typescript
import Redis from "ioredis";

const redis = new Redis({ host: "cache.internal" });

async function isAllowed(
  clientId: string,
  windowMs: number = 60_000,
  maxRequests: number = 100
): Promise<boolean> {
  const key = `ratelimit:${clientId}`;
  const now = Date.now();
  const windowStart = now - windowMs;

  const pipeline = redis.pipeline();
  // Remove entries outside the window
  pipeline.zremrangebyscore(key, 0, windowStart);
  // Count entries in the current window
  pipeline.zcard(key);
  // Add the current request
  pipeline.zadd(key, now.toString(), `${now}:${Math.random()}`);
  // Set expiry on the key to auto-cleanup
  pipeline.expire(key, Math.ceil(windowMs / 1000));

  const results = await pipeline.exec();
  const currentCount = results![1][1] as number;

  if (currentCount >= maxRequests) {
    // Remove the entry we just added (request is rejected)
    await redis.zremrangebyscore(key, now, now);
    return false;
  }
  return true;
}

// Usage in Express middleware:
// if (!(await isAllowed(req.ip))) return res.status(429).json({ error: "Rate limit exceeded" });
```

## 5) Back-Pressure with Bounded Queue (TypeScript)

```typescript
class BoundedQueue<T> {
  private queue: T[] = [];
  private processing = 0;
  private waiters: Array<(item: T) => void> = [];

  constructor(
    private maxSize: number,
    private concurrency: number,
    private handler: (item: T) => Promise<void>
  ) {}

  /** Enqueue an item. Returns false if queue is full (back-pressure signal). */
  enqueue(item: T): boolean {
    if (this.queue.length >= this.maxSize) {
      return false; // Back-pressure: caller must retry or drop
    }
    this.queue.push(item);
    this.drain();
    return true;
  }

  private async drain(): Promise<void> {
    while (this.processing < this.concurrency && this.queue.length > 0) {
      const item = this.queue.shift()!;
      this.processing++;
      this.handler(item)
        .catch((err) => console.error("Handler error:", err))
        .finally(() => {
          this.processing--;
          this.drain();
        });
    }
  }

  get pending(): number { return this.queue.length; }
  get active(): number { return this.processing; }
}

// Usage:
// const queue = new BoundedQueue<Job>(1000, 10, async (job) => { await processJob(job); });
// app.post("/jobs", (req, res) => {
//   if (!queue.enqueue(req.body)) return res.status(503).json({ error: "Queue full, retry later" });
//   res.status(202).json({ status: "accepted" });
// });
```

## 6) AWS Cost Estimation: 10M Requests/Day System

### Assumptions
- 10M requests/day = ~116 req/sec average, ~350 req/sec peak
- 80% reads, 20% writes
- Average response size: 2 KB
- 500 GB database, 50 GB cache, 1 TB object storage

### Monthly Cost Breakdown

| Service | Configuration | Monthly Cost |
|---|---|---|
| **Compute (ECS Fargate)** | 4 tasks x 2 vCPU / 4 GB RAM, running 24/7 | ~$460 |
| **Load Balancer (ALB)** | 1 ALB + 10M requests/day (~300M/month) | ~$85 |
| **Database (RDS PostgreSQL)** | db.r6g.xlarge Multi-AZ (4 vCPU, 32 GB), 500 GB gp3 storage | ~$830 |
| **Cache (ElastiCache Redis)** | cache.r6g.large (2 nodes for replication, 13 GB each) | ~$390 |
| **Object Storage (S3)** | 1 TB Standard; 5M PUT + 50M GET requests/month | ~$30 |
| **CDN (CloudFront)** | 2 TB transfer out/month; 300M requests | ~$230 |
| **Messaging (SQS)** | 50M messages/month (standard queue) | ~$20 |
| **Monitoring (CloudWatch)** | 20 custom metrics, 10 dashboards, 5 GB logs/month | ~$45 |
| **Data Transfer** | 3 TB out/month (inter-AZ + internet) | ~$280 |
| **Total** | | **~$2,370/month** |

### Scaling Cost Methodology
```
At 10x scale (100M requests/day):
  Compute:   Scale horizontally → 4x tasks = ~$1,840 (linear)
  Database:  Upgrade instance + read replicas → ~$2,500 (sub-linear with read replicas)
  Cache:     Larger cluster (6 nodes) → ~$1,170 (linear with data size)
  CDN:       20 TB transfer → ~$1,700 (volume discount)
  Total at 10x: ~$9,000-$11,000/month

Key insight: database and compute are the largest cost drivers.
Optimization levers:
  1. Reserved instances (RDS + ElastiCache) → 30-40% savings
  2. Spot/Fargate Spot for non-critical workloads → 50-70% compute savings
  3. S3 Intelligent Tiering for infrequently accessed objects
  4. Cache hit ratio improvement reduces DB load (cheaper instance tier)
```
