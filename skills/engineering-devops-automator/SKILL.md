---
name: engineering-devops-automator
description: "Automate infrastructure provisioning, CI/CD pipelines, and cloud operations for reliable deployments. Use when you need Terraform infrastructure-as-code, Docker containerization, blue-green or canary deployments, monitoring and alerting setup, log aggregation, disaster recovery planning, secrets management, cost optimization, or multi-environment configuration with tools like Vault, ELK, Loki, or AWS."
metadata:
  version: "1.0.0"
---

# DevOps & Infrastructure Guide

## Overview
This guide covers infrastructure automation, CI/CD pipeline development, deployment strategies, monitoring, and cloud operations. Use it when provisioning infrastructure, building pipelines, setting up observability, managing secrets, or planning disaster recovery.

## Infrastructure Decision Rules

### Provisioning
- Use Terraform with remote state (S3 + DynamoDB lock) so every resource is version-controlled and safe from concurrent modifications.
- Use Terraform workspaces or directory-per-environment layout with shared modules to catch drift between staging and production.
- Use the same Terraform modules as production with variable overrides -- never create infrastructure via cloud console.

### CI/CD Pipelines
- Structure as discrete stages (lint, test, build, scan, deploy) with explicit dependencies so security failures block deployment.
- Deployment strategy: **blue-green** for zero-downtime + instant rollback, **canary** for gradual traffic shifting with metric-based promotion, **rolling** when simplicity matters and brief mixed-version traffic is acceptable.
- Automate any manual step performed more than twice; delete the manual runbook entry to prevent drift.

### Containerization
- Use multi-stage Docker builds with distroless or Alpine final images to minimize attack surface.
- CI must run Trivy (or equivalent) and fail on CRITICAL/HIGH findings before merge.

### Monitoring and Reliability
- Instrument the four golden signals (latency, traffic, errors, saturation); alert on symptoms, not causes.
- Every alert must link to a runbook; alerts without runbooks get deleted or converted to dashboard metrics within one sprint.
- Enforce structured JSON logging; ship to centralized system (ELK, Loki) with compliance-aligned retention.
- Configure liveness probes for 30-second restart; set PodDisruptionBudget for availability during disruptions.

### Disaster Recovery
- Automate failover with runbooks tested quarterly; an untested DR plan is no plan.

### Cost Optimization
- Review cloud utilization monthly; downsize any instance averaging below 20% CPU over 14 days.

### Secrets Management
- Store secrets in Vault or AWS Secrets Manager with automated rotation (max 90-day TTL); inject at runtime.
- Never commit secrets to source control or bake them into images.

### Network Security
- Default all security groups and NACLs to deny-all inbound; open only required ports/CIDRs; prune monthly.

### Compliance
- Generate automated audit logs recording deployer, commit SHA, and approval; store immutably for retention period.

## Scripts

- `scripts/validate_dockerfile.sh` -- Check a Dockerfile against common best practices: multi-stage builds, USER instruction, HEALTHCHECK, no latest tags, COPY over ADD, and .dockerignore presence. Run with `--help` for usage.
- `scripts/check_services.sh` -- Check TCP connectivity and HTTP response for a list of host:port pairs. Reports status, latency, and HTTP status code. Run with `--help` for usage.

## Code Examples

See [CI/CD Pipeline Guide](references/cicd-pipeline.md) for a full GitHub Actions pipeline with security scanning, container build, and blue-green deployment with smoke tests.

See [Infrastructure & Monitoring Guide](references/infrastructure.md) for Terraform (launch template, ASG, ALB, CloudWatch alarm) and Prometheus configuration with alert rules.

## Workflow

### Step 1: Infrastructure Assessment
- Audit existing infrastructure, deployment process, and monitoring gaps.
- Map application dependencies and scaling requirements.
- Identify security and compliance requirements for the target environment.

### Step 2: Pipeline Design
- Design CI/CD pipeline with security scanning integration.
- Plan deployment strategy (blue-green, canary, rolling).
- Create infrastructure as code templates.
- Design monitoring and alerting strategy.

### Step 3: Implementation
- Set up CI/CD pipelines with automated testing.
- Implement infrastructure as code with version control.
- Configure monitoring, logging, and alerting systems.
- Create disaster recovery and backup automation.

### Step 4: Optimization and Maintenance
- Monitor system performance and optimize resources.
- Implement cost optimization strategies.
- Create automated security scanning and compliance reporting.
- Build self-healing systems with automated recovery.

## References

- [CI/CD Pipeline Guide](references/cicd-pipeline.md) -- GitHub Actions pipeline with security scanning, container build, and blue-green deployment.
- [Infrastructure & Monitoring Guide](references/infrastructure.md) -- Terraform (launch template, ASG, ALB, CloudWatch alarm) and Prometheus configuration.
- [Kubernetes Patterns](references/kubernetes.md) -- Production Deployment, HPA, PDB, ConfigMap/Secret mounting, Ingress with TLS, CronJob, and Helm values.
- [Docker Best Practices](references/docker.md) -- Multi-stage Dockerfiles (Node.js, Python, Go), .dockerignore, Docker Compose, and Trivy scanning.
- [Monitoring & Observability](references/observability.md) -- Structured logging, Prometheus metrics, Grafana dashboard, alert rules, OpenTelemetry tracing, and health checks.
