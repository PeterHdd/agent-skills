# Performance Profiling & Investigation

## 1) Node.js Profiling Workflows

### Clinic.js Flame Graph — Finding CPU Hot Paths

```bash
# Install once
npm install -g clinic

# Generate a flame graph while running load against the server
clinic flame -- node dist/server.js &
SERVER_PID=$!
# Hit it with realistic load (autocannon, k6, or wrk)
npx autocannon -c 50 -d 20 http://localhost:3000/api/orders
kill $SERVER_PID
# Opens an interactive flame graph in the browser automatically.
```

**Reading the flame graph:**
- Width = total time in that function (wider = more CPU).
- Look for wide plateaus that are NOT Node.js internals — those are your hot paths.
- Common findings: JSON.parse on large payloads, regex backtracking, synchronous crypto.

### Chrome DevTools Profiling via --inspect

```bash
# Start the app with the inspector
node --inspect dist/server.js
# Connect: open chrome://inspect in Chrome, click "inspect" on the target.
```

**CPU profile workflow:**
1. Open the "Performance" tab in DevTools.
2. Click "Record", send 10-20 requests to the slow endpoint.
3. Stop recording. Expand the main thread flame chart.
4. Sort by "Self Time" to find functions consuming the most CPU directly.

**Heap snapshot workflow:**
1. Open the "Memory" tab. Select "Heap snapshot".
2. Take snapshot 1 (baseline after startup).
3. Send 100 requests to the suspected leaky endpoint.
4. Take snapshot 2.
5. Use the "Comparison" view between snapshot 1 and 2.
6. Sort by "# Delta" — large positive deltas indicate objects being allocated but never freed.

### Event Loop Lag Detection

```ts
import { monitorEventLoopDelay } from "node:perf_hooks";

const histogram = monitorEventLoopDelay({ resolution: 20 });
histogram.enable();

// Sample every 10 seconds and report
setInterval(() => {
  const p99 = histogram.percentile(99) / 1e6; // nanoseconds to ms
  const max = histogram.max / 1e6;
  if (p99 > 100) {
    logger.warn("Event loop lag high", { p99Ms: p99.toFixed(1), maxMs: max.toFixed(1) });
    metrics.gauge("eventloop.lag_p99_ms", p99);
  }
  histogram.reset();
}, 10_000);

// Thresholds:
// p99 < 20ms  = healthy
// p99 20-100ms = investigate (synchronous work or GC pressure)
// p99 > 100ms = critical (blocking the event loop, users will notice)
```

---

## 2) Database Performance Investigation

### EXPLAIN ANALYZE Workflow

```sql
-- Step 1: Get the actual execution plan (not just estimated)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.id, o.total, c.email
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.created_at > NOW() - INTERVAL '7 days'
  AND o.status = 'pending';

-- What to look for in the output:
-- "Seq Scan" on a large table   -> needs an index
-- "Rows Removed by Filter: 890000" -> index not selective enough
-- "Sort Method: external merge"  -> not enough work_mem
-- "Loops: 4500"                  -> N+1 pattern in a nested loop join
-- "Buffers: shared read=12400"   -> cache miss, data not in shared_buffers
```

### Finding Top Slow Queries with pg_stat_statements

```sql
-- Enable the extension (one-time, requires superuser)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 queries by total execution time
SELECT
  round(total_exec_time::numeric, 1) AS total_ms,
  calls,
  round(mean_exec_time::numeric, 1) AS avg_ms,
  round((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 1) AS pct,
  substr(query, 1, 120) AS query_preview
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- Top 10 queries by average execution time (finds individually slow queries)
SELECT
  round(mean_exec_time::numeric, 1) AS avg_ms,
  calls,
  round(stddev_exec_time::numeric, 1) AS stddev_ms,
  substr(query, 1, 120) AS query_preview
FROM pg_stat_statements
WHERE calls > 10  -- filter out one-off queries
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Reset stats after optimization to get clean measurements
-- SELECT pg_stat_statements_reset();
```

### Index Recommendation Checklist

```
If you see this...                  Add this index...
─────────────────────────────────── ─────────────────────────────────────
Seq Scan + Filter on col WHERE      CREATE INDEX idx_tbl_col ON tbl(col);
  rows_removed > 1000

JOIN with Seq Scan on FK column     CREATE INDEX idx_tbl_fk ON tbl(fk_col);

ORDER BY col with external sort     CREATE INDEX idx_tbl_col ON tbl(col);

WHERE a = X AND b > Y               CREATE INDEX idx_tbl_a_b ON tbl(a, b);
                                     (equality columns first, then range)

WHERE a = X (returns 5+ columns)    CREATE INDEX idx_tbl_a_covering
  but only needs 2                    ON tbl(a) INCLUDE (col1, col2);

Partial scan on enum/status col     CREATE INDEX idx_tbl_status_active
                                      ON tbl(status) WHERE status = 'active';
```

### N+1 Query Detection

```ts
// Middleware that counts queries per request and warns on N+1 patterns
let queryCount = 0;
const originalQuery = pool.query.bind(pool);

pool.query = async (...args: any[]) => {
  queryCount++;
  return originalQuery(...args);
};

app.use((req, res, next) => {
  queryCount = 0;
  const originalEnd = res.end.bind(res);
  res.end = (...args: any[]) => {
    if (queryCount > 10) {
      logger.warn("Potential N+1 detected", {
        path: req.path,
        method: req.method,
        queryCount,
      });
    }
    metrics.histogram("http.queries_per_request", queryCount, { path: req.route?.path });
    return originalEnd(...args);
  };
  next();
});

// Fix: replace N+1 with a single query using IN() or JOIN
// Before (N+1): orders.forEach(o => db.query("SELECT * FROM items WHERE order_id=$1", [o.id]))
// After (1 query): db.query("SELECT * FROM items WHERE order_id = ANY($1)", [orderIds])
```

---

## 3) Memory Leak Investigation

### Three-Snapshot Heap Diff Technique

```
Step 1: Start the app. Wait for initialization to complete.
        Take HEAP SNAPSHOT #1 (baseline).

Step 2: Trigger the suspected leaky operation 500 times.
        (e.g., send 500 requests to the leaky endpoint)
        Force GC: global.gc() (run node with --expose-gc)
        Take HEAP SNAPSHOT #2.

Step 3: Trigger the same operation 500 more times.
        Force GC again.
        Take HEAP SNAPSHOT #3.

Analysis:
  - Compare snapshot #2 vs #1: "Objects allocated between 1 and 2"
  - Compare snapshot #3 vs #2: "Objects allocated between 2 and 3"
  - If the same object type grows by the SAME amount in both diffs,
    that object is leaking. If it grew in #2 but not #3, it was just
    warm-up / caching (not a leak).
```

**Programmatic heap snapshots for production:**

```ts
import v8 from "node:v8";
import fs from "node:fs";

// Trigger via admin endpoint (auth-protected!)
app.post("/admin/heap-snapshot", authAdmin, (req, res) => {
  const filename = `/tmp/heap-${Date.now()}.heapsnapshot`;
  const snapshotStream = v8.writeHeapSnapshot(filename);
  logger.info("Heap snapshot written", { filename: snapshotStream });
  res.json({ filename: snapshotStream });
  // Download and open in Chrome DevTools Memory tab
});
```

### Common Leak Patterns and Fixes

```ts
// LEAK: Event listeners never removed
class Processor {
  constructor(private emitter: EventEmitter) {
    // BUG: listener accumulates on every new Processor instance
    this.emitter.on("data", this.handle.bind(this));
  }
  handle(data: unknown) { /* ... */ }
}
// FIX: Remove listener in cleanup, or use AbortSignal
class ProcessorFixed {
  private controller = new AbortController();
  constructor(private emitter: EventEmitter) {
    this.emitter.on("data", this.handle.bind(this));
  }
  handle(data: unknown) { /* ... */ }
  destroy() {
    this.emitter.removeAllListeners("data"); // or track specific refs
    this.controller.abort();
  }
}

// LEAK: Closures capturing large objects
function processItems(hugeArray: Item[]) {
  return hugeArray.map(item => {
    // BUG: each closure captures `hugeArray` via the enclosing scope
    return () => console.log(item.name);
  });
}
// FIX: Extract only what the closure needs
function processItemsFixed(hugeArray: Item[]) {
  return hugeArray.map(item => {
    const name = item.name; // only capture the needed value
    return () => console.log(name);
  });
}

// LEAK: Unbounded caches / maps
const cache = new Map<string, Result>();
function getCached(key: string): Result {
  // BUG: map grows forever
  if (!cache.has(key)) cache.set(key, expensiveCompute(key));
  return cache.get(key)!;
}
// FIX: Use an LRU cache with max size
import { LRUCache } from "lru-cache";
const lru = new LRUCache<string, Result>({ max: 5000, ttl: 1000 * 60 * 10 });
```

### WeakRef for Cache-Friendly Patterns

```ts
// Use WeakRef when you want to cache objects that can be GC'd when no longer referenced
const weakCache = new Map<string, WeakRef<ExpensiveObject>>();
const registry = new FinalizationRegistry<string>((key) => {
  // Clean up the map entry when the object is GC'd
  const ref = weakCache.get(key);
  if (ref && ref.deref() === undefined) weakCache.delete(key);
});

function getOrCreate(key: string): ExpensiveObject {
  const ref = weakCache.get(key);
  const cached = ref?.deref();
  if (cached) return cached;

  const obj = new ExpensiveObject(key);
  weakCache.set(key, new WeakRef(obj));
  registry.register(obj, key);
  return obj;
}
```

---

## 4) CPU Profiling — Identifying Hot Paths

### Worker Thread Offloading for CPU-Bound Work

```ts
// worker-pool.ts — Offload CPU-intensive tasks to prevent event loop blocking
import { Worker } from "node:worker_threads";
import os from "node:os";

interface Task<T> {
  resolve: (value: T) => void;
  reject: (err: Error) => void;
  data: unknown;
}

export class WorkerPool {
  private workers: Worker[] = [];
  private queue: Task<unknown>[] = [];
  private freeWorkers: Worker[] = [];

  constructor(workerScript: string, poolSize = os.cpus().length - 1) {
    for (let i = 0; i < poolSize; i++) {
      const worker = new Worker(workerScript);
      worker.on("message", (result) => {
        const task = (worker as any).__currentTask as Task<unknown>;
        task.resolve(result);
        this.freeWorkers.push(worker);
        this.runNext();
      });
      worker.on("error", (err) => {
        const task = (worker as any).__currentTask as Task<unknown>;
        task.reject(err);
        this.freeWorkers.push(worker);
        this.runNext();
      });
      this.workers.push(worker);
      this.freeWorkers.push(worker);
    }
  }

  run<T>(data: unknown): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push({ resolve, reject, data });
      this.runNext();
    });
  }

  private runNext() {
    if (this.queue.length === 0 || this.freeWorkers.length === 0) return;
    const worker = this.freeWorkers.pop()!;
    const task = this.queue.shift()!;
    (worker as any).__currentTask = task;
    worker.postMessage(task.data);
  }
}

// Usage: offload PDF generation, image processing, CSV parsing, etc.
// const pool = new WorkerPool("./workers/pdf-generator.js");
// const pdf = await pool.run<Buffer>({ template: "invoice", data: orderData });
```

### Async Hooks Overhead — Measuring and Minimizing

```ts
// Async hooks add ~5-15% overhead. Use them selectively.
// Only enable when needed (e.g., for correlation IDs), and prefer
// AsyncLocalStorage (which is optimized) over raw createHook.

// AVOID in hot paths:
import { createHook } from "node:async_hooks";
// This fires on EVERY async operation — expensive at scale.
const hook = createHook({
  init(asyncId, type) { /* fires thousands of times per second */ },
});

// PREFER AsyncLocalStorage — same capability, optimized by V8:
import { AsyncLocalStorage } from "node:async_hooks";
const als = new AsyncLocalStorage<{ traceId: string }>();
// Only 1-3% overhead, propagates context automatically.
```

---

## 5) Worked Example: "API Endpoint Is Slow"

### Scenario
`GET /api/dashboard/summary` takes 4.2 seconds (p95). SLO is 500ms.

### Step 1: Measure Where Time Goes

```ts
// Add timing middleware to decompose latency
app.get("/api/dashboard/summary", async (req, res) => {
  const t = { start: Date.now(), db: 0, cache: 0, compute: 0 };

  const t1 = Date.now();
  const orders = await db.query("SELECT ... FROM orders WHERE ...");
  t.db += Date.now() - t1;

  const t2 = Date.now();
  const cached = await redis.get("dashboard:stats");
  t.cache += Date.now() - t2;

  const t3 = Date.now();
  const summary = computeSummary(orders.rows, cached);
  t.compute += Date.now() - t3;

  res.setHeader("Server-Timing", `db;dur=${t.db}, cache;dur=${t.cache}, compute;dur=${t.compute}`);
  res.json(summary);
});
```

**Result:** `Server-Timing: db;dur=3800, cache;dur=15, compute;dur=320`
The database is the bottleneck (3.8s of 4.2s).

### Step 2: Identify the Slow Query

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.id, o.status, o.total, c.name, COUNT(i.id) as item_count
FROM orders o
JOIN customers c ON c.id = o.customer_id
JOIN order_items i ON i.order_id = o.id
WHERE o.created_at > NOW() - INTERVAL '30 days'
GROUP BY o.id, c.name;

-- Result shows:
-- Hash Join (actual time=3412ms)
--   -> Seq Scan on order_items (actual time=2900ms, rows=2400000)
--   -> Hash (actual time=180ms)
--        -> Index Scan on orders (actual time=150ms, rows=45000)
```

**Root cause:** Sequential scan on `order_items` (2.4M rows) with no index on `order_id`.

### Step 3: Fix and Verify

```sql
-- Add the missing index
CREATE INDEX CONCURRENTLY idx_order_items_order_id ON order_items(order_id);

-- Re-run EXPLAIN ANALYZE
-- Result now shows:
-- Nested Loop (actual time=85ms)
--   -> Index Scan on orders (actual time=12ms, rows=45000)
--   -> Index Scan on order_items using idx_order_items_order_id (actual time=0.02ms per loop)
```

**After fix:** Query drops from 3.8s to 85ms. Endpoint p95 drops to 420ms (within SLO).

### Step 4: Prevent Recurrence

```yaml
# Add to CI pipeline: query plan check for new/modified queries
- name: Check query plans
  run: |
    for f in $(git diff --name-only origin/main -- 'src/**/*.sql' 'src/**/*.ts'); do
      # Extract SQL from migration files and check for Seq Scans on large tables
      node scripts/check-query-plans.js "$f"
    done
```

```ts
// scripts/check-query-plans.ts — CI guard
// Runs EXPLAIN on new queries against a prod-sized test DB
// Flags any query with Seq Scan on tables > 100k rows
import { extractQueries } from "./sql-extractor";
import { Pool } from "pg";

const pool = new Pool({ connectionString: process.env.TEST_DB_URL });

for (const query of extractQueries(process.argv[2])) {
  const plan = await pool.query(`EXPLAIN (FORMAT JSON) ${query}`);
  const nodes = flattenPlanNodes(plan.rows[0]["QUERY PLAN"]);
  for (const node of nodes) {
    if (node["Node Type"] === "Seq Scan" && node["Plan Rows"] > 100_000) {
      console.error(`WARNING: Seq Scan on ${node["Relation Name"]} (~${node["Plan Rows"]} rows)`);
      console.error(`Query: ${query.substring(0, 200)}`);
      process.exitCode = 1;
    }
  }
}
```
