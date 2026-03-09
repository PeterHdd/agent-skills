# Docker Best Practices

## Multi-stage Node.js Dockerfile

Builder stage installs dependencies, production stage uses distroless with non-root user and health check. COPY order optimized for layer caching.

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY tsconfig.json ./
COPY src/ src/
RUN npm run build && npm prune --production

FROM gcr.io/distroless/nodejs20-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

ENV NODE_ENV=production
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/nodejs/bin/node", "-e", "require('http').get('http://localhost:8080/health/live', r => { process.exit(r.statusCode === 200 ? 0 : 1) })"]

USER nonroot
CMD ["dist/server.js"]
```

## Multi-stage Python Dockerfile

Dependencies installed into a virtual environment in the builder stage, then only the venv is copied to the slim production image.

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r app && useradd -r -g app -d /app app
COPY --from=builder /opt/venv /opt/venv
COPY src/ src/
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000
USER app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Multi-stage Go Dockerfile

Static binary compiled in the builder stage and copied to a minimal distroless image.

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app/server ./cmd/server

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /app/server /server
EXPOSE 8080
USER nonroot
ENTRYPOINT ["/server"]
```

## .dockerignore

Comprehensive ignore file for Node.js projects preventing unnecessary files from entering the build context.

```dockerignore
node_modules
npm-debug.log*
.git
.gitignore
.env
.env.*
Dockerfile
docker-compose*.yml
.dockerignore
tests/
__tests__/
coverage/
docs/
*.md
.vscode/
.idea/
.nyc_output/
.github/
```

## Docker Compose for Local Development

Full local stack with application, PostgreSQL, Redis, and Mailhog. Uses healthchecks and conditional depends_on to ensure correct startup order.

```yaml
version: "3.9"

services:
  app:
    build:
      context: .
      target: builder
    ports:
      - "8080:8080"
    environment:
      NODE_ENV: development
      DATABASE_URL: postgresql://app:${POSTGRES_PASSWORD}@postgres:5432/appdb
      REDIS_URL: redis://redis:6379
      SMTP_HOST: mailhog
      SMTP_PORT: 1025
    volumes:
      - ./src:/app/src:cached
      - ./package.json:/app/package.json
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: npm run dev

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d appdb"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  mailhog:
    image: mailhog/mailhog:latest
    ports:
      - "1025:1025"
      - "8025:8025"

volumes:
  pgdata:
  redisdata:
```

Set `POSTGRES_PASSWORD` in a local `.env` file or your shell before starting Compose. Keep that value out of version control and use a separate secret source in non-local environments.

## Container Security Scanning

Trivy configuration as a CLI command for local use and as a GitHub Actions step for CI.

```bash
# CLI: scan image for CRITICAL and HIGH vulnerabilities, fail on findings
trivy image --severity CRITICAL,HIGH --exit-code 1 \
  --ignore-unfixed --format table registry.example.com/app:1.4.2
```

```yaml
# GitHub Actions step
- name: Container security scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: registry.example.com/app:${{ github.sha }}
    format: sarif
    output: trivy-results.sarif
    severity: CRITICAL,HIGH
    exit-code: "1"
    ignore-unfixed: true
- name: Upload scan results
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: trivy-results.sarif
```
