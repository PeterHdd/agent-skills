# Monitoring & Observability

## Structured Logging

Node.js pino logger with request ID correlation, log levels, and child loggers for per-module context.

```typescript
import pino from "pino";
import { randomUUID } from "crypto";
import { Request, Response, NextFunction } from "express";

const logger = pino({
  level: process.env.LOG_LEVEL || "info",
  formatters: {
    level(label) {
      return { level: label };
    },
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  redact: ["req.headers.authorization", "req.headers.cookie"],
});

export const dbLogger = logger.child({ module: "database" });
export const cacheLogger = logger.child({ module: "cache" });

export function requestLogger(req: Request, res: Response, next: NextFunction) {
  const requestId = (req.headers["x-request-id"] as string) || randomUUID();
  req.log = logger.child({ requestId, method: req.method, path: req.url });
  res.setHeader("x-request-id", requestId);

  const start = Date.now();
  res.on("finish", () => {
    req.log.info({ statusCode: res.statusCode, durationMs: Date.now() - start }, "request completed");
  });
  next();
}

export default logger;
```

## Prometheus Metrics

Express middleware exposing custom application metrics using prom-client: request duration histogram, active requests gauge, and HTTP error counter.

```typescript
import { Registry, Histogram, Gauge, Counter, collectDefaultMetrics } from "prom-client";
import { Request, Response, NextFunction } from "express";

const register = new Registry();
collectDefaultMetrics({ register });

const httpRequestDuration = new Histogram({
  name: "http_request_duration_seconds",
  help: "Duration of HTTP requests in seconds",
  labelNames: ["method", "route", "status_code"] as const,
  buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
  registers: [register],
});

const activeRequests = new Gauge({
  name: "http_active_requests",
  help: "Number of active HTTP requests",
  labelNames: ["method"] as const,
  registers: [register],
});

const httpErrors = new Counter({
  name: "http_errors_total",
  help: "Total number of HTTP errors",
  labelNames: ["method", "route", "status_code"] as const,
  registers: [register],
});

export function metricsMiddleware(req: Request, res: Response, next: NextFunction) {
  const end = httpRequestDuration.startTimer({ method: req.method, route: req.route?.path || req.path });
  activeRequests.inc({ method: req.method });

  res.on("finish", () => {
    const labels = { method: req.method, route: req.route?.path || req.path, status_code: String(res.statusCode) };
    end(labels);
    activeRequests.dec({ method: req.method });
    if (res.statusCode >= 400) {
      httpErrors.inc(labels);
    }
  });
  next();
}

export async function metricsHandler(_req: Request, res: Response) {
  res.set("Content-Type", register.contentType);
  res.end(await register.metrics());
}
```

## Grafana Dashboard JSON

Dashboard with four panels: request rate, error rate, latency percentiles (p50/p95/p99), and active connections. Import directly into Grafana.

```json
{
  "dashboard": {
    "title": "Application Overview",
    "uid": "app-overview",
    "timezone": "utc",
    "refresh": "30s",
    "time": { "from": "now-1h", "to": "now" },
    "panels": [
      {
        "title": "Request Rate",
        "type": "timeseries",
        "gridPos": { "x": 0, "y": 0, "w": 12, "h": 8 },
        "targets": [
          { "expr": "sum(rate(http_request_duration_seconds_count[5m]))", "legendFormat": "requests/sec" }
        ]
      },
      {
        "title": "Error Rate",
        "type": "timeseries",
        "gridPos": { "x": 12, "y": 0, "w": 12, "h": 8 },
        "targets": [
          { "expr": "sum(rate(http_errors_total[5m])) / sum(rate(http_request_duration_seconds_count[5m])) * 100", "legendFormat": "error %" }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 1 },
                { "color": "red", "value": 5 }
              ]
            },
            "unit": "percent"
          }
        }
      },
      {
        "title": "Latency p50 / p95 / p99",
        "type": "timeseries",
        "gridPos": { "x": 0, "y": 8, "w": 12, "h": 8 },
        "targets": [
          { "expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))", "legendFormat": "p50" },
          { "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))", "legendFormat": "p95" },
          { "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))", "legendFormat": "p99" }
        ],
        "fieldConfig": { "defaults": { "unit": "s" } }
      },
      {
        "title": "Active Connections",
        "type": "timeseries",
        "gridPos": { "x": 12, "y": 8, "w": 12, "h": 8 },
        "targets": [
          { "expr": "sum(http_active_requests)", "legendFormat": "active" }
        ]
      }
    ]
  }
}
```

## Prometheus Alert Rules

Alert rules for high error rate, high latency, pod restart loops, and disk usage.

```yaml
groups:
  - name: application.alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_errors_total[5m]))
          / sum(rate(http_request_duration_seconds_count[5m]))
          > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 5%"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes."
          runbook_url: "https://wiki.example.com/runbooks/high-error-rate"

      - alert: HighP99Latency
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "p99 latency above 1s"
          description: "p99 latency is {{ $value | humanizeDuration }} over the last 10 minutes."
          runbook_url: "https://wiki.example.com/runbooks/high-latency"

      - alert: PodRestartLoop
        expr: increase(kube_pod_container_status_restarts_total[15m]) > 3
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Pod {{ $labels.pod }} restarting repeatedly"
          description: "{{ $labels.pod }} has restarted {{ $value }} times in 15 minutes."
          runbook_url: "https://wiki.example.com/runbooks/pod-restart-loop"

      - alert: DiskUsageHigh
        expr: |
          (node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_avail_bytes{mountpoint="/"})
          / node_filesystem_size_bytes{mountpoint="/"} > 0.80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Disk usage above 80% on {{ $labels.instance }}"
          description: "Root filesystem on {{ $labels.instance }} is at {{ $value | humanizePercentage }}."
          runbook_url: "https://wiki.example.com/runbooks/disk-usage"
```

## Distributed Tracing

OpenTelemetry setup for Node.js with tracer provider, span processor, automatic HTTP instrumentation, and custom spans for database calls.

```typescript
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { HttpInstrumentation } from "@opentelemetry/instrumentation-http";
import { ExpressInstrumentation } from "@opentelemetry/instrumentation-express";
import { Resource } from "@opentelemetry/resources";
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from "@opentelemetry/semantic-conventions";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { trace, SpanStatusCode } from "@opentelemetry/api";

const exporter = new OTLPTraceExporter({
  url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || "http://localhost:4318/v1/traces",
});

const sdk = new NodeSDK({
  resource: new Resource({
    [ATTR_SERVICE_NAME]: "app",
    [ATTR_SERVICE_VERSION]: process.env.APP_VERSION || "0.0.0",
  }),
  spanProcessor: new BatchSpanProcessor(exporter),
  instrumentations: [new HttpInstrumentation(), new ExpressInstrumentation()],
});

sdk.start();
process.on("SIGTERM", () => sdk.shutdown());

// Custom span helper for wrapping database calls
const tracer = trace.getTracer("app");

export async function tracedQuery<T>(name: string, query: () => Promise<T>): Promise<T> {
  return tracer.startActiveSpan(`db.${name}`, async (span) => {
    try {
      const result = await query();
      span.setStatus({ code: SpanStatusCode.OK });
      return result;
    } catch (error) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: (error as Error).message });
      span.recordException(error as Error);
      throw error;
    } finally {
      span.end();
    }
  });
}
```

## Health Check Endpoint

Express `/health/live` and `/health/ready` endpoints that verify database, Redis, and external service dependencies.

```typescript
import { Router, Request, Response } from "express";
import { Pool } from "pg";
import { Redis } from "ioredis";

const router = Router();
const db = new Pool({ connectionString: process.env.DATABASE_URL });
const redis = new Redis(process.env.REDIS_URL || "redis://localhost:6379");

interface CheckResult {
  status: "ok" | "error";
  latencyMs: number;
  message?: string;
}

async function checkDatabase(): Promise<CheckResult> {
  const start = Date.now();
  try {
    await db.query("SELECT 1");
    return { status: "ok", latencyMs: Date.now() - start };
  } catch (err) {
    return { status: "error", latencyMs: Date.now() - start, message: (err as Error).message };
  }
}

async function checkRedis(): Promise<CheckResult> {
  const start = Date.now();
  try {
    await redis.ping();
    return { status: "ok", latencyMs: Date.now() - start };
  } catch (err) {
    return { status: "error", latencyMs: Date.now() - start, message: (err as Error).message };
  }
}

async function checkExternalService(): Promise<CheckResult> {
  const start = Date.now();
  try {
    const res = await fetch(process.env.EXTERNAL_API_URL + "/health", { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return { status: "ok", latencyMs: Date.now() - start };
  } catch (err) {
    return { status: "error", latencyMs: Date.now() - start, message: (err as Error).message };
  }
}

// Liveness: is the process running and not deadlocked
router.get("/health/live", (_req: Request, res: Response) => {
  res.json({ status: "ok" });
});

// Readiness: can the service handle traffic (all dependencies available)
router.get("/health/ready", async (_req: Request, res: Response) => {
  const [database, cache, external] = await Promise.all([checkDatabase(), checkRedis(), checkExternalService()]);
  const checks = { database, cache, external };
  const healthy = Object.values(checks).every((c) => c.status === "ok");
  res.status(healthy ? 200 : 503).json({ status: healthy ? "ok" : "degraded", checks });
});

export default router;
```
