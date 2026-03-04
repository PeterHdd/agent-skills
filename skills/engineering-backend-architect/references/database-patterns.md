# Database Architecture Patterns

## Connection Pooling with pg

```typescript
import { Pool, PoolClient } from "pg";

const pool = new Pool({
  host: process.env.DB_HOST,
  port: 5432,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  min: 5,                        // minimum idle connections
  max: 20,                       // maximum connections in pool
  idleTimeoutMillis: 30_000,     // close idle connections after 30s
  connectionTimeoutMillis: 5_000, // fail if connection takes > 5s
});

pool.on("error", (err) => {
  console.error("Unexpected pool error:", err);
  process.exit(1);
});

// Query wrapper: acquires client, runs query, releases automatically
async function query<T = Record<string, unknown>>(
  text: string,
  params?: unknown[]
): Promise<T[]> {
  const client: PoolClient = await pool.connect();
  try {
    const result = await client.query(text, params);
    return result.rows as T[];
  } finally {
    client.release();
  }
}

// Transaction wrapper
async function withTransaction<T>(fn: (client: PoolClient) => Promise<T>): Promise<T> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}
```

## Read Replica Routing

```typescript
import { Pool } from "pg";
import { Request, Response, NextFunction } from "express";

const primary = new Pool({ host: process.env.PRIMARY_HOST, max: 20 });
const replica = new Pool({ host: process.env.REPLICA_HOST, max: 20 });

// Middleware: attach the right pool based on HTTP method
function routeDatabase(req: Request, _res: Response, next: NextFunction): void {
  const isReadOnly = req.method === "GET" || req.method === "HEAD";
  // Allow override via header for queries that must read-your-own-writes
  const forcePrimary = req.headers["x-force-primary"] === "true";
  req.app.locals.db = isReadOnly && !forcePrimary ? replica : primary;
  next();
}

// Usage in route
app.use(routeDatabase);

app.get("/api/products", async (req, res) => {
  const { rows } = await req.app.locals.db.query("SELECT * FROM products WHERE is_active = true");
  res.json({ data: rows });
});

app.post("/api/products", async (req, res) => {
  // Automatically routed to primary by middleware
  const { rows } = await req.app.locals.db.query(
    "INSERT INTO products (name, price) VALUES ($1, $2) RETURNING *",
    [req.body.name, req.body.price]
  );
  res.status(201).json({ data: rows[0] });
});
```

## Database Migration — Expand-Migrate-Contract

### Step 1: Expand — add new column (non-breaking)

```sql
-- Migration: 001_add_display_name.sql
ALTER TABLE users ADD COLUMN display_name VARCHAR(200);

-- New column is nullable, existing code continues to work
-- Deploy code that writes to BOTH full_name and display_name
```

### Step 2: Migrate — backfill data

```sql
-- Migration: 002_backfill_display_name.sql
-- Run in batches to avoid locking the table
UPDATE users
SET display_name = first_name || ' ' || last_name
WHERE display_name IS NULL
  AND id IN (
    SELECT id FROM users WHERE display_name IS NULL LIMIT 5000
  );

-- Repeat until all rows are backfilled
-- Then deploy code that reads from display_name instead of full_name
```

### Step 3: Contract — drop old columns

```sql
-- Migration: 003_drop_legacy_name_columns.sql
-- Only run after all services read from display_name
ALTER TABLE users ALTER COLUMN display_name SET NOT NULL;
ALTER TABLE users DROP COLUMN first_name;
ALTER TABLE users DROP COLUMN last_name;
```

## Hash-Based Sharding

```typescript
import { Pool } from "pg";
import crypto from "crypto";

const SHARD_COUNT = 4;

// One pool per shard
const shards: Pool[] = Array.from({ length: SHARD_COUNT }, (_, i) =>
  new Pool({ host: `shard-${i}.db.internal`, database: "app", max: 10 })
);

function resolveShard(userId: string): number {
  const hash = crypto.createHash("md5").update(userId).digest();
  // Use first 4 bytes as a 32-bit unsigned integer
  const numeric = hash.readUInt32BE(0);
  return numeric % SHARD_COUNT;
}

function getShardPool(userId: string): Pool {
  return shards[resolveShard(userId)];
}

// Query routed to the correct shard
async function getUserOrders(userId: string) {
  const pool = getShardPool(userId);
  const { rows } = await pool.query(
    "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC",
    [userId]
  );
  return rows;
}

// Cross-shard scatter-gather (use sparingly)
async function getGlobalOrderCount(): Promise<number> {
  const counts = await Promise.all(
    shards.map((pool) => pool.query("SELECT COUNT(*) AS c FROM orders"))
  );
  return counts.reduce((sum, r) => sum + parseInt(r.rows[0].c, 10), 0);
}
```

## Query Optimization — Before and After

### Before: Slow query

```sql
-- Query: find recent active orders for a user
SELECT o.id, o.total, o.created_at, p.name
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE o.user_id = 'usr_abc123'
  AND o.status = 'ACTIVE'
ORDER BY o.created_at DESC
LIMIT 20;

-- EXPLAIN ANALYZE output (before):
-- Sort  (cost=28450.12..28452.30 rows=872 width=96) (actual time=312.4..312.8 rows=20 loops=1)
--   ->  Hash Join  (cost=12500.00..28410.50 rows=872 width=96) (actual time=205.1..310.2 rows=843 loops=1)
--         ->  Seq Scan on orders o  (cost=0.00..15420.00 rows=1250 width=48) (actual time=0.03..180.5 rows=1250 loops=1)
--               Filter: ((user_id = 'usr_abc123') AND (status = 'ACTIVE'))
--               Rows Removed by Filter: 498750
-- Planning Time: 0.8 ms
-- Execution Time: 313.2 ms
```

### After: Optimized with proper indexes

```sql
-- Add a composite covering index
CREATE INDEX idx_orders_user_status_created
  ON orders (user_id, status, created_at DESC)
  INCLUDE (total);

-- Same query now uses the index
-- EXPLAIN ANALYZE output (after):
-- Limit  (cost=0.56..45.20 rows=20 width=96) (actual time=0.08..0.35 rows=20 loops=1)
--   ->  Nested Loop  (cost=0.56..1950.30 rows=872 width=96) (actual time=0.07..0.33 rows=20 loops=1)
--         ->  Index Scan using idx_orders_user_status_created on orders o
--               (cost=0.42..85.60 rows=872 width=48) (actual time=0.04..0.06 rows=20 loops=1)
--               Index Cond: ((user_id = 'usr_abc123') AND (status = 'ACTIVE'))
-- Planning Time: 0.5 ms
-- Execution Time: 0.6 ms
--
-- Improvement: 313ms → 0.6ms (522x faster)
```

## Cache-Aside with Redis

```typescript
import Redis from "ioredis";
import { Pool } from "pg";

const redis = new Redis();
const db = new Pool();

interface User {
  id: string;
  email: string;
  display_name: string;
}

async function getUserById(userId: string): Promise<User | null> {
  const cacheKey = `user:${userId}`;

  // 1. Try cache first
  const cached = await redis.get(cacheKey);
  if (cached) {
    return JSON.parse(cached) as User;
  }

  // 2. Cache miss — fetch from database
  const { rows } = await db.query<User>(
    "SELECT id, email, display_name FROM users WHERE id = $1",
    [userId]
  );
  if (rows.length === 0) return null;

  // 3. Populate cache with TTL (5 minutes)
  await redis.set(cacheKey, JSON.stringify(rows[0]), "EX", 300);
  return rows[0];
}

// Invalidate on write — called after any user update
async function updateUser(userId: string, data: Partial<User>): Promise<User> {
  const setClauses = Object.keys(data)
    .map((key, i) => `${key} = $${i + 2}`)
    .join(", ");
  const { rows } = await db.query<User>(
    `UPDATE users SET ${setClauses}, updated_at = NOW() WHERE id = $1 RETURNING *`,
    [userId, ...Object.values(data)]
  );

  // Delete cache entry so next read fetches fresh data
  await redis.del(`user:${userId}`);
  return rows[0];
}
```
