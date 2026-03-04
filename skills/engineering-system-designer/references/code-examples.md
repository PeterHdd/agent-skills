# System Design Code Examples

## 1) Capacity Estimation Calculations (Python)
```python
# URL shortener capacity estimation
MAU = 50_000_000
WRITES_PER_USER_MONTH = 0.5
READ_WRITE_RATIO = 100

writes_per_sec = (MAU * WRITES_PER_USER_MONTH) / (30 * 86400)  # ~9.6 QPS
reads_per_sec = writes_per_sec * READ_WRITE_RATIO               # ~960 QPS

RECORD_BYTES = 600  # 500 URL + 100 metadata
total_records_5yr = MAU * WRITES_PER_USER_MONTH * 12 * 5         # 1.5B records
storage_tb = (total_records_5yr * RECORD_BYTES) / (1024 ** 4)    # ~0.82 TB
outbound_kbps = reads_per_sec * RECORD_BYTES * 8 / 1000          # ~4,608 kbps
```

## 2) API Contract Definition (OpenAPI YAML)
```yaml
openapi: "3.0.3"
info:
  title: URL Shortener API
  version: "1.0.0"
paths:
  /urls:
    post:
      summary: Create a short URL
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [original_url]
              properties:
                original_url: { type: string, format: uri, maxLength: 2048 }
                custom_alias: { type: string, pattern: "^[a-zA-Z0-9_-]{4,16}$" }
                ttl_seconds: { type: integer, minimum: 60, maximum: 31536000 }
      responses:
        "201": { description: Short URL created }
        "409": { description: Alias already taken }
        "429": { description: Rate limit exceeded }
```

## 3) Database Schema with Sharding Key Design (SQL)
```sql
CREATE TABLE urls (
    short_hash CHAR(7) PRIMARY KEY,  -- base62, uniformly distributed shard key
    original_url TEXT NOT NULL,
    creator_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    click_count BIGINT NOT NULL DEFAULT 0
);
-- Sharding: hash(short_hash) mod N; ~300M rows per shard at 10x scale
CREATE INDEX idx_urls_creator ON urls (creator_id, created_at DESC);
CREATE INDEX idx_urls_expiry ON urls (expires_at) WHERE expires_at IS NOT NULL;
```

## 4) Circuit Breaker (Python)
```python
import time
from enum import Enum

class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = State.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def call(self, fn, *args, **kwargs):
        if self.state == State.OPEN:
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self.state = State.HALF_OPEN
            else:
                raise RuntimeError("Circuit is OPEN; call rejected")
        try:
            result = fn(*args, **kwargs)
            self.failure_count, self.state = 0, State.CLOSED
            return result
        except Exception:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            if self.failure_count >= self.failure_threshold:
                self.state = State.OPEN
            raise
```
