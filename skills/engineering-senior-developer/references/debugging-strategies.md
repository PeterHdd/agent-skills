# Systematic Debugging Strategies

## 1) Binary Search Debugging with Git Bisect

### Automated Bisect with a Test Script

```bash
# Scenario: tests pass on v2.3.0 (3 weeks ago) but fail on HEAD.
# 847 commits in between. Binary search finds the bad commit in ~10 steps.

# Step 1: Start bisect
git bisect start
git bisect bad HEAD
git bisect good v2.3.0

# Step 2: Write a test script that exits 0 (good) or 1 (bad)
cat > /tmp/bisect-test.sh << 'SCRIPT'
#!/bin/bash
npm ci --silent 2>/dev/null
npm run build --silent 2>/dev/null
# The specific test that reproduces the bug:
npm test -- --grep "checkout calculates tax correctly" 2>/dev/null
SCRIPT
chmod +x /tmp/bisect-test.sh

# Step 3: Run automated bisect (tests each commit automatically)
git bisect run /tmp/bisect-test.sh

# Output: abc1234 is the first bad commit
# Step 4: Examine the offending commit
git show abc1234 --stat
git bisect reset
```

### Bisect for Non-Test Failures (Performance Regression)

```bash
cat > /tmp/bisect-perf.sh << 'SCRIPT'
#!/bin/bash
npm ci --silent 2>/dev/null && npm run build --silent 2>/dev/null
# Start server, measure latency, check against threshold
node dist/server.js &
PID=$!
sleep 3
LATENCY=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:3000/api/health)
kill $PID 2>/dev/null
# Threshold: response must be under 200ms (0.2 seconds)
echo "Latency: ${LATENCY}s"
if (( $(echo "$LATENCY > 0.2" | bc -l) )); then
  exit 1  # bad — too slow
fi
exit 0    # good — fast enough
SCRIPT
chmod +x /tmp/bisect-perf.sh
git bisect start && git bisect bad HEAD && git bisect good v2.1.0
git bisect run /tmp/bisect-perf.sh
```

---

## 2) Log-Based Debugging

### Structured Log Correlation Across Services

```
When debugging across microservices, correlate logs using these fields:

REQUIRED FIELDS in every log line:
  correlationId  — UUID propagated via X-Correlation-ID header across all services
  service        — which service emitted the log
  timestamp      — ISO 8601 with milliseconds
  level          — info/warn/error
  msg            — human-readable message

QUERY PATTERN (e.g., in Datadog, Loki, CloudWatch Logs Insights):

  # Find the full request path for a failed checkout
  correlationId="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  | sort timestamp asc

  # Typical result — one correlation ID traced across 4 services:
  10:41:23.001 api-gateway     INFO  Received POST /checkout {userId: "u-789"}
  10:41:23.045 order-service   INFO  Creating order {items: 3, total: 149.99}
  10:41:23.112 payment-service INFO  Charging card {amount: 149.99, provider: "stripe"}
  10:41:23.850 payment-service ERROR Stripe API timeout after 700ms {retryable: true}
  10:41:24.560 payment-service INFO  Retry 1 succeeded {chargeId: "ch_abc"}
  10:41:24.590 order-service   INFO  Order confirmed {orderId: "ord-456"}
  10:41:24.610 email-service   INFO  Sending confirmation {to: "user@example.com"}
```

### Request Tracing with Correlation IDs — Propagation Pattern

```ts
// Middleware: extract or create correlation ID
import { randomUUID } from "node:crypto";
import { AsyncLocalStorage } from "node:async_hooks";

const als = new AsyncLocalStorage<{ correlationId: string }>();

export function tracingMiddleware(req: Request, res: Response, next: NextFunction) {
  const correlationId = (req.headers["x-correlation-id"] as string) || randomUUID();
  res.setHeader("x-correlation-id", correlationId);
  als.run({ correlationId }, next);
}

// When calling downstream services, always forward the correlation ID
export async function callDownstream(url: string, body: unknown) {
  const ctx = als.getStore();
  return fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Correlation-ID": ctx?.correlationId ?? "unknown",
    },
    body: JSON.stringify(body),
  });
}
```

---

## 3) Reproduction Techniques

### Capturing and Replaying HTTP Traffic

```ts
// Record incoming requests to a file for replay during debugging
import fs from "node:fs";

const recordFile = fs.createWriteStream("/tmp/traffic-capture.jsonl", { flags: "a" });

app.use((req, res, next) => {
  if (process.env.RECORD_TRAFFIC === "true") {
    const record = {
      timestamp: Date.now(),
      method: req.method,
      url: req.originalUrl,
      headers: req.headers,
      body: req.body,
    };
    recordFile.write(JSON.stringify(record) + "\n");
  }
  next();
});

// Replay script: replay captured traffic against a local server
// replay.ts
import fs from "node:fs";
import readline from "node:readline";

const rl = readline.createInterface({ input: fs.createReadStream("/tmp/traffic-capture.jsonl") });

for await (const line of rl) {
  const { method, url, headers, body } = JSON.parse(line);
  const resp = await fetch(`http://localhost:3000${url}`, {
    method,
    headers: { ...headers, host: "localhost:3000" },
    body: method !== "GET" ? JSON.stringify(body) : undefined,
  });
  console.log(`${method} ${url} -> ${resp.status}`);
}
```

### Seed-Based Test Data Generation

```ts
// Deterministic test data: same seed = same data = reproducible bugs
import { faker } from "@faker-js/faker";

export function generateTestOrders(seed: number, count: number) {
  faker.seed(seed);  // deterministic — same seed always produces same data
  return Array.from({ length: count }, (_, i) => ({
    id: faker.string.uuid(),
    customerId: faker.string.uuid(),
    email: faker.internet.email(),
    items: Array.from({ length: faker.number.int({ min: 1, max: 5 }) }, () => ({
      sku: faker.string.alphanumeric(8),
      name: faker.commerce.productName(),
      price: parseFloat(faker.commerce.price({ min: 5, max: 500 })),
      quantity: faker.number.int({ min: 1, max: 10 }),
    })),
    createdAt: faker.date.recent({ days: 30 }),
  }));
}

// In bug reports: "Reproduces with seed 42, count 500, order index 347"
// const orders = generateTestOrders(42, 500);
// const buggyOrder = orders[347]; // exact same data every time
```

---

## 4) Race Condition Debugging

### Timestamp-Based Race Detection

```ts
// Add microsecond-resolution timestamps to concurrent operations
import { performance } from "node:perf_hooks";

const operationLog: { op: string; t: number; threadId?: string }[] = [];

export function logOp(op: string, threadId?: string) {
  operationLog.push({ op, t: performance.now(), threadId });
}

// After reproducing the race condition, analyze the log:
export function analyzeRaces() {
  const sorted = operationLog.sort((a, b) => a.t - b.t);
  for (let i = 0; i < sorted.length - 1; i++) {
    const gap = sorted[i + 1].t - sorted[i].t;
    console.log(
      `${sorted[i].t.toFixed(3)}ms [${sorted[i].threadId ?? "main"}] ${sorted[i].op}` +
      (gap < 1 ? `  <-- ${gap.toFixed(3)}ms gap (POSSIBLE RACE)` : "")
    );
  }
}

// Example output showing a race:
// 142.301ms [req-a] READ balance = 100
// 142.304ms [req-b] READ balance = 100     <-- 0.003ms gap (POSSIBLE RACE)
// 143.510ms [req-a] WRITE balance = 80
// 143.512ms [req-b] WRITE balance = 70     <-- overwrites req-a's write!
```

### Database-Level Lock Contention Analysis

```sql
-- Find blocked queries and what is blocking them
SELECT
  blocked.pid AS blocked_pid,
  blocked.query AS blocked_query,
  blocked.wait_event_type,
  blocking.pid AS blocking_pid,
  blocking.query AS blocking_query,
  now() - blocked.query_start AS blocked_duration
FROM pg_stat_activity blocked
JOIN pg_locks bl ON bl.pid = blocked.pid AND NOT bl.granted
JOIN pg_locks gl ON gl.locktype = bl.locktype
  AND gl.database IS NOT DISTINCT FROM bl.database
  AND gl.relation IS NOT DISTINCT FROM bl.relation
  AND gl.page IS NOT DISTINCT FROM bl.page
  AND gl.tuple IS NOT DISTINCT FROM bl.tuple
  AND gl.pid != bl.pid
  AND gl.granted
JOIN pg_stat_activity blocking ON blocking.pid = gl.pid
ORDER BY blocked_duration DESC;
```

### Fixing Common Race Conditions

```ts
// RACE: Two requests read-then-write the same row
// Request A: read balance=100, write balance=80
// Request B: read balance=100, write balance=70 (overwrites A!)

// FIX 1: Optimistic locking with version column
async function deductBalance(userId: string, amount: number): Promise<boolean> {
  const { rows } = await db.query(
    `UPDATE accounts
     SET balance = balance - $1, version = version + 1
     WHERE user_id = $2 AND balance >= $1 AND version = $3
     RETURNING balance`,
    [amount, userId, expectedVersion]
  );
  if (rows.length === 0) throw new Error("Conflict — retry with fresh version");
  return true;
}

// FIX 2: SELECT FOR UPDATE (pessimistic locking)
async function deductBalancePessimistic(userId: string, amount: number) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const { rows } = await client.query(
      "SELECT balance FROM accounts WHERE user_id = $1 FOR UPDATE",
      [userId]
    );
    if (rows[0].balance < amount) throw new Error("Insufficient funds");
    await client.query(
      "UPDATE accounts SET balance = balance - $1 WHERE user_id = $2",
      [amount, userId]
    );
    await client.query("COMMIT");
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

// FIX 3: Atomic single-statement update (simplest, preferred when possible)
async function deductBalanceAtomic(userId: string, amount: number) {
  const { rowCount } = await db.query(
    "UPDATE accounts SET balance = balance - $1 WHERE user_id = $2 AND balance >= $1",
    [amount, userId]
  );
  if (rowCount === 0) throw new Error("Insufficient funds or user not found");
}
```

---

## 5) Production Debugging

### Safe Debug Endpoints

```ts
// Auth-protected diagnostic endpoints for production debugging
// NEVER expose these without authentication and rate limiting

const adminRouter = express.Router();
adminRouter.use(requireAdminAuth);  // JWT with admin role check
adminRouter.use(rateLimit({ windowMs: 60_000, max: 10 }));

// Current connection pool status
adminRouter.get("/debug/db-pool", (req, res) => {
  res.json({
    total: pool.totalCount,
    idle: pool.idleCount,
    waiting: pool.waitingCount,
  });
});

// In-flight request count and oldest request
adminRouter.get("/debug/requests", (req, res) => {
  res.json({
    inFlight: activeRequests.size,
    oldest: activeRequests.size > 0
      ? Date.now() - Math.min(...activeRequests.values())
      : 0,
  });
});

// Event loop lag snapshot
adminRouter.get("/debug/eventloop", (req, res) => {
  const start = Date.now();
  setImmediate(() => {
    res.json({ lagMs: Date.now() - start });
  });
});

// Memory usage
adminRouter.get("/debug/memory", (req, res) => {
  const mem = process.memoryUsage();
  res.json({
    rssBytes: mem.rss,
    heapUsedBytes: mem.heapUsed,
    heapTotalBytes: mem.heapTotal,
    externalBytes: mem.external,
    rssMB: (mem.rss / 1024 / 1024).toFixed(1),
    heapUsedMB: (mem.heapUsed / 1024 / 1024).toFixed(1),
  });
});
```

### Feature Flags for Verbose Logging

```ts
// Toggle verbose logging per-service or per-endpoint without redeploy
// Controlled via feature flag system or config service

const verboseEndpoints = new Set<string>(); // populated from config

export function verboseLoggingMiddleware(req: Request, res: Response, next: NextFunction) {
  const route = req.route?.path ?? req.path;
  if (verboseEndpoints.has(route) || verboseEndpoints.has("*")) {
    const startTime = Date.now();
    logger.info("REQUEST_START", {
      method: req.method, path: req.path,
      query: req.query, bodySize: JSON.stringify(req.body ?? "").length,
      headers: { "user-agent": req.headers["user-agent"], "content-type": req.headers["content-type"] },
    });

    const originalJson = res.json.bind(res);
    res.json = (body: any) => {
      logger.info("REQUEST_END", {
        method: req.method, path: req.path,
        status: res.statusCode, durationMs: Date.now() - startTime,
        responseSize: JSON.stringify(body).length,
      });
      return originalJson(body);
    };
  }
  next();
}

// Enable/disable at runtime:
// POST /admin/debug/verbose-logging { "endpoint": "/api/checkout", "enabled": true }
adminRouter.post("/debug/verbose-logging", (req, res) => {
  const { endpoint, enabled } = req.body;
  if (enabled) verboseEndpoints.add(endpoint);
  else verboseEndpoints.delete(endpoint);
  logger.info("Verbose logging toggled", { endpoint, enabled });
  res.json({ active: Array.from(verboseEndpoints) });
});
```

### Canary Deployments for Fixes

```yaml
# Deploy fix to 5% of traffic first, monitor, then expand
# Kubernetes canary with Argo Rollouts:
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: order-service
spec:
  strategy:
    canary:
      steps:
        - setWeight: 5        # 5% of traffic gets the fix
        - pause: { duration: 10m }  # bake for 10 minutes
        - analysis:
            templates:
              - templateName: error-rate-check
            args:
              - name: service
                value: order-service
        - setWeight: 25       # if analysis passes, bump to 25%
        - pause: { duration: 10m }
        - setWeight: 75
        - pause: { duration: 5m }
        - setWeight: 100      # full rollout

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: error-rate-check
spec:
  metrics:
    - name: error-rate
      interval: 60s
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(http_requests_total{service="{{args.service}}",status=~"5.."}[2m]))
            /
            sum(rate(http_requests_total{service="{{args.service}}"}[2m]))
      successCondition: result[0] < 0.02  # less than 2% error rate
```

---

## 6) Common Bug Patterns and Their Signatures

```
PATTERN               SIGNATURE                                     FIRST CHECK
────────────────────  ────────────────────────────────────────────   ─────────────────────────────
Memory leak           RSS grows linearly over hours, never drops     Heap snapshot diff: what object
                      after GC. OOM kills in container logs.         type is accumulating?

Connection pool       "connection timeout" errors spike suddenly.    pg_stat_activity: idle connections
exhaustion            Available connections = 0 in pool metrics.     with open transactions? Missing
                      Often after deploy or traffic spike.           .release() calls?

Deadlock              Two+ requests hang forever. No CPU spike.      pg_locks WHERE NOT granted.
                      Other requests to same tables also hang.       Check lock ordering in code:
                      Database logs: "deadlock detected".            Table A->B vs Table B->A?

Cache stampede        Latency spikes every N minutes (TTL interval). Cache miss rate spikes from 2%
                      Database load spikes at same interval.         to 100% simultaneously. Fix:
                      Multiple identical queries run simultaneously. stale-while-revalidate or mutex.

N+1 queries           Endpoint is slow only with large result sets.  Count queries per request. If
                      Query count scales with # of items returned.   it's O(N), you have an N+1.
                      Individual queries are fast (< 5ms each).      Fix: JOIN or WHERE IN().

Retry storm           Error rate amplifies (not reduces) over time.  Check retry config: is there
                      Downstream service gets 10x normal traffic     exponential backoff? Jitter?
                      during degradation. Circuit breaker not        Max retry limit? Circuit breaker
                      opening.                                       properly configured?

Event loop blocking   All endpoints slow simultaneously. p99 goes    monitorEventLoopDelay shows
                      from 50ms to 2000ms. CPU at 100% on one core.  spikes > 100ms. Profile with
                      Not database — DB queries still fast.           clinic flame to find sync code.

Timezone bug          Errors at midnight UTC or at DST transitions.  Search for new Date() without
                      Off-by-one-day errors for users in certain     explicit timezone. Check if DB
                      timezones. Test data (UTC) works fine.         stores UTC vs local time.
```
