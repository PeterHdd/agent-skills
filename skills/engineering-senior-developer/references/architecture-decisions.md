# Architecture Decision Matrices

## 1) Monolith vs Microservices

### Decision Matrix — Score Each Row (1-5), Multiply by Weight

```
FACTOR                    WEIGHT   MONOLITH WINS IF...         MICROSERVICES WIN IF...
─────────────────────     ──────   ────────────────────────    ──────────────────────────────
Team size                 3x       1-15 engineers              25+ engineers (3+ teams)
Deployment frequency      2x       < 5 deploys/week            > 20 deploys/week across teams
Domain complexity         3x       < 5 bounded contexts        8+ distinct bounded contexts
Scaling requirements      2x       Uniform load across app     10x difference between features
Operational maturity      3x       No k8s, no service mesh     CI/CD, observability, k8s in place
Time to market            2x       MVP or pre-PMF              Scaling proven product

SCORING:
  Monolith score = SUM(weight * monolith_score for each factor)
  Microservices score = SUM(weight * microservices_score for each factor)

  If monolith leads by > 15 points: stay monolith.
  If microservices lead by > 15 points: decompose.
  If within 15 points: start modular monolith, extract later.
```

### Concrete Thresholds

```
Team size 1-8:     Monolith. No exceptions. Microservices overhead will kill you.
Team size 8-20:    Modular monolith with clear module boundaries. Extract ONE service
                   only if there's a concrete scaling or deployment bottleneck.
Team size 20-50:   2-5 services aligned to team ownership. NOT one service per developer.
Team size 50+:     Service-oriented architecture. Each team owns 1-3 services.

Deploy frequency < 2/day: Monolith is fine. The overhead of service coordination
                          outweighs independent deployment benefits.
Deploy frequency 2-10/day: Modular monolith or 2-3 services max.
Deploy frequency > 10/day: Microservices justified IF teams are independent.
```

---

## 2) Database Selection Matrix

### Scoring (1-5 per use case, 5 = best fit)

```
USE CASE                  PostgreSQL  MySQL  MongoDB  DynamoDB  Redis
──────────────────────    ──────────  ─────  ───────  ────────  ─────
Relational/transactional       5        4       2        2       1
Complex queries/reporting      5        4       2        1       1
Document/flexible schema       3        2       5        4       1
High-write throughput          3        3       4        5       3
Key-value lookups              2        2       3        4       5
Time-series data               4        3       3        3       3
Full-text search               4        3       4        1       1
Geospatial queries             5        3       4        1       2
Session/cache storage          2        2       3        3       5
Event sourcing                 3        2       4        4       3
Multi-region replication       3        3       4        5       3
Cost at < 10GB                 5        5       4        3       4
Cost at > 1TB                  4        4       3        5       2
Operational complexity         3        4       3        5       4
Team familiarity (avg)         4        4       3        2       4
```

### Decision Tree

```
Q: Do you need ACID transactions across multiple tables?
├─ YES → PostgreSQL (or MySQL if team prefers)
│   Q: Do you also need JSON document storage?
│   ├─ YES → PostgreSQL with JSONB columns (best of both worlds)
│   └─ NO → PostgreSQL with normalized schema
└─ NO
   Q: Is your access pattern primarily key-value lookup?
   ├─ YES
   │   Q: Do you need persistence beyond restart?
   │   ├─ YES and data < 50GB → Redis with AOF persistence
   │   ├─ YES and data > 50GB → DynamoDB
   │   └─ NO → Redis (in-memory only)
   └─ NO
      Q: Is your schema highly variable (> 5 shapes per collection)?
      ├─ YES → MongoDB (or PostgreSQL JSONB if you also need joins)
      └─ NO
         Q: Do you need > 50k writes/second sustained?
         ├─ YES → DynamoDB (predictable performance at any scale)
         └─ NO → PostgreSQL (default choice — most versatile)
```

### The Default Choice Rule

```
If you don't have a specific reason to pick something else, use PostgreSQL.
It handles 90% of application workloads well, has the best ecosystem of
extensions, your team probably already knows SQL, and it scales to
hundreds of millions of rows with proper indexing.

Only deviate when you hit a CONCRETE limitation, not a theoretical one.
```

---

## 3) Queue / Message Broker Selection

```
FACTOR                    SQS              RabbitMQ         Kafka
──────────────────────    ─────────────    ─────────────    ─────────────
Latency (p50)             20-50ms          1-5ms            5-15ms
Throughput (per node)     3k msg/s         20k msg/s        100k+ msg/s
Message ordering          Per-group (FIFO) Per-queue        Per-partition
Exactly-once delivery     FIFO queues      With confirms    With txn API
Message replay            No               No               Yes (retention)
Max message size          256KB            128MB (config)   1MB default
Consumer groups           No (single)      No (competing)   Yes (native)
Operational overhead      Zero (managed)   Medium (cluster) High (ZK/KRaft)
Cost at 1M msgs/month     ~$0.40           Server cost      Server cost
Cost at 1B msgs/month     ~$400            Server cost      Server cost
Dead letter queue         Built-in         Plugin           Custom topic
Multi-region              Cross-region     Federation       MirrorMaker
```

### Decision Tree

```
Q: Do you need to replay messages (event sourcing, reprocessing)?
├─ YES → Kafka (only option with log retention and consumer offsets)
└─ NO
   Q: Do you need > 50k messages/second sustained throughput?
   ├─ YES → Kafka
   └─ NO
      Q: Can you accept 20-50ms delivery latency?
      ├─ YES
      │   Q: Do you want zero operational overhead?
      │   ├─ YES → SQS (fully managed, scales automatically)
      │   └─ NO → RabbitMQ (more features, more control)
      └─ NO (need < 5ms latency)
         → RabbitMQ (lowest latency, direct push to consumers)

COMMON PATTERNS:
  Background jobs (email, reports)     → SQS (simple, cheap, reliable)
  Service-to-service async commands    → SQS FIFO or RabbitMQ
  Event streaming (analytics, logs)    → Kafka
  Real-time notifications              → RabbitMQ (low latency push)
  CQRS event store                     → Kafka (replay capability)
  Task queue with priorities           → RabbitMQ (priority queues native)
```

---

## 4) Caching Strategy

```
STRATEGY            LOCAL (in-process)     DISTRIBUTED (Redis)     CDN (CloudFront/Fastly)
──────────────────  ────────────────────   ────────────────────    ──────────────────────
Latency             < 0.1ms (memory)       1-5ms (network)         0ms (edge, cache hit)
Capacity            100MB-1GB per node     Unlimited (cluster)     Unlimited (edge network)
Consistency         Per-process only       Shared across nodes     Eventually consistent
Invalidation        Instant (local)        Pub/sub or TTL          TTL or purge API (seconds)
Best for            Config, small lookups  Sessions, user data     Static assets, API responses
Worst for           User-specific data     Sub-ms requirements     Personalized content
Cache stampede      Per-process (mild)     Global (severe)         Edge (very severe)
Memory overhead     Adds to app heap       Separate infra          No app overhead
```

### Cache Hit Rate Thresholds

```
Hit rate > 95%:  Cache is working well. Monitor but don't change.
Hit rate 80-95%: Acceptable. Check if TTL is too short or key cardinality too high.
Hit rate 50-80%: Poor. Investigate: are keys too specific? Is TTL too aggressive?
Hit rate < 50%:  Cache is not helping. Either fix the key strategy or remove the cache
                 (caching adds complexity — if it doesn't help, it only hurts).
```

### Cache Stampede Prevention

```ts
// Problem: 1000 requests arrive, all see cache miss, all hit the DB simultaneously
// Solution: Mutex lock — only one request computes, others wait for the result

import { Redis } from "ioredis";
const redis = new Redis();

async function cachedQuery<T>(key: string, ttlSeconds: number, compute: () => Promise<T>): Promise<T> {
  // Try cache first
  const cached = await redis.get(key);
  if (cached) return JSON.parse(cached);

  // Acquire a lock (NX = only if not exists, EX = auto-expire)
  const lockKey = `lock:${key}`;
  const acquired = await redis.set(lockKey, "1", "EX", 10, "NX");

  if (acquired) {
    // We got the lock — compute the value
    try {
      const result = await compute();
      await redis.setex(key, ttlSeconds, JSON.stringify(result));
      return result;
    } finally {
      await redis.del(lockKey);
    }
  } else {
    // Someone else is computing — wait and retry from cache
    await new Promise(r => setTimeout(r, 100));
    return cachedQuery(key, ttlSeconds, compute); // retry (add max retries in production)
  }
}
```

---

## 5) API Style Selection

### Decision Tree

```
Q: Are clients primarily internal services (server-to-server)?
├─ YES
│   Q: Do you need streaming or bidirectional communication?
│   ├─ YES → gRPC (bidirectional streaming, multiplexing)
│   └─ NO
│      Q: Is performance critical (< 5ms latency, > 10k RPS)?
│      ├─ YES → gRPC (binary protocol, ~10x smaller than JSON, codegen)
│      └─ NO → REST (simpler debugging, curl-friendly, wider tooling)
└─ NO (external clients: web, mobile, third-party)
   Q: Do clients need flexible field selection (many different views of same data)?
   ├─ YES
   │   Q: Is the data graph-shaped (many relationships, nested resources)?
   │   ├─ YES → GraphQL (eliminates over/under-fetching, single endpoint)
   │   └─ NO → REST with sparse fieldsets (?fields=id,name,email)
   └─ NO → REST (widest client compatibility, best tooling, simplest caching)
```

### Comparison Matrix

```
FACTOR                   REST            GraphQL          gRPC
───────────────────────  ──────────────  ───────────────  ──────────────
Caching                  HTTP native     Custom (Apollo)  Custom
Browser support          Native          Native (HTTP)    grpc-web (extra)
Type safety              OpenAPI (opt)   Schema (built-in) Protobuf (built-in)
Overfetching             Common          Solved           N/A (defined msgs)
Learning curve           Low             Medium           Medium
File uploads             Multipart       Messy            Streaming native
Real-time updates        SSE/WebSocket   Subscriptions    Streaming
Payload size             JSON (~1x)      JSON (~0.7x)     Binary (~0.1x)
Code generation          Optional        Optional         Required
Error handling           HTTP status     errors[] array   Status codes
Versioning               URL or header   Schema evolution Package version
Tooling maturity         Excellent       Good             Good
```

### When NOT to Use GraphQL

```
Skip GraphQL if:
  - You have < 5 client-facing endpoints (REST is simpler)
  - Your API is action-oriented, not data-oriented (use REST/RPC)
  - You need HTTP caching (GraphQL uses POST for queries)
  - Your team has no GraphQL experience and deadline is < 3 months
  - You don't have a dedicated frontend team driving requirements
```

---

## 6) Authentication Strategy

```
FACTOR                  Sessions            JWT (stateless)      OAuth2 + OIDC
───────────────────     ─────────────────   ─────────────────   ──────────────────
State                   Server-side store   Token carries state  Delegated to provider
Scalability             Need shared store   Stateless (any node) Stateless (verify sig)
Revocation              Instant (delete)    Hard (blocklist or   Instant (provider)
                                            short TTL)
Token size              Session ID (~32B)   500B-2KB             Access token varies
Security (XSS)          Cookie (httpOnly)   localStorage (risky) Cookie or token
Security (CSRF)         Needs CSRF token    Immune (if header)   Depends on grant
Multi-device            Session per device  Token per device     Provider handles
Third-party access      Not designed for    Not designed for     Native (scopes)
Implementation cost     Low                 Medium               Low (use provider SDK)
Best for                Traditional web     Service-to-service   Consumer-facing apps
                        apps, SSR           APIs, microservices  with social login
```

### Decision Tree

```
Q: Do users sign in with Google, GitHub, or another identity provider?
├─ YES → OAuth2 + OIDC (don't build your own identity)
│   Implementation: Use Auth0, Clerk, or Cognito. Not worth building from scratch.
└─ NO (your own username/password)
   Q: Is this a server-rendered app (Next.js, Rails, Django)?
   ├─ YES → Sessions (httpOnly cookies, server-side store in Redis/DB)
   │   Session TTL: 24h for active sessions, 30d with "remember me"
   │   Store: Redis (fast) or PostgreSQL (simpler ops, slightly slower)
   └─ NO
      Q: Is this service-to-service (no browser involved)?
      ├─ YES → JWT with short TTL (5-15 minutes) + refresh token rotation
      │   Sign with RS256 (asymmetric) so services can verify without shared secret
      │   Include: sub, iss, exp, iat, jti (for blocklist), roles/scopes
      └─ NO (SPA / mobile app)
         → JWT with BFF (Backend for Frontend) pattern:
           - Browser gets httpOnly cookie (session) with the BFF
           - BFF exchanges cookie for JWT when calling APIs
           - Best of both: browser safety (cookies) + API flexibility (JWT)
```

### JWT Security Checklist

```
[x] Use RS256 or ES256, NEVER HS256 with shared secrets across services
[x] Set exp (expiry) to 5-15 minutes maximum
[x] Include jti (JWT ID) for revocation/blocklist capability
[x] Validate iss (issuer) and aud (audience) on every request
[x] Store refresh tokens server-side (DB/Redis), not in the JWT
[x] Rotate refresh tokens on each use (detect token theft)
[x] Never store JWTs in localStorage (XSS vulnerable)
    Use httpOnly cookies or BFF pattern for browser apps
[x] Set token size budget: < 1KB. If larger, you're putting too much in the JWT.
```
