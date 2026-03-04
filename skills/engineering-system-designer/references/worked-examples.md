# Worked System Design Examples

## Example 1: URL Shortener (bit.ly-style)

### Requirements
- 100M new URLs created per month
- 10:1 read-to-write ratio
- 5-year data retention
- Short URLs must be globally unique and as short as possible
- Analytics: track click counts per URL

### Capacity Estimation
```
Write QPS:  100M / (30 * 86400) ≈ 39 writes/sec (peak 2x ≈ 78/sec)
Read QPS:   39 * 10 = 390 reads/sec (peak ≈ 780/sec)
Storage per URL: ~500 bytes (hash + original URL + metadata)
Total URLs in 5 years: 100M * 12 * 5 = 6 billion
Total storage: 6B * 500 bytes = 3 TB
Bandwidth (reads): 780 * 500 bytes = 390 KB/sec outbound at peak
```

### High-Level Design
```
Client → API Gateway (rate limiting, auth)
  ├─ POST /urls → Write Service → PostgreSQL (primary)
  └─ GET /:hash → Read Service → Redis Cache → PostgreSQL (replica)

Async path: Write Service → Kafka → Analytics Consumer → ClickHouse
```

### Database Schema (PostgreSQL)
```sql
CREATE TABLE urls (
    id          BIGSERIAL PRIMARY KEY,
    short_hash  CHAR(7) UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    user_id     UUID,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '5 years'
);
CREATE INDEX idx_urls_hash ON urls (short_hash);
CREATE INDEX idx_urls_expiry ON urls (expires_at) WHERE expires_at IS NOT NULL;
```

### URL Generation: Two Approaches

**Approach A -- Base62 encode auto-increment ID**
- Generate: `base62(next_id)` produces short, unique hashes (e.g., ID 1000000 → `"4c92"`)
- Pros: zero collisions, sequential IDs make DB inserts efficient
- Cons: predictable/enumerable URLs, requires centralized ID generator (single point of failure)
- Mitigation: use a distributed ID service (Snowflake/TSID) to remove the single point of failure

**Approach B -- Random hash with collision check**
- Generate: `base62(random_bytes(5))` → 7-character string, check DB for collision
- Pros: non-predictable, no centralized dependency
- Cons: collision probability grows with scale (~0.001% at 6B URLs with 7 chars), extra DB read on write
- Mitigation: retry on collision (max 3 attempts), use 8 chars if collision rate exceeds 0.01%

**Decision**: Use Approach A with a Snowflake-style ID generator for production systems where predictability is acceptable. Use Approach B when URL secrecy matters.

### Caching Strategy
- **Pattern**: cache-aside (lazy population)
- **Store**: Redis cluster with 50 GB capacity (hot set of ~100M URLs)
- **Key**: `url:{short_hash}` → original URL string
- **TTL**: match URL expiration time, cap at 24 hours for very long-lived URLs
- **Invalidation**: on URL deletion, explicitly `DEL url:{hash}` from Redis
- **Cache hit ratio target**: 95%+ (most traffic hits a small fraction of URLs)

### Analytics Pipeline
```
Read Service emits click event → Kafka topic "url-clicks"
  → Analytics Consumer (batch writes every 5 sec)
    → ClickHouse table: (short_hash, timestamp, country, referrer, device_type)

Real-time dashboard reads from ClickHouse.
Daily rollups aggregate into per-URL daily counts.
```

---

## Example 2: Chat System (WhatsApp-like)

### Requirements
- 500M registered users, 50M daily active
- 1:1 and group chat (max 256 members per group)
- Message delivery guarantee: at-least-once, deduplicated on client
- Read receipts (sent → delivered → read)
- Message history stored for 30 days on server, indefinitely on device

### Capacity Estimation
```
Messages/day:   50M DAU * 40 msgs/day = 2 billion messages/day
Write QPS:      2B / 86400 ≈ 23,000 writes/sec (peak 3x ≈ 70,000/sec)
Avg message:    200 bytes text + 100 bytes metadata = 300 bytes
Storage/day:    2B * 300 bytes = 600 GB/day
Storage/30 days: 18 TB
Concurrent WebSocket connections: ~10M (20% of DAU online simultaneously)
```

### High-Level Design
```
Client ↔ WebSocket Gateway (10M persistent connections, partitioned by user_id)
  ├─ Send message → Message Service → Kafka → Message Store (Cassandra)
  │                                  └─→ Delivery fanout to recipient gateway(s)
  ├─ Delivery/read ack → Status Service → update message state
  └─ Presence heartbeat → Presence Service → Redis sorted set
```

### Message Storage (Cassandra)
```cql
CREATE TABLE messages (
    chat_id    UUID,
    message_id TIMEUUID,       -- time-ordered, globally unique
    sender_id  UUID,
    content    TEXT,
    msg_type   TEXT,            -- 'text', 'image', 'system'
    created_at TIMESTAMP,
    PRIMARY KEY (chat_id, message_id)
) WITH CLUSTERING ORDER BY (message_id ASC);
```
- **Partition key** `chat_id`: all messages for a chat live on the same partition, enabling efficient range queries ("last 50 messages")
- **Clustering key** `message_id` (TIMEUUID): messages are physically sorted by time within a partition
- **Partition size limit**: for very active groups, sub-partition by month: `PRIMARY KEY ((chat_id, month_bucket), message_id)`

### Delivery Guarantee
```
Message lifecycle:
  1. Client sends message → server assigns message_id, persists to Cassandra
  2. Server returns ACK to sender → message state = SENT
  3. Server pushes to recipient via WebSocket (or queues if offline)
  4. Recipient device ACKs receipt → state = DELIVERED
  5. Recipient opens chat → client sends read ACK → state = READ

Offline handling:
  - Messages queued in per-user Kafka partition
  - On reconnect, gateway drains the user's queue in order
  - Client deduplicates by message_id (idempotent processing)
  - Queue TTL = 30 days (matches server retention)
```

### Group Messaging: Fan-Out Strategy

**Fan-out on write (small groups, <=50 members)**
- On send, write one copy to group chat and push notification to each member's gateway
- Pros: simple read path, instant delivery, low read latency
- Cons: write amplification scales with group size
- Use when: groups are small and all members are likely to read the message

**Fan-out on read (large groups, >50 members)**
- On send, write once to group chat partition only
- Each member pulls from the group partition on app open or via periodic sync
- Pros: constant write cost regardless of group size
- Cons: higher read latency, more complex sync logic
- Use when: large groups where most members read messages hours later

**Threshold**: groups with <=50 members use fan-out on write; above 50 use fan-out on read. The threshold is configurable per deployment.

### Presence System
```
Online detection:
  - Client sends heartbeat every 30 seconds over WebSocket
  - Gateway writes to Redis sorted set: ZADD presence:<shard> <timestamp> <user_id>
  - User is "online" if their score (timestamp) is within last 60 seconds

Querying presence:
  - Client requests presence for contacts list
  - Server: ZRANGEBYSCORE presence:<shard> <now - 60> +inf
  - Returns set of online user_ids, intersected with requester's contacts

Scaling:
  - Shard the sorted set by user_id hash (e.g., 256 shards)
  - Each shard holds ~200K users → small enough for fast ZRANGEBYSCORE
  - Background job prunes entries older than 5 minutes every 60 seconds
```
