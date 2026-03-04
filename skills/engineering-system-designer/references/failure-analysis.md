# Failure Modes & Reliability Patterns

## 1) Failure Mode Analysis: E-Commerce Checkout System

| Component | Failure Mode | Impact | Detection | Mitigation | Recovery Time |
|---|---|---|---|---|---|
| Payment Gateway | Timeout (>5s) | User cannot complete purchase; revenue loss | p99 latency alert >3s | Circuit breaker (open after 3 consecutive timeouts); retry with exponential backoff (max 2 retries); fallback to secondary payment provider | Auto-recovery when gateway responds; circuit half-open after 30s |
| Inventory Service | Process crash | Cannot verify stock; overselling risk | Health check failure; error rate spike on `/reserve` endpoint | Pessimistic stock reservation with DB-level row lock as fallback; return "temporarily unavailable" for affected SKUs | Auto-restart via orchestrator <10s; stale reservations expire after 5 min TTL |
| Primary Database | Failover to replica | 5-30s of write unavailability; reads unaffected | Replication lag alert; connection error rate spike | Connection pool retries with 1s backoff; queue writes in memory (bounded buffer, max 500 ops); idempotency keys prevent duplicates on replay | Automated failover 15-30s (RDS Multi-AZ); manual promotion <5 min |
| Redis Cache | Cache stampede (mass expiration) | All requests hit DB simultaneously; potential DB overload | DB QPS spike >5x baseline; cache hit ratio drops below 50% | Staggered TTLs (base TTL +/- 10% jitter); request coalescing (singleflight pattern); pre-warm cache for high-traffic keys | Self-resolving as cache repopulates; ~30s to stabilize |
| Network | Partition between app and DB | Writes fail; stale reads from cache | Connection timeout errors; split-brain detection via heartbeat | Serve cached/stale data with degradation banner; queue writes locally; reject new checkout starts if partition >60s | Depends on network repair; app auto-reconnects with backoff |

## 2) Cache Strategies Compared

| Strategy | Consistency | Read Latency | Write Latency | On Cache Failure | Best Use Case |
|---|---|---|---|---|---|
| Cache-aside | Eventual (stale reads possible) | Cache hit: fast; miss: slow (DB + cache write) | No cache penalty on write | Reads fall through to DB; graceful degradation | Read-heavy, tolerates staleness (product catalog, URL shortener) |
| Write-through | Strong (cache always current) | Always fast (cache is warm) | Slower (write to cache + DB synchronously) | Writes fail if cache is down | Read-heavy, needs strong consistency (user sessions) |
| Write-behind | Eventual (DB lags cache) | Always fast | Fast (write to cache only, async DB write) | **Data loss risk** if cache crashes before DB flush | Write-heavy, tolerates some data loss (analytics counters) |
| Read-through | Eventual (same as cache-aside) | Cache hit: fast; miss: slow (cache fetches from DB) | No cache penalty on write | Same as cache-aside | When cache library manages DB fetching (simplifies app code) |

### Cache-Aside Implementation (TypeScript)
```typescript
import Redis from "ioredis";
import { Pool } from "pg";

const redis = new Redis({ host: "cache.internal", port: 6379 });
const db = new Pool({ connectionString: process.env.DATABASE_URL });

async function getUrl(shortHash: string): Promise<string | null> {
  // 1. Check cache
  const cached = await redis.get(`url:${shortHash}`);
  if (cached) return cached;

  // 2. Cache miss — query DB
  const result = await db.query(
    "SELECT original_url FROM urls WHERE short_hash = $1",
    [shortHash]
  );
  if (result.rows.length === 0) return null;

  const url = result.rows[0].original_url;

  // 3. Populate cache with jittered TTL (avoid stampede)
  const baseTtl = 3600;
  const jitter = Math.floor(Math.random() * 360); // +/- 10%
  await redis.set(`url:${shortHash}`, url, "EX", baseTtl + jitter);

  return url;
}
```

### Write-Through Implementation (TypeScript)
```typescript
async function createUrl(shortHash: string, originalUrl: string): Promise<void> {
  // 1. Write to DB first (source of truth)
  await db.query(
    "INSERT INTO urls (short_hash, original_url) VALUES ($1, $2)",
    [shortHash, originalUrl]
  );

  // 2. Write to cache synchronously (caller blocks until both succeed)
  await redis.set(`url:${shortHash}`, originalUrl, "EX", 86400);
}
```

## 3) Priority-Based Load Shedding (TypeScript)

```typescript
import { Request, Response, NextFunction } from "express";
import os from "os";

type Priority = "critical" | "normal" | "background";

function getPriority(req: Request): Priority {
  if (req.path === "/healthz" || req.path === "/readyz") return "critical";
  if (req.headers["x-priority"] === "background") return "background";
  if (req.path.startsWith("/admin/")) return "background";
  return "normal";
}

function getCpuUsage(): number {
  const cpus = os.cpus();
  const total = cpus.reduce((sum, cpu) => {
    const times = cpu.times;
    return sum + times.user + times.nice + times.sys + times.idle + times.irq;
  }, 0);
  const idle = cpus.reduce((sum, cpu) => sum + cpu.times.idle, 0);
  return 1 - idle / total; // 0.0 to 1.0
}

export function loadShedding(): (req: Request, res: Response, next: NextFunction) => void {
  return (req: Request, res: Response, next: NextFunction) => {
    const cpu = getCpuUsage();
    const priority = getPriority(req);

    if (priority === "background" && cpu > 0.8) {
      return res.status(503).json({ error: "Service busy", retryAfter: 10 });
    }
    if (priority === "normal" && cpu > 0.9) {
      return res.status(503).json({ error: "Service overloaded", retryAfter: 30 });
    }
    // Critical requests (health checks) are never shed
    next();
  };
}
```

## 4) Bulkhead Pattern: Per-Client Isolation (TypeScript)

```typescript
const clientSemaphores = new Map<string, { current: number; max: number }>();

const DEFAULT_MAX_CONCURRENT = 10;

export function bulkhead(maxPerClient: number = DEFAULT_MAX_CONCURRENT) {
  return async (req: Request, res: Response, next: NextFunction) => {
    const clientId = req.headers["x-client-id"] as string || "anonymous";

    if (!clientSemaphores.has(clientId)) {
      clientSemaphores.set(clientId, { current: 0, max: maxPerClient });
    }

    const sem = clientSemaphores.get(clientId)!;
    if (sem.current >= sem.max) {
      return res.status(429).json({
        error: "Too many concurrent requests",
        limit: sem.max,
      });
    }

    sem.current++;
    res.on("finish", () => { sem.current--; });
    next();
  };
}
```

## 5) Chaos Engineering Checklist

| Experiment | Method | Expected Behavior | Pass Criteria |
|---|---|---|---|
| Kill random pod | `kubectl delete pod <name>` | Orchestrator restarts pod; requests route to healthy pods during restart | Zero failed requests observed by clients; new pod healthy within 30s |
| Network latency 100ms | `tc qdisc add dev eth0 root netem delay 100ms` | Increased p99 latency; no errors; timeouts do not fire | p99 < baseline + 150ms; error rate unchanged |
| Network latency 500ms | Same tool, 500ms delay | Some client-facing latency increase; circuit breakers remain closed | No cascading failures; all requests complete within SLA (2s) |
| Network latency 2s | Same tool, 2s delay | Circuit breakers open for affected downstream; fallback responses served | Graceful degradation; no thread pool exhaustion; recovery within 60s of fix |
| Fill disk to 90% | `fallocate -l <size> /tmp/fill` | Log rotation triggers; alerts fire; writes to WAL still succeed | Database remains writable; disk alert fires within 2 min |
| Exhaust connection pool | Open max connections and hold them | New requests receive 503; existing in-flight requests complete | No hung threads; pool recovers within 10s of connections releasing |
| DNS failure | Block DNS resolution via iptables | Cached DNS entries used; new resolutions fail; circuit breakers open | Services with cached entries continue; others degrade gracefully within 5s |
| Clock skew (+5 min) | `date -s "+5 minutes"` on one node | Token validation may fail; log timestamps misaligned; alerts on clock drift | Mutual TLS unaffected; NTP sync corrects within 1 min; no data corruption |
