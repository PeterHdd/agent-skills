# API Design Patterns

## REST API with Cursor Pagination

```typescript
import express, { Request, Response } from "express";
import { Pool } from "pg";

const db = new Pool();
const router = express.Router();

function encodeCursor(id: string, createdAt: string): string {
  return Buffer.from(`${id}|${createdAt}`).toString("base64url");
}

function decodeCursor(cursor: string): { id: string; createdAt: string } {
  const [id, createdAt] = Buffer.from(cursor, "base64url").toString().split("|");
  return { id, createdAt };
}

router.get("/api/posts", async (req: Request, res: Response) => {
  const limit = Math.min(parseInt(req.query.limit as string) || 20, 100);
  const cursor = req.query.cursor as string | undefined;

  let query = `SELECT id, title, created_at FROM posts WHERE is_published = true`;
  const params: unknown[] = [];

  if (cursor) {
    const { id, createdAt } = decodeCursor(cursor);
    query += ` AND (created_at, id) < ($1, $2)`;
    params.push(createdAt, id);
  }

  query += ` ORDER BY created_at DESC, id DESC LIMIT $${params.length + 1}`;
  params.push(limit + 1); // fetch one extra to detect next page

  const { rows } = await db.query(query, params);
  const hasMore = rows.length > limit;
  const data = hasMore ? rows.slice(0, limit) : rows;
  const nextCursor = hasMore ? encodeCursor(data[data.length - 1].id, data[data.length - 1].created_at) : null;

  res.json({ data, pagination: { next_cursor: nextCursor, has_more: hasMore } });
});
```

## Sliding Window Rate Limiter with Redis

```typescript
import Redis from "ioredis";
import { Request, Response, NextFunction } from "express";

const redis = new Redis();

function rateLimiter(opts: { windowMs: number; max: number }) {
  return async (req: Request, res: Response, next: NextFunction) => {
    const key = `ratelimit:${req.ip}`;
    const now = Date.now();
    const windowStart = now - opts.windowMs;

    const pipeline = redis.pipeline();
    pipeline.zremrangebyscore(key, 0, windowStart);   // remove expired entries
    pipeline.zadd(key, now.toString(), `${now}:${Math.random()}`); // add current request
    pipeline.zcard(key);                               // count requests in window
    pipeline.pexpire(key, opts.windowMs);              // set TTL on the key

    const results = await pipeline.exec();
    const requestCount = results![2][1] as number;

    res.set("X-RateLimit-Limit", opts.max.toString());
    res.set("X-RateLimit-Remaining", Math.max(0, opts.max - requestCount).toString());

    if (requestCount > opts.max) {
      res.status(429).json({ error: "Too many requests", retry_after_ms: opts.windowMs });
      return;
    }
    next();
  };
}

// Usage: 100 requests per 15-minute window
app.use("/api", rateLimiter({ windowMs: 15 * 60 * 1000, max: 100 }));
```

## API Versioning with Express Router

```typescript
import express from "express";

const app = express();
app.use(express.json());

// Shared middleware applied to all versions
function requestLogger(req: express.Request, _res: express.Response, next: express.NextFunction) {
  console.log(`${req.method} ${req.originalUrl}`);
  next();
}
app.use(requestLogger);

// V1 routes
const v1 = express.Router();
v1.get("/users/:id", async (req, res) => {
  const user = await db.query("SELECT id, name, email FROM users WHERE id = $1", [req.params.id]);
  res.json({ user: user.rows[0] }); // v1 envelope: { user: ... }
});

// V2 routes — different response shape
const v2 = express.Router();
v2.get("/users/:id", async (req, res) => {
  const user = await db.query("SELECT id, display_name, email, avatar_url FROM users WHERE id = $1", [req.params.id]);
  res.json({ data: user.rows[0], meta: { api_version: "v2" } }); // v2 envelope: { data, meta }
});

app.use("/api/v1", v1);
app.use("/api/v2", v2);
```

## Request Validation Middleware with Zod

```typescript
import { z, ZodSchema } from "zod";
import { Request, Response, NextFunction } from "express";

function validate(schema: { body?: ZodSchema; query?: ZodSchema; params?: ZodSchema }) {
  return (req: Request, res: Response, next: NextFunction) => {
    const errors: Record<string, string[]> = {};

    for (const [key, zodSchema] of Object.entries(schema) as [string, ZodSchema][]) {
      const result = zodSchema.safeParse(req[key as keyof Request]);
      if (!result.success) {
        errors[key] = result.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`);
      } else {
        (req as Record<string, unknown>)[key] = result.data; // replace with parsed/coerced data
      }
    }

    if (Object.keys(errors).length > 0) {
      res.status(400).json({ error: "Validation failed", details: errors });
      return;
    }
    next();
  };
}

// Usage
const createUserSchema = {
  body: z.object({
    email: z.string().email(),
    display_name: z.string().min(1).max(200),
    role: z.enum(["user", "admin"]).default("user"),
  }),
};

app.post("/api/users", validate(createUserSchema), async (req, res) => {
  // req.body is typed and validated
  const user = await userService.create(req.body);
  res.status(201).json({ data: user });
});
```

## Webhook Delivery with Retry and Signature

```typescript
import crypto from "crypto";

interface WebhookTarget {
  id: string;
  url: string;
  secret: string;
}

interface DeliveryRecord {
  webhookId: string;
  targetId: string;
  status: "pending" | "delivered" | "failed";
  attempts: number;
  lastAttemptAt?: Date;
  nextRetryAt?: Date;
}

function signPayload(payload: string, secret: string): string {
  return crypto.createHmac("sha256", secret).update(payload).digest("hex");
}

async function deliverWebhook(target: WebhookTarget, event: Record<string, unknown>): Promise<boolean> {
  const body = JSON.stringify(event);
  const signature = signPayload(body, target.secret);

  const response = await fetch(target.url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Webhook-Signature": `sha256=${signature}`,
      "X-Webhook-Id": event.id as string,
    },
    body,
    signal: AbortSignal.timeout(10_000), // 10s timeout
  });
  return response.ok;
}

// Retry dispatcher with exponential backoff
async function dispatchWithRetry(
  pool: import("pg").Pool,
  target: WebhookTarget,
  event: Record<string, unknown>,
  maxAttempts = 5
): Promise<void> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const success = await deliverWebhook(target, event).catch(() => false);

    await pool.query(
      `UPDATE webhook_deliveries SET attempts = $1, last_attempt_at = NOW(), status = $2, next_retry_at = $3 WHERE webhook_id = $4 AND target_id = $5`,
      [
        attempt,
        success ? "delivered" : attempt === maxAttempts ? "failed" : "pending",
        success ? null : new Date(Date.now() + Math.pow(2, attempt) * 1000), // 2s, 4s, 8s, 16s, 32s
        event.id,
        target.id,
      ]
    );

    if (success) return;

    // Exponential backoff: 2^attempt seconds
    await new Promise((resolve) => setTimeout(resolve, Math.pow(2, attempt) * 1000));
  }
}
```

## GraphQL Resolver with DataLoader

```typescript
import DataLoader from "dataloader";
import { Pool } from "pg";

const db = new Pool();

// Batch function: fetch many users in a single query
async function batchGetUsers(ids: readonly string[]) {
  const { rows } = await db.query(
    `SELECT id, display_name, email FROM users WHERE id = ANY($1)`,
    [ids]
  );
  // DataLoader requires results in the same order as input ids
  const userMap = new Map(rows.map((r) => [r.id, r]));
  return ids.map((id) => userMap.get(id) ?? new Error(`User ${id} not found`));
}

// Create a new loader per request to avoid caching across users
function createLoaders() {
  return {
    user: new DataLoader(batchGetUsers),
  };
}

// GraphQL resolvers
const resolvers = {
  Query: {
    post: async (_: unknown, { id }: { id: string }) => {
      const { rows } = await db.query("SELECT * FROM posts WHERE id = $1", [id]);
      return rows[0];
    },
  },
  Post: {
    // Without DataLoader: N+1 — one query per post's author
    // With DataLoader: batched into a single WHERE id = ANY([...]) query
    author: (post: { author_id: string }, _args: unknown, ctx: { loaders: ReturnType<typeof createLoaders> }) => {
      return ctx.loaders.user.load(post.author_id);
    },
  },
};

// In your GraphQL server setup (e.g., Apollo Server)
// context: ({ req }) => ({ loaders: createLoaders() })
```
